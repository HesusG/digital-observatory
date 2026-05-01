import logging

from config.settings import settings
from observatory.storage import chromadb_store
from observatory.processing.embedder import clean_for_embedding

logger = logging.getLogger(__name__)


def is_duplicate(raw_text: str, url: str) -> tuple[bool, str | None]:
    """
    Check if an item is semantically similar to an existing one in ChromaDB.
    Returns (is_duplicate, duplicate_of_url).
    """
    cleaned = clean_for_embedding(raw_text)
    distance, metadata = chromadb_store.find_nearest(cleaned)

    if distance is None:
        return False, None

    existing_url = metadata.get("url", "") if metadata else ""

    # Same URL is not a "duplicate" — it's an update
    if existing_url == url:
        return False, None

    if distance < settings.dedup_distance_threshold:
        logger.info(
            f"Duplicate detected (distance={distance:.3f}): "
            f"'{url[:60]}' ≈ '{existing_url[:60]}'"
        )
        return True, existing_url

    return False, None
