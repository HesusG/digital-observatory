import pytest
from unittest.mock import patch, MagicMock
from observatory.processing.deduplicator import is_duplicate


@patch("observatory.processing.deduplicator.chromadb_store")
def test_exact_url_duplicate(mock_store):
    mock_store.url_exists.return_value = True
    dup, dup_of = is_duplicate("Some text about AI", "https://example.com/opp1")
    assert dup is True
    assert dup_of == "https://example.com/opp1"
    mock_store.find_nearest.assert_not_called()


@patch("observatory.processing.deduplicator.chromadb_store")
def test_semantic_duplicate(mock_store):
    mock_store.url_exists.return_value = False
    mock_store.find_nearest.return_value = (
        0.05,
        {"url": "https://other.com/same-opp"},
    )
    dup, dup_of = is_duplicate("AI scholarship in Finland", "https://new.com/opp")
    assert dup is True
    assert dup_of == "https://other.com/same-opp"


@patch("observatory.processing.deduplicator.chromadb_store")
def test_not_duplicate(mock_store):
    mock_store.url_exists.return_value = False
    mock_store.find_nearest.return_value = (0.85, {"url": "https://unrelated.com"})
    dup, dup_of = is_duplicate("Completely new opportunity", "https://brand-new.com")
    assert dup is False
    assert dup_of is None


@patch("observatory.processing.deduplicator.chromadb_store")
def test_empty_store(mock_store):
    mock_store.url_exists.return_value = False
    mock_store.find_nearest.return_value = (None, None)
    dup, dup_of = is_duplicate("First item ever", "https://first.com")
    assert dup is False
    assert dup_of is None
