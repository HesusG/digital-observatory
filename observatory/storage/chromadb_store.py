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
    kind: str = "opportunity",
    source_group: str = "opportunities",
    lang_hint: str = "en",
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
        "kind": kind,
        "source_group": source_group,
        "lang_hint": lang_hint,
        "processed_at": datetime.utcnow().isoformat(),
    }

    # Embed title + body so items sharing boilerplate body text still embed
    # distinctly (MiniLM handles ~256 word pieces).
    from observatory.processing.embedder import build_embedding_text

    document = build_embedding_text(title, raw_text)

    collection.upsert(ids=[doc_id], documents=[document], metadatas=[metadata])
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


def get_recent_items(
    since: datetime,
    min_affinity: int = 0,
    kind: str | None = None,
    lang: str | None = None,
    min_relevance: int = 0,
) -> list[dict]:
    """Recent items, filtered. Filtering is done in Python to handle ChromaDB
    metadata fields that don't always exist (older entries missing kind etc.).

    - kind: "opportunity" | "article" | None (any)
    - lang: ISO-639 code; matches when present in metadata.lang_targets list
    - min_relevance: applied to teacher_relevance for articles, affinity_score
      for opportunities (so callers can use one knob across both)
    """
    collection = get_items_collection()
    try:
        results = collection.get(include=["metadatas", "documents"])
    except Exception as e:
        logger.error(f"ChromaDB get failed: {e}")
        return []

    items: list[dict] = []
    since_iso = since.isoformat()
    if not results["ids"]:
        return items

    for i, doc_id in enumerate(results["ids"]):
        meta = results["metadatas"][i] if results["metadatas"] else {}
        if meta.get("collected_at", "") < since_iso:
            continue

        item_kind = meta.get("kind", "opportunity")  # legacy items default to opportunity
        if kind is not None and item_kind != kind:
            continue

        if item_kind == "article":
            score = int(meta.get("teacher_relevance", 0) or 0)
        else:
            score = int(meta.get("affinity_score", 0) or 0)

        # Backwards-compatible: callers using min_affinity get the same
        # semantics for opportunities; new callers use min_relevance.
        threshold = max(min_affinity, min_relevance)
        if score < threshold:
            continue

        if lang is not None:
            targets = (meta.get("lang_targets") or "").split(",")
            targets = [t for t in (s.strip() for s in targets) if t]
            if lang not in targets:
                continue

        items.append({
            "id": doc_id,
            "metadata": meta,
            "document": results["documents"][i] if results["documents"] else "",
        })
    return items


def get_item_by_url(url: str) -> dict | None:
    collection = get_items_collection()
    doc_id = url_to_id(url)
    res = collection.get(ids=[doc_id], include=["metadatas", "documents"])
    if not res["ids"]:
        return None
    meta = res["metadatas"][0] if res["metadatas"] else {}
    doc = res["documents"][0] if res["documents"] else ""
    return {"id": res["ids"][0], "metadata": meta, "document": doc}


def mark_item_skipped(item_id: str, reason: str = "user-skip") -> bool:
    """Mark an item as skipped (user pressed Skip in the marketing inbox).
    Returns True if the item existed and was updated."""
    collection = get_items_collection()
    existing = collection.get(ids=[item_id])
    if not existing["ids"]:
        return False
    metadata = existing["metadatas"][0] if existing["metadatas"] else {}
    metadata.update({
        "skip_reason": reason,
        "status": "skipped",
        "processed_at": datetime.utcnow().isoformat(),
    })
    collection.update(ids=[item_id], metadatas=[metadata])
    logger.info(f"Marked {item_id[:12]}... as skipped (reason={reason})")
    return True


def get_item_count() -> int:
    collection = get_items_collection()
    return collection.count()


def get_item_count_fast() -> int:
    """Count items without instantiating the SentenceTransformer embedding model
    (which is what made /api/stats time out on first call)."""
    client = _get_client()
    col = client.get_collection(name="items")
    return col.count()


def url_exists(url: str) -> bool:
    collection = get_items_collection()
    doc_id = url_to_id(url)
    results = collection.get(ids=[doc_id])
    return bool(results["ids"])


def update_item_evaluation(
    url: str,
    affinity_score: int,
    category: str = "general",
    summary: str = "",
    reasoning: str = "",
    is_free_or_funded: bool = False,
    deadline: str = "",
):
    collection = get_items_collection()
    doc_id = url_to_id(url)

    existing = collection.get(ids=[doc_id])
    if not existing["ids"]:
        logger.warning(f"Cannot update evaluation for unknown URL: {url[:60]}")
        return

    metadata = existing["metadatas"][0] if existing["metadatas"] else {}
    metadata.update({
        "affinity_score": affinity_score,
        "category": category,
        "summary": summary,
        "reasoning": reasoning,
        "is_free_or_funded": is_free_or_funded,
        "deadline": deadline,
        "processed_at": datetime.utcnow().isoformat(),
    })

    collection.update(ids=[doc_id], metadatas=[metadata])
    logger.info(f"Updated evaluation for {doc_id[:12]}... (score={affinity_score}, cat={category})")


def update_item_ai_evaluation(
    url: str,
    teacher_relevance: int,
    audience_fit: list[str],
    lang_targets: list[str],
    topic_tags: list[str],
    post_angles: list[dict] | None = None,
    suggested_platforms: list[str] | None = None,
    one_line_hook: str = "",
    summary: str = "",
    course_tie_in: str = "",
    skip_reason: str = "",
):
    import json as _json

    collection = get_items_collection()
    doc_id = url_to_id(url)

    existing = collection.get(ids=[doc_id])
    if not existing["ids"]:
        logger.warning(f"Cannot update AI evaluation for unknown URL: {url[:60]}")
        return

    metadata = existing["metadatas"][0] if existing["metadatas"] else {}
    metadata.update({
        "teacher_relevance": teacher_relevance,
        "audience_fit": ",".join(audience_fit or []),
        "lang_targets": ",".join(lang_targets or []),
        "topic_tags": ",".join(topic_tags or []),
        "post_angles_json": _json.dumps(post_angles or []),
        "suggested_platforms": ",".join(suggested_platforms or []),
        "one_line_hook": one_line_hook,
        "summary": summary,
        "course_tie_in": course_tie_in,
        "skip_reason": skip_reason,
        "processed_at": datetime.utcnow().isoformat(),
    })

    collection.update(ids=[doc_id], metadatas=[metadata])
    logger.info(
        f"Updated AI eval for {doc_id[:12]}... "
        f"(relevance={teacher_relevance}, langs={lang_targets})"
    )
