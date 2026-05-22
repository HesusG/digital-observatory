from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from observatory.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_drafts_list_filters_by_status(client, monkeypatch):
    from observatory.storage import drafts_store

    monkeypatch.setattr(
        drafts_store,
        "list_drafts_by_status",
        lambda status, limit=100: [
            {"id": "d1", "metadata": {"status": status, "platform": "x", "lang": "en"}, "document": "hi"},
        ],
    )

    r = client.get("/api/drafts?status=awaiting-user")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["id"] == "d1"


def test_post_drafts_approve_calls_pablo(client, monkeypatch):
    from observatory.agents import pablo

    monkeypatch.setattr(
        pablo,
        "publish_draft",
        AsyncMock(return_value=pablo.PabloResult(ok=True, postiz_post_id="ptz-42")),
    )

    r = client.post("/api/drafts/draft-abc/approve")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["postiz_post_id"] == "ptz-42"


def test_post_drafts_approve_pablo_fails(client, monkeypatch):
    from observatory.agents import pablo

    monkeypatch.setattr(
        pablo,
        "publish_draft",
        AsyncMock(return_value=pablo.PabloResult(ok=False, error="boom")),
    )

    r = client.post("/api/drafts/draft-abc/approve")
    assert r.status_code == 502
    assert "boom" in r.json()["error"]


def test_post_drafts_skip_updates_status(client, monkeypatch):
    from observatory.storage import drafts_store

    calls = []
    monkeypatch.setattr(
        drafts_store,
        "mark_skipped",
        lambda draft_id, reason="user-skip": calls.append((draft_id, reason)),
    )

    r = client.post("/api/drafts/draft-abc/skip", params={"reason": "off-topic"})
    assert r.status_code == 200
    assert calls == [("draft-abc", "off-topic")]


def test_post_drafts_edit_replaces_content_then_approves(client, monkeypatch):
    """Edit replaces content, then triggers Pablo publish on the new content."""
    from observatory.storage import drafts_store
    from observatory.agents import pablo

    updates = []
    monkeypatch.setattr(
        drafts_store,
        "get_draft",
        lambda did: {"id": did, "metadata": {"platform": "bluesky", "lang": "en", "status": "awaiting-user", "item_url": "u", "item_title": "t", "item_source": "s"}, "document": "old"},
    )
    monkeypatch.setattr(
        drafts_store,
        "upsert_draft",
        lambda **kw: updates.append(kw) or "draft-abc",
    )
    monkeypatch.setattr(
        pablo,
        "publish_draft",
        AsyncMock(return_value=pablo.PabloResult(ok=True, postiz_post_id="ptz-2")),
    )

    r = client.post("/api/drafts/draft-abc/edit", json={"content": "new text"})
    assert r.status_code == 200
    assert r.json()["postiz_post_id"] == "ptz-2"
