from unittest.mock import AsyncMock, MagicMock

import pytest

from observatory.agents import edu


def test_parse_edu_response_well_formed():
    raw = (
        '{"verdict": "approved-for-review", "reasoning": "Good.", '
        '"fail_categories": [], "hand_back": ""}'
    )
    r = edu.parse_edu_response(raw)
    assert r.verdict == "approved-for-review"
    assert r.reasoning == "Good."
    assert r.fail_categories == []


def test_parse_edu_response_revise_with_handback():
    raw = (
        '{"verdict": "revise", "reasoning": "Over X limit.", '
        '"fail_categories": ["platform"], "hand_back": "Trim by 50 chars."}'
    )
    r = edu.parse_edu_response(raw)
    assert r.verdict == "revise"
    assert "platform" in r.fail_categories
    assert "Trim by 50 chars." in r.hand_back


def test_parse_edu_response_malformed_returns_revise():
    """When the model returns garbage, we default to revise (safer than
    rejecting a draft that might be fine)."""
    r = edu.parse_edu_response("not json")
    assert r.verdict == "revise"
    assert "parse-error" in r.reasoning.lower()


def test_build_edu_prompt_includes_persona_and_inputs():
    prompt = edu.build_edu_prompt(
        draft_text="A draft.",
        platform="x",
        lang="en",
        hook="Hook.",
        summary="Summary.",
        recent_posts=[{"title": "Old post", "hook": "Old hook"}],
    )
    assert "You are Edu" in prompt
    assert "A draft." in prompt
    assert "Old post" in prompt
    assert "x" in prompt.lower()


@pytest.mark.asyncio
async def test_review_draft_returns_verdict(monkeypatch):
    """End-to-end happy path: mocked Ollama returns approved-for-review."""
    fake_provider = AsyncMock()
    fake_provider.ainvoke = AsyncMock(return_value=MagicMock(
        content='{"verdict":"approved-for-review","reasoning":"OK.","fail_categories":[],"hand_back":""}'
    ))

    async def fake_get_provider():
        return fake_provider

    monkeypatch.setattr(edu, "_get_provider", fake_get_provider)

    verdict = await edu.review_draft(
        draft_text="A draft.",
        platform="x",
        lang="en",
        hook="Hook.",
        summary="Summary.",
        recent_posts=[],
    )

    assert verdict.verdict == "approved-for-review"


@pytest.mark.asyncio
async def test_review_draft_ollama_unreachable_returns_revise(monkeypatch):
    """If Ollama is down, we revise (not reject) — fail-safe."""
    async def fake_get_provider():
        return None

    monkeypatch.setattr(edu, "_get_provider", fake_get_provider)

    verdict = await edu.review_draft(
        draft_text="A draft.",
        platform="x",
        lang="en",
        hook="Hook.",
        summary="Summary.",
        recent_posts=[],
    )

    assert verdict.verdict == "revise"
    assert "unavailable" in verdict.reasoning.lower()
