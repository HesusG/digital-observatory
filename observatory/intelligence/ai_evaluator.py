"""Teacher-lens evaluator for AI / EdTech articles.

Parallel to evaluator.py (which scores opportunities for personal-affinity).
This module asks Ollama: "If I'm running an AI-for-Teachers course, is this
article useful to my audience this week, and how would I post about it?"
"""
import json
import logging
import textwrap
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from config.settings import settings
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = """You are the editorial brain of a marketing pipeline for an
"AI for Teachers" course. The audience is high-school and university teachers
(ES and EN speakers, two separate streams), plus AI-curious general public.

Your job: read a recently published AI / tech / edtech article and decide
whether it's worth turning into social-media content for that audience — and if
so, how.

--- USER / COURSE OWNER PROFILE ---
{user_profile}

--- ARTICLE ---
{article_text}

--- INSTRUCTIONS ---
1. teacher_relevance (1-10): how useful is this article to a classroom teacher
   in the next 1-2 weeks? Score generously for anything with a clear classroom
   angle; harshly for pure research with no obvious teaching application.
2. audience_fit: any subset of ["k12", "highered", "ai_curious_public"].
3. lang_targets: ["es"], ["en"], or ["es", "en"]. Be honest — many AI news
   items only matter in EN. Cross-language only if the underlying point lands
   for both audiences without translation friction.
4. topic_tags: 2-6 short tags (e.g., "llm", "agents", "rag", "classroom-tool",
   "edtech-policy", "evals").
5. one_line_hook: ≤140 chars. This is the most important field — it must work
   as the opening line of a post a teacher would actually click.
6. post_angles: 3-5 angles, each {{"angle": "...", "for": "<audience>-<lang>"}},
   e.g. "for": "k12-es". Mix audiences and languages from lang_targets.
7. suggested_platforms: any subset of ["x", "linkedin", "bluesky"].
8. summary: 2 sentences in the article's original language.
9. course_tie_in: null OR a short sentence describing a natural way to soft-pitch
   the "AI for Teachers" course alongside this article. Leave null when forced.
10. skip_reason: null when the article is worth posting; otherwise one of:
    "research-only-no-classroom-angle", "duplicate-of-recent", "too-niche",
    "low-signal".

Return ONLY valid JSON with this exact structure, no extra text:
{{"teacher_relevance": <int 1-10>, "audience_fit": [<str>], "lang_targets": [<str>], "topic_tags": [<str>], "one_line_hook": <str>, "post_angles": [{{"angle": <str>, "for": <str>}}], "suggested_platforms": [<str>], "summary": <str>, "course_tie_in": <str|null>, "skip_reason": <str|null>}}"""


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
    truncated = textwrap.shorten(article_text, width=6000, placeholder="... [truncated]")
    return PROMPT_TEMPLATE.format(user_profile=user_profile, article_text=truncated)


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
