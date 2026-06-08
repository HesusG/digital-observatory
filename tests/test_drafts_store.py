from unittest.mock import MagicMock, patch

import pytest

from observatory.storage import drafts_store
from observatory.storage.drafts_store import (
    Draft,
    EduVerdict,
    DraftStatus,
    build_draft_id,
)


def test_build_draft_id_is_deterministic():
    a = build_draft_id(item_url="https://x.com/y", platform="x", lang="es")
    b = build_draft_id(item_url="https://x.com/y", platform="x", lang="es")
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_build_draft_id_distinguishes_platform_and_lang():
    base = "https://x.com/y"
    ids = {
        build_draft_id(base, "x", "es"),
        build_draft_id(base, "x", "en"),
        build_draft_id(base, "linkedin", "es"),
        build_draft_id(base, "bluesky", "es"),
    }
    assert len(ids) == 4  # all distinct


@patch.object(drafts_store, "_get_collection")
def test_upsert_draft_writes_expected_metadata(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll

    draft_id = drafts_store.upsert_draft(
        item_url="https://example.com/post",
        platform="x",
        lang="en",
        content="A post body.",
        item_title="Example",
        item_source="Test Source",
    )

    assert draft_id == build_draft_id("https://example.com/post", "x", "en")
    coll.upsert.assert_called_once()
    kwargs = coll.upsert.call_args.kwargs
    assert kwargs["ids"] == [draft_id]
    meta = kwargs["metadatas"][0]
    assert meta["item_url"] == "https://example.com/post"
    assert meta["platform"] == "x"
    assert meta["lang"] == "en"
    assert meta["status"] == "draft"
    assert meta["edu_verdict"] == ""
    assert meta["item_title"] == "Example"


@patch.object(drafts_store, "_get_collection")
def test_update_edu_verdict_writes_status_when_approved(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["draftid123"],
        "metadatas": [{"item_url": "u", "platform": "x", "lang": "en", "status": "draft"}],
    }

    drafts_store.update_edu_verdict(
        draft_id="draftid123",
        verdict=EduVerdict.APPROVED_FOR_REVIEW,
        reasoning="Looks good.",
    )

    coll.update.assert_called_once()
    new_meta = coll.update.call_args.kwargs["metadatas"][0]
    assert new_meta["edu_verdict"] == "approved-for-review"
    assert new_meta["edu_reasoning"] == "Looks good."
    assert new_meta["status"] == "awaiting-user"


@patch.object(drafts_store, "_get_collection")
def test_update_edu_verdict_rejects_set_status_rejected(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["d1"],
        "metadatas": [{"item_url": "u", "platform": "x", "lang": "en", "status": "draft"}],
    }

    drafts_store.update_edu_verdict("d1", EduVerdict.REJECT, "Bad tone.")

    new_meta = coll.update.call_args.kwargs["metadatas"][0]
    assert new_meta["status"] == "rejected"


@patch.object(drafts_store, "_get_collection")
def test_mark_published_records_postiz_id(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["d1"],
        "metadatas": [{"status": "awaiting-user"}],
    }

    drafts_store.mark_published(
        draft_id="d1",
        postiz_post_id="ptz_42",
        scheduled_at="2026-05-22T10:00:00Z",
    )

    meta = coll.update.call_args.kwargs["metadatas"][0]
    assert meta["status"] == "scheduled"
    assert meta["postiz_post_id"] == "ptz_42"
    assert meta["scheduled_at"] == "2026-05-22T10:00:00Z"


@patch.object(drafts_store, "_get_collection")
def test_mark_skipped_sets_status_and_reason(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {"ids": ["d1"], "metadatas": [{"status": "awaiting-user"}]}

    drafts_store.mark_skipped("d1", reason="not-relevant-this-week")

    meta = coll.update.call_args.kwargs["metadatas"][0]
    assert meta["status"] == "skipped"
    assert meta["skip_reason"] == "not-relevant-this-week"


@patch.object(drafts_store, "_get_collection")
def test_list_drafts_by_status_filters(mock_get_collection):
    coll = MagicMock()
    mock_get_collection.return_value = coll
    coll.get.return_value = {
        "ids": ["d1", "d2", "d3"],
        "metadatas": [
            {"status": "awaiting-user", "platform": "x", "lang": "es"},
            {"status": "scheduled", "platform": "x", "lang": "es"},
            {"status": "awaiting-user", "platform": "linkedin", "lang": "en"},
        ],
        "documents": ["d1c", "d2c", "d3c"],
    }

    result = drafts_store.list_drafts_by_status("awaiting-user")

    assert {r["id"] for r in result} == {"d1", "d3"}


def test_upsert_draft_persists_profile_and_account(monkeypatch):
    captured = {}

    class FakeColl:
        def upsert(self, ids, documents, metadatas):
            captured["id"] = ids[0]
            captured["meta"] = metadatas[0]

    monkeypatch.setattr(
        "observatory.storage.drafts_store._get_collection", lambda: FakeColl()
    )
    from observatory.storage.drafts_store import upsert_draft

    upsert_draft(
        item_url="https://example.com/a",
        platform="x",
        lang="es",
        content="hola",
        item_title="T",
        item_source="S",
        profile_id="tech-reviewer",
        account="x",
    )
    assert captured["meta"]["profile_id"] == "tech-reviewer"
    assert captured["meta"]["account"] == "x"
