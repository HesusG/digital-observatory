import pytest
from unittest.mock import MagicMock, patch
from observatory.storage.chromadb_store import url_to_id, url_exists, update_item_evaluation


def test_url_to_id_deterministic():
    url = "https://example.com/opp/123"
    assert url_to_id(url) == url_to_id(url)


def test_url_to_id_different_urls():
    assert url_to_id("https://a.com") != url_to_id("https://b.com")


@patch("observatory.storage.chromadb_store.get_items_collection")
def test_url_exists_true(mock_collection):
    collection = MagicMock()
    collection.get.return_value = {"ids": ["abc123"]}
    mock_collection.return_value = collection
    assert url_exists("https://example.com") is True


@patch("observatory.storage.chromadb_store.get_items_collection")
def test_url_exists_false(mock_collection):
    collection = MagicMock()
    collection.get.return_value = {"ids": []}
    mock_collection.return_value = collection
    assert url_exists("https://nonexistent.com") is False


@patch("observatory.storage.chromadb_store.get_items_collection")
def test_update_item_evaluation(mock_collection):
    collection = MagicMock()
    collection.get.return_value = {
        "ids": ["abc"],
        "metadatas": [{"url": "https://example.com", "title": "Test"}],
    }
    mock_collection.return_value = collection

    update_item_evaluation(
        url="https://example.com",
        affinity_score=9,
        category="scholarship",
        summary="Great match",
        reasoning="Strong AI focus",
        is_free_or_funded=True,
    )

    collection.update.assert_called_once()
    call_args = collection.update.call_args
    metadata = call_args[1]["metadatas"][0]
    assert metadata["affinity_score"] == 9
    assert metadata["category"] == "scholarship"
