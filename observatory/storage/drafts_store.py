"""ChromaDB helpers for the drafts collection.

One row per (item_url, platform, lang). Lifecycle:

    draft           ← Carla just wrote it
    awaiting-user   ← Edu approved-for-review; sitting in Telegram
    scheduled       ← Pablo handed it to Postiz; postiz_post_id stored
    published       ← Postiz reported success (Ana fills this in)
    skipped         ← user tapped Skip
    rejected        ← Edu vetoed
"""
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config.settings import settings

logger = logging.getLogger(__name__)

_client: Optional[chromadb.HttpClient] = None
_embedding_fn: Optional[SentenceTransformerEmbeddingFunction] = None


class DraftStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_USER = "awaiting-user"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    SKIPPED = "skipped"
    REJECTED = "rejected"


class EduVerdict(str, Enum):
    APPROVED_FOR_REVIEW = "approved-for-review"
    REVISE = "revise"
    REJECT = "reject"


@dataclass
class Draft:
    id: str
    item_url: str
    platform: str
    lang: str
    content: str
    status: str
    edu_verdict: str
    edu_reasoning: str
    postiz_post_id: str
    metadata: dict


def _get_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return _client


def _get_embedding_fn() -> SentenceTransformerEmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model)
    return _embedding_fn


def _get_collection() -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name="drafts",
        embedding_function=_get_embedding_fn(),
        metadata={"hnsw:space": "cosine"},
    )


def build_draft_id(item_url: str, platform: str, lang: str) -> str:
    key = f"{item_url}|{platform}|{lang}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()


def upsert_draft(
    item_url: str,
    platform: str,
    lang: str,
    content: str,
    item_title: str = "",
    item_source: str = "",
) -> str:
    """Create or refresh a draft row. Status starts as 'draft'."""
    draft_id = build_draft_id(item_url, platform, lang)
    coll = _get_collection()
    now = datetime.utcnow().isoformat()
    metadata = {
        "item_url": item_url,
        "platform": platform,
        "lang": lang,
        "status": DraftStatus.DRAFT.value,
        "edu_verdict": "",
        "edu_reasoning": "",
        "postiz_post_id": "",
        "scheduled_at": "",
        "skip_reason": "",
        "item_title": item_title,
        "item_source": item_source,
        "created_at": now,
        "updated_at": now,
    }
    coll.upsert(ids=[draft_id], documents=[content], metadatas=[metadata])
    return draft_id


def _read(draft_id: str) -> Optional[dict]:
    coll = _get_collection()
    res = coll.get(ids=[draft_id], include=["metadatas", "documents"])
    if not res["ids"]:
        return None
    return {
        "id": res["ids"][0],
        "metadata": res["metadatas"][0] if res["metadatas"] else {},
        "document": res["documents"][0] if res["documents"] else "",
    }


def _merge_meta(draft_id: str, patch: dict) -> None:
    coll = _get_collection()
    existing = coll.get(ids=[draft_id])
    if not existing["ids"]:
        logger.warning("Unknown draft id: %s", draft_id[:12])
        return
    meta = existing["metadatas"][0] if existing["metadatas"] else {}
    meta.update(patch)
    meta["updated_at"] = datetime.utcnow().isoformat()
    coll.update(ids=[draft_id], metadatas=[meta])


def update_edu_verdict(
    draft_id: str,
    verdict: EduVerdict,
    reasoning: str = "",
) -> None:
    if verdict == EduVerdict.APPROVED_FOR_REVIEW:
        status = DraftStatus.AWAITING_USER.value
    elif verdict == EduVerdict.REJECT:
        status = DraftStatus.REJECTED.value
    else:  # REVISE
        status = DraftStatus.DRAFT.value
    _merge_meta(draft_id, {
        "edu_verdict": verdict.value,
        "edu_reasoning": reasoning,
        "status": status,
    })


def mark_published(draft_id: str, postiz_post_id: str, scheduled_at: str = "") -> None:
    _merge_meta(draft_id, {
        "status": DraftStatus.SCHEDULED.value,
        "postiz_post_id": postiz_post_id,
        "scheduled_at": scheduled_at,
    })


def mark_skipped(draft_id: str, reason: str = "user-skip") -> None:
    _merge_meta(draft_id, {
        "status": DraftStatus.SKIPPED.value,
        "skip_reason": reason,
    })


def get_draft(draft_id: str) -> Optional[dict]:
    return _read(draft_id)


def list_drafts_by_status(status: str, limit: int = 100) -> list[dict]:
    coll = _get_collection()
    try:
        res = coll.get(include=["metadatas", "documents"])
    except Exception as e:
        logger.error("ChromaDB get failed: %s", e)
        return []
    out: list[dict] = []
    if not res["ids"]:
        return out
    for i, doc_id in enumerate(res["ids"]):
        meta = res["metadatas"][i] if res["metadatas"] else {}
        if meta.get("status") != status:
            continue
        out.append({
            "id": doc_id,
            "metadata": meta,
            "document": res["documents"][i] if res["documents"] else "",
        })
        if len(out) >= limit:
            break
    return out
