import pytest

from observatory import pipeline


@pytest.mark.asyncio
async def test_draft_promo_posts_uses_promo_voice_and_books(monkeypatch):
    calls = []

    async def fake_draft_for_platforms(**kwargs):
        calls.append(kwargs)
        return {"x": "promo!", "draft_ids": {"x": "id-x"}}

    monkeypatch.setattr(
        "observatory.intelligence.drafter.draft_for_platforms",
        fake_draft_for_platforms,
    )
    monkeypatch.setattr(pipeline.event_log, "append_event", lambda *a, **k: None)

    drafts = await pipeline.draft_promo_posts(book_id="ser-tutor", lang="es")

    assert calls, "expected at least one draft_for_platforms call"
    assert calls[0]["profile_id"] == "promo"
    assert "Ser Tutor" in calls[0]["hook"]
    assert calls[0]["tone"]  # promo voice non-empty
    assert len(drafts) >= 1


@pytest.mark.asyncio
async def test_draft_promo_posts_unknown_book_returns_empty(monkeypatch):
    monkeypatch.setattr(pipeline.event_log, "append_event", lambda *a, **k: None)
    drafts = await pipeline.draft_promo_posts(book_id="does-not-exist", lang="es")
    assert drafts == []
