"""Edu — Editor agent. Reviews Carla's drafts and emits a verdict."""
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from config.settings import settings
from observatory.agents.persona import Persona, load_persona
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)


PERSONA_PATH = Path(__file__).resolve().parents[2] / "agents" / "edu.md"


@dataclass
class EduResult:
    verdict: str  # "approved-for-review" | "revise" | "reject"
    reasoning: str
    fail_categories: list[str]
    hand_back: str


@lru_cache(maxsize=1)
def _edu_persona() -> Persona:
    return load_persona(PERSONA_PATH)


def build_edu_prompt(
    draft_text: str,
    platform: str,
    lang: str,
    hook: str,
    summary: str,
    recent_posts: list[dict],
) -> str:
    persona = _edu_persona()
    recent_lines = "\n".join(
        f"- {r.get('title','?')}: {r.get('hook','')[:80]}" for r in recent_posts
    ) or "(no recent posts yet)"
    return (
        f"{persona.body}\n\n"
        f"--- ASSIGNMENT ---\n"
        f"platform: {platform}\n"
        f"lang: {lang}\n"
        f"article_hook: {hook}\n"
        f"article_summary: {summary}\n\n"
        f"--- RECENT POSTS (last 30 days) ---\n{recent_lines}\n\n"
        f"--- DRAFT TO REVIEW ---\n{draft_text}\n\n"
        f"Return ONLY the verdict JSON described above. No markdown fences."
    )


def parse_edu_response(raw: str) -> EduResult:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        return EduResult(
            verdict=str(data.get("verdict", "revise")),
            reasoning=str(data.get("reasoning", "")),
            fail_categories=list(data.get("fail_categories") or []),
            hand_back=str(data.get("hand_back", "")),
        )
    except (json.JSONDecodeError, ValueError):
        return EduResult(
            verdict="revise",
            reasoning="parse-error: editor response was not valid JSON",
            fail_categories=[],
            hand_back="",
        )


async def _get_provider():
    if not await check_ollama():
        logger.error(
            "Ollama unreachable at %s — Edu cannot review drafts.",
            settings.ollama_base_url,
        )
        return None
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.1,
        )
    except Exception as e:
        logger.error("Edu provider failed to initialize: %s", e)
        return None


async def review_draft(
    draft_text: str,
    platform: str,
    lang: str,
    hook: str,
    summary: str,
    recent_posts: list[dict],
) -> EduResult:
    provider = await _get_provider()
    if provider is None:
        return EduResult(
            verdict="revise",
            reasoning="Editor unavailable (Ollama unreachable); not approving by default.",
            fail_categories=[],
            hand_back="",
        )

    prompt = build_edu_prompt(draft_text, platform, lang, hook, summary, recent_posts)

    try:
        from langchain_core.messages import HumanMessage
        response = await provider.ainvoke([HumanMessage(content=prompt)])
        return parse_edu_response(response.content)
    except Exception as e:
        logger.error("Edu review failed: %s", e)
        return EduResult(
            verdict="revise",
            reasoning=f"editor-error: {e}",
            fail_categories=[],
            hand_back="",
        )
