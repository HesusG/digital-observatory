"""
Embedding is handled directly by ChromaDB's SentenceTransformerEmbeddingFunction.
This module provides utilities for pre-processing text before embedding.
"""

import re


def clean_for_embedding(text: str, max_chars: int = 2000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^\w\s.,;:!?@#$%&*()\-+=\[\]{}/\\'\"|<>]", "", text)
    return text[:max_chars]
