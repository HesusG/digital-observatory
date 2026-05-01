import logging
from pathlib import Path
from datetime import datetime

import feedparser
import yaml

from observatory.collectors.base import BaseCollector
from observatory.storage.models import CollectedItem

logger = logging.getLogger(__name__)

FEEDS_CONFIG = Path(__file__).parent.parent.parent / "config" / "sources" / "rss_feeds.yaml"


class RSSCollector(BaseCollector):
    name = "rss"
    source_type = "rss"

    def __init__(self, feeds_path: Path | None = None):
        self.feeds_path = feeds_path or FEEDS_CONFIG
        self.feeds: dict[str, list[dict]] = {}
        self._load_feeds()

    def _load_feeds(self):
        if not self.feeds_path.exists():
            logger.warning(f"RSS feeds config not found: {self.feeds_path}")
            return
        with open(self.feeds_path, "r", encoding="utf-8") as f:
            self.feeds = yaml.safe_load(f) or {}

    async def collect(self) -> list[CollectedItem]:
        items = []
        for category, feed_list in self.feeds.items():
            for feed_entry in feed_list:
                url = feed_entry.get("url", "") if isinstance(feed_entry, dict) else feed_entry
                source_name = feed_entry.get("name", url) if isinstance(feed_entry, dict) else url
                try:
                    new_items = self._parse_feed(url, source_name, category)
                    items.extend(new_items)
                except Exception as e:
                    logger.error(f"Error parsing feed {url}: {e}")
        logger.info(f"RSS collector gathered {len(items)} items from {len(self.feeds)} categories")
        return items

    def _parse_feed(self, feed_url: str, source_name: str, category: str) -> list[CollectedItem]:
        parsed = feedparser.parse(feed_url)
        items = []

        for entry in parsed.entries[:10]:
            title = entry.get("title", "Sin título")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")

            raw_text = f"{title}\n\n{summary}\n\n{content}".strip()
            if not link:
                continue

            published = entry.get("published_parsed")
            collected_at = datetime(*published[:6]) if published else datetime.utcnow()

            items.append(CollectedItem(
                url=link,
                title=title,
                source=source_name,
                source_type="rss",
                raw_text=raw_text,
                collected_at=collected_at,
                metadata={"category": category, "feed_url": feed_url},
            ))
        return items
