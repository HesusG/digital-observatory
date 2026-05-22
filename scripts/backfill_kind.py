#!/usr/bin/env python3
"""One-shot backfill: tag existing ChromaDB items with kind/source_group/lang_hint.

Pre-Phase-1, items were stored without these fields, which means the new
kind-based routing in /api/items/recent and the marketing-team workflows can't
see them. This script walks the collection once and stamps each item.

Usage (inside the observatory container or with the right .env):

    python -m scripts.backfill_kind --dry-run
    python -m scripts.backfill_kind                 # actually writes

The mapping is derived from config/sources/rss_feeds.yaml. Items whose source
doesn't match any RSS feed name fall back to source_type-based defaults
(wordpress → opportunity, anything else → article).
"""
import argparse
import logging
import sys
from pathlib import Path

import yaml

from config.settings import settings
from observatory.collectors.rss import CATEGORY_ROUTING
from observatory.storage import chromadb_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")


def load_source_to_kind() -> dict[str, tuple[str, str]]:
    """Returns {source_name: (kind, source_group)} from the RSS feeds YAML."""
    feeds_path = Path(__file__).parent.parent / "config" / "sources" / "rss_feeds.yaml"
    if not feeds_path.exists():
        logger.error(f"Cannot find {feeds_path}")
        sys.exit(2)
    with open(feeds_path, "r", encoding="utf-8") as f:
        feeds = yaml.safe_load(f) or {}

    mapping: dict[str, tuple[str, str]] = {}
    for category, entries in feeds.items():
        kind, source_group = CATEGORY_ROUTING.get(category, ("article", category))
        for entry in entries:
            name = entry.get("name") if isinstance(entry, dict) else None
            if name:
                mapping[name] = (kind, source_group)
    return mapping


def classify(meta: dict, source_to_kind: dict[str, tuple[str, str]]) -> tuple[str, str, str]:
    source_name = meta.get("source", "") or ""
    if source_name in source_to_kind:
        kind, source_group = source_to_kind[source_name]
    elif meta.get("source_type") == "wordpress":
        kind, source_group = "opportunity", "opportunities"
    else:
        kind, source_group = "article", "uncategorized"
    return kind, source_group, "en"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report counts, don't write")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-stamp items that already have a kind field",
    )
    args = parser.parse_args()

    source_to_kind = load_source_to_kind()
    logger.info(
        f"Loaded source→kind map for {len(source_to_kind)} RSS feed names from YAML"
    )

    collection = chromadb_store.get_items_collection()
    results = collection.get(include=["metadatas"])
    total = len(results["ids"]) if results["ids"] else 0
    logger.info(f"Scanning {total} items in ChromaDB at {settings.chroma_host}:{settings.chroma_port}")

    counts = {"opportunity": 0, "article": 0, "skipped_already_tagged": 0}
    updates: list[tuple[str, dict]] = []

    for i, doc_id in enumerate(results["ids"] or []):
        meta = results["metadatas"][i] if results["metadatas"] else {}
        if not args.force and meta.get("kind"):
            counts["skipped_already_tagged"] += 1
            continue
        kind, source_group, lang_hint = classify(meta, source_to_kind)
        counts[kind] += 1
        new_meta = dict(meta)
        new_meta.update({"kind": kind, "source_group": source_group, "lang_hint": lang_hint})
        updates.append((doc_id, new_meta))

    logger.info(
        f"Counts: opportunity={counts['opportunity']} article={counts['article']} "
        f"already_tagged={counts['skipped_already_tagged']}"
    )

    if args.dry_run:
        logger.info("--dry-run set; not writing")
        return

    if not updates:
        logger.info("Nothing to update")
        return

    # ChromaDB doesn't have a great bulk-update; do it in chunks.
    CHUNK = 200
    for i in range(0, len(updates), CHUNK):
        chunk = updates[i:i + CHUNK]
        ids = [x[0] for x in chunk]
        metas = [x[1] for x in chunk]
        collection.update(ids=ids, metadatas=metas)
        logger.info(f"Updated {i + len(chunk)}/{len(updates)}")

    logger.info("Backfill complete")


if __name__ == "__main__":
    main()
