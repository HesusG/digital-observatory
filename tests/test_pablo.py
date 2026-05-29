from unittest.mock import AsyncMock, MagicMock

import pytest

from observatory.agents import pablo


@pytest.mark.asyncio
async def test_publish_draft_happy_path(monkeypatch):
    """Pablo posts to Postiz, captures postiz_post_id, marks the draft scheduled."""
    monkeypatch.setattr(pablo.settings, "postiz_base_url", "http://test:5000")
    monkeypatch.setattr(pablo.settings, "postiz_api_key", "key123")
    monkeypatch.setattr(pablo.settings, "postiz_bluesky_integration_id", "int-bsky")

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"posts": [{"id": "ptz-42"}]}
    fake_resp.raise_for_status = MagicMock()

    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = False
    fake_client.post.return_value = fake_resp

    monkeypatch.setattr(pablo.httpx, "AsyncClient", lambda **kw: fake_client)

    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: {
        "id": did,
        "metadata": {
            "platform": "bluesky",
            "lang": "en",
            "status": "awaiting-user",
        },
        "document": "Hello world.",
    })

    marks = []
    monkeypatch.setattr(pablo.drafts_store, "mark_published", lambda **kw: marks.append(kw))

    result = await pablo.publish_draft("draft-abc")

    assert result.ok is True
    assert result.postiz_post_id == "ptz-42"
    assert marks and marks[0]["postiz_post_id"] == "ptz-42"


@pytest.mark.asyncio
async def test_publish_draft_unknown_draft_returns_error(monkeypatch):
    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: None)
    result = await pablo.publish_draft("missing")
    assert result.ok is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_publish_draft_unsupported_platform_returns_error(monkeypatch):
    """Slice 1: only Bluesky is wired."""
    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: {
        "id": did,
        "metadata": {"platform": "linkedin", "status": "awaiting-user"},
        "document": "Hi.",
    })
    result = await pablo.publish_draft("d1")
    assert result.ok is False
    assert "platform" in result.error.lower()


@pytest.mark.asyncio
async def test_publish_draft_postiz_500_returns_error(monkeypatch):
    monkeypatch.setattr(pablo.settings, "postiz_api_key", "k")
    monkeypatch.setattr(pablo.settings, "postiz_bluesky_integration_id", "int-bsky")
    monkeypatch.setattr(pablo.drafts_store, "get_draft", lambda did: {
        "id": did,
        "metadata": {"platform": "bluesky", "lang": "en", "status": "awaiting-user"},
        "document": "Hi.",
    })

    err_resp = MagicMock()
    err_resp.status_code = 500
    err_resp.text = "boom"
    err_resp.raise_for_status.side_effect = pablo.httpx.HTTPStatusError(
        "500", request=MagicMock(), response=err_resp
    )
    fake_client = AsyncMock()
    fake_client.__aenter__.return_value = fake_client
    fake_client.__aexit__.return_value = False
    fake_client.post.return_value = err_resp
    monkeypatch.setattr(pablo.httpx, "AsyncClient", lambda **kw: fake_client)

    result = await pablo.publish_draft("d1")
    assert result.ok is False
    assert "postiz" in result.error.lower()
