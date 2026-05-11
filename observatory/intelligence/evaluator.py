import json
import logging
import textwrap
from pathlib import Path
from typing import Optional

from config.settings import settings
from observatory.storage.models import EvaluationResult
from observatory.monitoring.health import check_ollama

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are an expert analyzer of professional opportunities spanning education,
AI research, technology careers, and funding/grants.

Your task: read a recently scraped opportunity and evaluate how well it matches
the user's profile.

--- USER PROFILE ---
{user_profile}

--- OPPORTUNITY FOUND ---
{opportunity_text}

--- INSTRUCTIONS ---
1. Analyze the opportunity against the user's profile, skills, and interests.
2. Determine if it is free, funded, or paid (scholarships, grants, salary).
3. Classify the opportunity type into one of these categories:
   scholarship, fellowship, internship, job, grant, conference, award, general.
4. Assign an affinity score from 1 to 10 (10 = perfect match). Consider:
   - Educational programs (PhD, summer schools, exchange programs)
   - AI/ML research positions (postdoc, research engineer, lab positions)
   - Tech jobs (especially AI/data science, remote-friendly)
   - Grants and funding (NGO grants, research funding, project grants)
   - Conferences and workshops (CFPs, speaking opportunities, AI + education)
5. Summarize what the opportunity is about in 2 sentences max.

Return ONLY valid JSON with this structure, no extra text or markdown blocks:
{{"affinity_score": (int 1-10), "is_free_or_funded": (bool), "category": (str), "summary": (str), "reasoning": (str)}}"""


def _load_user_profile() -> str:
    profile_path = Path(settings.user_profile_path)
    if not profile_path.exists():
        logger.warning(f"User profile not found at {profile_path}")
        return "No user profile available."
    return profile_path.read_text(encoding="utf-8")


def build_evaluation_prompt(user_profile: str, opportunity_text: str) -> str:
    truncated = textwrap.shorten(opportunity_text, width=6000, placeholder="... [truncated]")
    return PROMPT_TEMPLATE.format(user_profile=user_profile, opportunity_text=truncated)


def parse_llm_response(raw: str) -> EvaluationResult:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        score = max(1, min(10, int(data.get("affinity_score", 1))))
        return EvaluationResult(
            affinity_score=score,
            is_free_or_funded=bool(data.get("is_free_or_funded", False)),
            category=str(data.get("category", "general")),
            summary=str(data.get("summary", "")),
            reasoning=str(data.get("reasoning", "")),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return EvaluationResult(
            affinity_score=1,
            summary="LLM response could not be parsed",
            reasoning=str(e),
        )


async def _get_provider():
    """Returns an LLM provider in priority order: Ollama -> OpenAI -> Gemini."""
    if await check_ollama():
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=0,
            )
        except Exception as e:
            logger.warning(f"Ollama provider failed to initialize: {e}")

    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", temperature=0)
        except Exception as e:
            logger.warning(f"OpenAI provider failed to initialize: {e}")

    if settings.gemini_api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
        except Exception as e:
            logger.warning(f"Gemini provider failed to initialize: {e}")

    logger.error("No LLM provider available")
    return None


async def evaluate_opportunity(opportunity_text: str) -> Optional[EvaluationResult]:
    provider = await _get_provider()
    if provider is None:
        return None

    user_profile = _load_user_profile()
    prompt_text = build_evaluation_prompt(user_profile, opportunity_text)

    try:
        from langchain_core.messages import HumanMessage
        response = await provider.ainvoke([HumanMessage(content=prompt_text)])
        return parse_llm_response(response.content)
    except Exception as e:
        logger.error(f"LLM evaluation failed: {e}")
        return None
