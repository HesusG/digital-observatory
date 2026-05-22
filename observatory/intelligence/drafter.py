"""Per-platform, per-language post drafter.

Consumes an already-stored article (with its AI eval metadata) and produces
draft text for X, LinkedIn, and Bluesky in the requested language. Uses Ollama
with the same disabled-cloud-fallback posture as the evaluators.
"""
import asyncio
import json
import logging
import textwrap
from typing import Optional

from config.settings import settings
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)


PLATFORM_PROMPTS = {
    "x": {
        "limit_chars": 280,
        "spec": (
            "Write a single X (Twitter) post in {lang}. Open with a hook, no hashtag spam, "
            "max one or two precise tags only if natural. Stay strictly under 280 characters. "
            "Speak to a high-school or university teacher about the article's classroom angle. "
            "If 280 characters cannot fit the point, return a JSON list of 2-4 thread tweets "
            "(each ≤ 280 chars) — otherwise return a single string."
        ),
    },
    "linkedin": {
        "limit_chars": 1300,
        "spec": (
            "Write a single LinkedIn post in {lang}. Open with a 1-sentence teacher scenario, "
            "then explain what's new in the article and why it matters for the classroom. "
            "Use 3-6 short paragraphs separated by blank lines. End with a question to spark "
            "comments. ≤ 1300 characters. Return a single string."
        ),
    },
    "bluesky": {
        "limit_chars": 300,
        "spec": (
            "Write a Bluesky post in {lang}. Friendlier, more conversational than X. "
            "≤ 300 characters; if the point needs more, return a JSON list of 2-3 "
            "thread posts (each ≤ 300 chars). Otherwise a single string."
        ),
    },
}


LANG_LABELS = {"es": "Spanish (es-MX register)", "en": "English"}


PROMPT_TEMPLATE = """You are a social-media writer for an "AI for Teachers" course.

Audience: high-school and university teachers, plus AI-curious general public.
Voice: precise, warm, never hypey. No jargon walls. The teacher should feel
respected, not lectured.

Language: {lang_label}

Platform: {platform}
Platform spec: {platform_spec}

Article hook (already approved): {hook}
Article summary: {summary}
Suggested angles (use one as the spine):
{angles}

{cta_block}

Return ONLY the post text. If the platform spec asks for a thread, return a
JSON array of strings; otherwise return a plain string. No markdown fences,
no commentary."""


def _format_angles(angles: list[dict], lang: str) -> str:
    if not angles:
        return "(no angles provided)"
    lines = []
    for a in angles:
        if not isinstance(a, dict):
            lines.append(f"- {a}")
            continue
        for_tag = str(a.get("for", ""))
        if lang and lang not in for_tag and for_tag:
            # angle is tagged for a different language; still show but mark
            lines.append(f"- ({for_tag}) {a.get('angle','')}")
        else:
            lines.append(f"- {a.get('angle','')}")
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
    spec = PLATFORM_PROMPTS[platform]["spec"].format(lang=LANG_LABELS.get(lang, lang))
    cta_block = (
        "Soft-pitch the AI-for-Teachers course at the end — one sentence, no hard sell, "
        "leave a hook for the user to drop a course link in a reply. "
        if include_course_cta
        else "Do not mention the course. "
    )
    if tone:
        cta_block += f"Tone override: {tone}. "

    return PROMPT_TEMPLATE.format(
        lang_label=LANG_LABELS.get(lang, lang),
        platform=platform,
        platform_spec=spec,
        hook=hook or "(no hook supplied)",
        summary=textwrap.shorten(summary or "(no summary)", width=600, placeholder="..."),
        angles=_format_angles(angles, lang),
        cta_block=cta_block,
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
            f"Ollama unreachable at {settings.ollama_base_url} — d3r-ser asleep; "
            "drafter cannot produce content."
        )
        return None
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.7,  # warmer than the evaluator — we want voice
        )
    except Exception as e:
        logger.error(f"Ollama provider failed to initialize: {e}")
        return None


async def draft_for_platforms(
    hook: str,
    summary: str,
    angles: list[dict],
    platforms: list[str],
    lang: str,
    include_course_cta: bool = False,
    tone: str = "",
) -> dict[str, str | list[str]]:
    provider = await _get_provider()
    if provider is None:
        return {p: "" for p in platforms}

    from langchain_core.messages import HumanMessage

    async def draft_one(platform: str) -> tuple[str, str | list[str]]:
        if platform not in PLATFORM_PROMPTS:
            return platform, ""
        prompt = build_platform_prompt(
            platform=platform, lang=lang,
            hook=hook, summary=summary, angles=angles,
            include_course_cta=include_course_cta, tone=tone,
        )
        try:
            response = await provider.ainvoke([HumanMessage(content=prompt)])
            limit = PLATFORM_PROMPTS[platform]["limit_chars"]
            return platform, _parse_platform_output(response.content, limit)
        except Exception as e:
            logger.error(f"Draft failed for {platform}/{lang}: {e}")
            return platform, ""

    results = await asyncio.gather(*(draft_one(p) for p in platforms))
    return {p: text for p, text in results}
