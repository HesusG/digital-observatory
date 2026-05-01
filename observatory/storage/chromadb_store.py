import hashlib
import logging
from datetime import datetime
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config.settings import settings

logger = logging.getLogger(__name__)

_client: Optional[chromadb.HttpClient] = None
_embedding_fn: Optional[SentenceTransformerEmbeddingFunction] = None


def _get_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        logger.info(f"Connected to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
    return _client


def _get_embedding_fn() -> SentenceTransformerEmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
    return _embedding_fn


def get_items_collection() -> chromadb.Collection:
    client = _get_client()
    return client.get_or_create_collection(
        name="items",
        embedding_function=_get_embedding_fn(),
        metadata={"hnsw:space": "cosine"},
    )


def url_to_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def upsert_item(
    url: str,
    title: str,
    source: str,
    source_type: str,
    raw_text: str,
    topics: list[str] | None = None,
    sentiment: str = "neutral",
    affinity_score: int = 0,
    summary: str = "",
    reasoning: str = "",
    is_free_or_funded: bool = False,
    obsidian_path: str = "",
    is_duplicate: bool = False,
    duplicate_of: str | None = None,
) -> str:
    collection = get_items_collection()
    doc_id = url_to_id(url)

    metadata = {
        "url": url,
        "title": title,
        "source": source,
        "source_type": source_type,
        "collected_at": datetime.utcnow().isoformat(),
        "topics": ",".join(topics or []),
        "sentiment": sentiment,
        "affinity_score": affinity_score,
        "summary": summary,
        "reasoning": reasoning,
        "is_free_or_funded": is_free_or_funded,
        "obsidian_path": obsidian_path,
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of or "",
        "processed_at": datetime.utcnow().isoformat(),
    }

    # Truncate raw_text for embedding (MiniLM handles ~256 word pieces)
    truncated = raw_text[:2000]

    collection.upsert(ids=[doc_id], documents=[truncated], metadatas=[metadata])
    logger.info(f"Upserted item {doc_id[:12]}... ({title[:50]})")
    return doc_id


def query_similar(text: str, n_results: int = 5) -> list[dict]:
    collection = get_items_collection()
    results = collection.query(query_texts=[text], n_results=n_results)

    items = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            items.append({
                "id": doc_id,
                "distance": results["distances"][0][i] if results["distances"] else None,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "document": results["documents"][0][i] if results["documents"] else "",
            })
    return items


def find_nearest(text: str) -> tuple[float | None, dict | None]:
    """Returns (distance, metadata) of the nearest existing item, or (None, None)."""
    results = query_similar(text, n_results=1)
    if not results:
        return None, None
    return results[0]["distance"], results[0]["metadata"]


def get_recent_items(since: datetime, min_affinity: int = 0) -> list[dict]:
    collection = get_items_collection()
    where_filter = {"$and": [
        {"collected_at": {"$gte": since.isoformat()}},
        {"affinity_score": {"$gte": min_affinity}},
    ]}

    try:
        results = collection.get(where=where_filter, include=["metadatas", "documents"])
    except Exception:
        # Fallback: get all and filter in Python
        results = collection.get(include=["metadatas", "documents"])

    items = []
    if results["ids"]:
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            collected = meta.get("collected_at", "")
            score = meta.get("affinity_score", 0)
            if collected >= since.isoformat() and score >= min_affinity:
                items.append({
                    "id": doc_id,
                    "metadata": meta,
                    "document": results["documents"][i] if results["documents"] else "",
                })
    return items


def get_item_count() -> int:
    collection = get_items_collection()
    return collection.count()
