from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from observatory.intelligence import drafter
from observatory.intelligence.drafter import build_platform_prompt, _parse_platform_output


def test_build_platform_prompt_includes_carla_persona():
    prompt = build_platform_prompt(
        platform="x",
        lang="es",
        hook="Hook here",
        summary="Summary.",
        angles=[{"angle": "ang1", "for": "k12-es"}],
        include_course_cta=False,
        tone="",
    )
    assert "You are Carla" in prompt
    assert "x" in prompt.lower()
    assert "Hook here" in prompt
    assert "Summary." in prompt
    assert "ang1" in prompt


def test_parse_platform_output_thread_array():
    out = _parse_platform_output('["one tweet", "two tweet"]', 280)
    assert out == ["one tweet", "two tweet"]


def test_parse_platform_output_single_truncates_to_limit():
    long = "x" * 500
    out = _parse_platform_output(long, 280)
    assert isinstance(out, str)
    assert len(out) == 280


@pytest.mark.asyncio
async def test_draft_for_platforms_persists_each_draft(monkeypatch):
    """draft_for_platforms must write one drafts_store row per platform."""
    upsert_calls = []

    def fake_upsert(**kwargs):
        upsert_calls.append(kwargs)
        return "fake-draft-id-" + kwargs["platform"]

    monkeypatch.setattr(drafter, "upsert_draft", fake_upsert)

    fake_provider = AsyncMock()
    fake_provider.ainvoke = AsyncMock(side_effect=[
        MagicMock(content="x-post"),
        MagicMock(content="linkedin-post"),
        MagicMock(content="bluesky-post"),
    ])

    async def fake_get_provider():
        return fake_provider

    monkeypatch.setattr(drafter, "_get_provider", fake_get_provider)

    result = await drafter.draft_for_platforms(
        hook="Hook",
        summary="Summary",
        angles=[],
        platforms=["x", "linkedin", "bluesky"],
        lang="en",
        item_url="https://example.com/x",
        item_title="Title",
        item_source="Source",
    )

    assert len(upsert_calls) == 3
    platforms_persisted = {c["platform"] for c in upsert_calls}
    assert platforms_persisted == {"x", "linkedin", "bluesky"}
    assert result["x"] == "x-post"
    assert result["linkedin"] == "linkedin-post"
    assert "draft_ids" in result
    assert result["draft_ids"]["x"] == "fake-draft-id-x"


async def test_draft_for_platforms_passes_profile_and_account(monkeypatch):
    from observatory.intelligence import drafter as _drafter

    captured = []

    def fake_upsert(**kwargs):
        captured.append(kwargs)
        return "draft-" + kwargs["platform"]

    class FakeResp:
        content = "texto generado"

    class FakeProvider:
        async def ainvoke(self, messages):
            return FakeResp()

    async def fake_get_provider():
        return FakeProvider()

    monkeypatch.setattr(_drafter, "upsert_draft", fake_upsert)
    monkeypatch.setattr(_drafter, "_get_provider", fake_get_provider)

    result = await _drafter.draft_for_platforms(
        hook="h", summary="s", angles=[], platforms=["x"], lang="es",
        item_url="https://ex.com/a", item_title="T", item_source="S",
        tone="voz reviewer",
        profile_id="tech-reviewer",
        accounts={"x": "x"},
    )

    assert result["x"] == "texto generado"
    assert captured[0]["profile_id"] == "tech-reviewer"
    assert captured[0]["account"] == "x"


def test_platform_prompts_includes_youtube_formats():
    from observatory.intelligence.drafter import PLATFORM_PROMPTS

    assert "youtube_short" in PLATFORM_PROMPTS
    assert "youtube_long" in PLATFORM_PROMPTS
    # Scripts are unbounded (0 = no hard char cap).
    assert PLATFORM_PROMPTS["youtube_short"]["limit_chars"] == 0
    assert PLATFORM_PROMPTS["youtube_long"]["limit_chars"] == 0


def test_youtube_short_prompt_embeds_script_framework():
    from observatory.intelligence.drafter import build_platform_prompt

    p = build_platform_prompt(
        platform="youtube_short", lang="es", hook="Claude 4.8 salió",
        summary="Nuevo modelo", angles=[], include_course_cta=False, tone="punchy",
    )
    low = p.lower()
    assert "video script" in low
    assert "hook" in low
    assert "payoff" in low  # short-form structure
    assert "punchy" in low  # tone threaded in


def test_youtube_long_prompt_embeds_script_framework():
    from observatory.intelligence.drafter import build_platform_prompt

    p = build_platform_prompt(
        platform="youtube_long", lang="es", hook="Cómo usar RAG",
        summary="Guía", angles=[], include_course_cta=False, tone="pedagógica",
    )
    low = p.lower()
    assert "video script" in low
    assert "second-best" in low  # body ordering cheat code
    assert "outro" in low
