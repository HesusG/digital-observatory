"""Per-platform, per-language post drafter.

Consumes an already-stored article (with its AI eval metadata) and produces
draft text for X, LinkedIn, and Bluesky in the requested language. Uses
Ollama with the same disabled-cloud-fallback posture as the evaluators.

Persona lives in agents/carla.md. Each generated draft is persisted to the
'drafts' ChromaDB collection so Edu can review it and Pablo can publish it.
"""
import asyncio
import json
import logging
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Optional

from config.settings import settings
from observatory.agents.persona import Persona, load_persona
from observatory.monitoring.health import check_ollama
from observatory.storage.drafts_store import upsert_draft

logger = logging.getLogger(__name__)


PLATFORM_PROMPTS = {
    "x":        {"limit_chars": 280},
    "linkedin": {"limit_chars": 1300},
    "bluesky":  {"limit_chars": 300},
    # Long-form blog draft: no hard character cap (0 = unbounded).
    "blog":     {"limit_chars": 0},
}

LANG_LABELS = {"es": "Spanish (es-MX register)", "en": "English"}


PERSONA_PATH = Path(__file__).resolve().parents[2] / "agents" / "carla.md"


@lru_cache(maxsize=1)
def _carla_persona() -> Persona:
    return load_persona(PERSONA_PATH)


def _format_angles(angles: list[dict], lang: str) -> str:
    if not angles:
        return "(no angles provided)"
    lines = []
    for a in angles:
        if not isinstance(a, dict):
            lines.append(f"- {a}")
            continue
        for_tag = str(a.get("for", ""))
        lines.append(f"- ({for_tag}) {a.get('angle','')}" if for_tag else f"- {a.get('angle','')}")
    return "\n".join(lines)


def build_platform_prompt(
    platform: str,
    lang: str,
    hook: str,
    summary: str,
    angles: list[dict],
    include_course_cta: bool,
    tone: str = "",
) -> str:
    persona = _carla_persona()
    limit = PLATFORM_PROMPTS[platform]["limit_chars"]
    lang_label = LANG_LABELS.get(lang, lang)
    cta_block = (
        "include_course_cta=true: soft-pitch the course in the last paragraph."
        if include_course_cta
        else "include_course_cta=false: do not mention the course."
    )
    tone_block = f"tone_override: {tone}" if tone else "tone_override: (none)"

    if platform == "blog":
        platform_line = "platform: blog (long-form article, no character limit)"
        format_line = (
            "Write a complete long-form BLOG DRAFT (several paragraphs, with an "
            "intro, body, and closing). Return ONLY the article text as a plain "
            "string. Markdown headings are allowed; no code fences."
        )
    else:
        platform_line = f"platform: {platform} (char limit {limit})"
        format_line = (
            "Return ONLY the post text. If platform requires a thread, return a JSON "
            "array of strings. Otherwise a plain string. No markdown fences."
        )

    return (
        f"{persona.body}\n\n"
        f"--- ASSIGNMENT ---\n"
        f"{platform_line}\n"
        f"lang: {lang_label}\n"
        f"hook: {hook}\n"
        f"summary: {textwrap.shorten(summary or '(no summary)', width=600, placeholder='...')}\n"
        f"angles:\n{_format_angles(angles, lang)}\n"
        f"{cta_block}\n"
        f"{tone_block}\n\n"
        f"{format_line}"
    )


def _parse_platform_output(raw: str, char_limit: int) -> str | list[str]:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    if cleaned.startswith("["):
        try:
            arr = json.loads(cleaned)
            if isinstance(arr, list):
                return [str(p)[:char_limit] for p in arr]
        except json.JSONDecodeError:
            pass
    return cleaned[: char_limit if char_limit > 0 else len(cleaned)]


async def _get_provider():
    if not await check_ollama():
        logger.error(
            "Ollama unreachable at %s — d3r-ser asleep; drafter cannot produce content.",
            settings.ollama_base_url,
        )
        return None
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.7,
        )
    except Exception as e:
        logger.error("Ollama provider failed to initialize: %s", e)
        return None


async def draft_for_platforms(
    hook: str,
    summary: str,
    angles: list[dict],
    platforms: list[str],
    lang: str,
    item_url: str = "",
    item_title: str = "",
    item_source: str = "",
    include_course_cta: bool = False,
    tone: str = "",
    profile_id: str = "",
    accounts: Optional[dict] = None,
) -> dict:
    """Generate per-platform drafts AND persist each one to the drafts collection.

    Returns:
        {
          "x": "<post text or thread list>",
          "linkedin": ...,
          "bluesky": ...,
          "draft_ids": {"x": "<draft id>", "linkedin": ..., "bluesky": ...},
        }
    """
    provider = await _get_provider()
    if provider is None:
        return {p: "" for p in platforms} | {"draft_ids": {}}

    from langchain_core.messages import HumanMessage

    async def one(platform: str) -> tuple[str, str | list[str]]:
        if platform not in PLATFORM_PROMPTS:
            return platform, ""
        prompt = build_platform_prompt(
            platform=platform, lang=lang,
            hook=hook, summary=summary, angles=angles,
            include_course_cta=include_course_cta, tone=tone,
        )
        try:
            response = await provider.ainvoke([HumanMessage(content=prompt)])
            return platform, _parse_platform_output(
                response.content, PLATFORM_PROMPTS[platform]["limit_chars"]
            )
        except Exception as e:
            logger.error("Draft failed for %s/%s: %s", platform, lang, e)
            return platform, ""

    results = await asyncio.gather(*(one(p) for p in platforms))

    drafts_dict: dict[str, str | list[str]] = {}
    draft_ids: dict[str, str] = {}
    for platform, content in results:
        drafts_dict[platform] = content
        if not content or not item_url:
            continue
        body = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        draft_id = upsert_draft(
            item_url=item_url,
            platform=platform,
            lang=lang,
            content=body,
            item_title=item_title,
            item_source=item_source,
            profile_id=profile_id,
            account=(accounts or {}).get(platform, ""),
        )
        draft_ids[platform] = draft_id

    drafts_dict["draft_ids"] = draft_ids
    return drafts_dict
