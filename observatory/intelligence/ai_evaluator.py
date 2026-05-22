"""Teacher-lens evaluator for AI / EdTech articles.

Parallel to evaluator.py (which scores opportunities for personal-affinity).
This module asks Ollama: "If I'm running an AI-for-Teachers course, is this
article useful to my audience this week, and how would I post about it?"
"""
import json
import logging
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from config.settings import settings
from observatory.agents.persona import Persona, load_persona
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)


PERSONA_PATH = Path(__file__).resolve().parents[2] / "agents" / "tess.md"


@lru_cache(maxsize=1)
def _tess_persona() -> Persona:
    return load_persona(PERSONA_PATH)


class PostAngle(BaseModel):
    angle: str
    for_: str = Field(alias="for")

    class Config:
        populate_by_name = True


class AIEvaluationResult(BaseModel):
    teacher_relevance: int = 0
    audience_fit: list[str] = Field(default_factory=list)
    lang_targets: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)
    one_line_hook: str = ""
    post_angles: list[dict] = Field(default_factory=list)
    suggested_platforms: list[str] = Field(default_factory=list)
    summary: str = ""
    course_tie_in: Optional[str] = None
    skip_reason: Optional[str] = None


def _load_user_profile() -> str:
    profile_path = Path(settings.user_profile_path)
    if not profile_path.exists():
        return "No user profile available."
    return profile_path.read_text(encoding="utf-8")


def build_ai_prompt(user_profile: str, article_text: str) -> str:
    persona = _tess_persona()
    truncated = textwrap.shorten(article_text, width=6000, placeholder="... [truncated]")
    return (
        f"{persona.body}\n\n"
        f"--- USER / COURSE OWNER PROFILE ---\n{user_profile}\n\n"
        f"--- ARTICLE ---\n{truncated}\n\n"
        f"Return ONLY the JSON described in the output schema above. "
        f"No commentary, no markdown fences."
    )


def parse_ai_response(raw: str) -> AIEvaluationResult:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        relevance = max(1, min(10, int(data.get("teacher_relevance", 1))))
        return AIEvaluationResult(
            teacher_relevance=relevance,
            audience_fit=list(data.get("audience_fit") or []),
            lang_targets=[l for l in (data.get("lang_targets") or []) if l in settings.ai_supported_langs],
            topic_tags=list(data.get("topic_tags") or []),
            one_line_hook=str(data.get("one_line_hook", "")),
            post_angles=list(data.get("post_angles") or []),
            suggested_platforms=list(data.get("suggested_platforms") or []),
            summary=str(data.get("summary", "")),
            course_tie_in=data.get("course_tie_in"),
            skip_reason=data.get("skip_reason"),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse AI eval response: {e}")
        return AIEvaluationResult(skip_reason="parse-error")


async def _get_provider():
    """Ollama-only; same posture as evaluator._get_provider. Returns None when
    d3r-ser is unreachable so the pipeline skips evaluation rather than
    silently falling back to a paid cloud LLM."""
    if await check_ollama():
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=0.2,
            )
        except Exception as e:
            logger.error(f"Ollama provider failed to initialize: {e}")
    else:
        logger.error(
            f"Ollama unreachable at {settings.ollama_base_url} — d3r-ser likely asleep. "
            "Wake it (WOL) to restore AI-article evaluation."
        )
    return None


async def evaluate_ai_signal(article_text: str) -> Optional[AIEvaluationResult]:
    provider = await _get_provider()
    if provider is None:
        return None

    user_profile = _load_user_profile()
    prompt_text = build_ai_prompt(user_profile, article_text)

    try:
        from langchain_core.messages import HumanMessage
        response = await provider.ainvoke([HumanMessage(content=prompt_text)])
        return parse_ai_response(response.content)
    except Exception as e:
        logger.error(f"AI-signal evaluation failed: {e}")
        return None
