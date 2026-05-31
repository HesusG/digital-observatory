import logging

from config.settings import settings
from observatory.storage import chromadb_store
from observatory.processing.embedder import build_embedding_text

logger = logging.getLogger(__name__)


def is_duplicate(raw_text: str, url: str, title: str = "") -> tuple[bool, str | None]:
    """
    Two-phase deduplication:
    1. URL hash check (fast O(1) — catches exact re-scrapes)
    2. Semantic similarity (expensive — catches same opp on different sites)
    """
    if chromadb_store.url_exists(url):
        return True, url

    cleaned = build_embedding_text(title, raw_text)
    distance, metadata = chromadb_store.find_nearest(cleaned)

    if distance is None:
        return False, None

    existing_url = metadata.get("url", "") if metadata else ""

    if distance < settings.dedup_distance_threshold:
        logger.info(
            f"Semantic duplicate (distance={distance:.3f}): "
            f"'{url[:60]}' ≈ '{existing_url[:60]}'"
        )
        return True, existing_url

    return False, None
