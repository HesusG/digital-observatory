"""
Embedding is handled directly by ChromaDB's SentenceTransformerEmbeddingFunction.
This module provides utilities for pre-processing text before embedding.
"""

import re


def clean_for_embedding(text: str, max_chars: int = 2000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^\w\s.,;:!?@#$%&*()\-+=\[\]{}/\\'\"|<>]", "", text)
    return text[:max_chars]


def build_embedding_text(title: str, raw_text: str, max_chars: int = 2000) -> str:
    """Text used for semantic dedup/embedding. Prefix the title so that items
    sharing boilerplate body text (common across opportunity sites) still embed
    distinctly. Falls back to raw_text when title is empty."""
    title = (title or "").strip()
    if not title:
        return clean_for_embedding(raw_text or "", max_chars=max_chars)
    return clean_for_embedding(f"{title}. {raw_text or ''}", max_chars=max_chars)
