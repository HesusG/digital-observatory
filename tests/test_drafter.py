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
