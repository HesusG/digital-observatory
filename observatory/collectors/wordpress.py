import asyncio
import logging
import random
from datetime import datetime
from html import unescape
from pathlib import Path

import httpx
import yaml

from observatory.collectors.base import BaseCollector
from observatory.storage.models import CollectedItem
from config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "DigitalObservatory/1.0 (educational research; contact: hesusgc@gmail.com)"
}


class WordPressCollector(BaseCollector):
    name = "wordpress"
    source_type = "wordpress"

    def __init__(
        self,
        config_path: Path | None = None,
        keywords: list[str] | None = None,
        delay_range: tuple[float, float] | None = None,
    ):
        self.config_path = config_path or settings.wordpress_config_path
        self.keywords = keywords or settings.wp_default_keywords
        self.delay_range = delay_range if delay_range is not None else (
            settings.wp_request_delay_min,
            settings.wp_request_delay_max,
        )
        self.sites: list[dict] = []
        self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            logger.warning(f"WordPress config not found: {self.config_path}")
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.sites = [s for s in data.get("sites", []) if s.get("enabled", True)]

    async def collect(self) -> list[CollectedItem]:
        items = []
        for site in self.sites:
            try:
                site_items = await self._scrape_site(site)
                items.extend(site_items)
            except Exception as e:
                logger.error(f"Error scraping {site['name']}: {e}")
        logger.info(f"WordPress collector gathered {len(items)} items from {len(self.sites)} sites")
        return items

    async def _scrape_site(self, site: dict) -> list[CollectedItem]:
        base_url = site["base_url"].rstrip("/")
        source_name = site["name"]
        endpoint = f"{base_url}/wp-json/wp/v2/posts"
        seen_urls: set[str] = set()
        results: list[CollectedItem] = []

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0) as client:
            for term in self.keywords:
                params = {"per_page": settings.wp_max_results_per_site, "search": term}

                try:
                    resp = await client.get(endpoint, params=params)

                    if resp.status_code == 429:
                        logger.warning(f"[{source_name}] Rate limited. Retrying after 5s...")
                        await asyncio.sleep(5)
                        resp = await client.get(endpoint, params=params)

                    if resp.status_code != 200:
                        logger.warning(
                            f"[{source_name}] HTTP {resp.status_code} for term='{term}'"
                        )
                        continue

                    posts = resp.json()
                    if not posts:
                        continue

                    for post in posts:
                        item = self._parse_post(post, source_name, seen_urls)
                        if item:
                            results.append(item)

                except httpx.HTTPError as e:
                    logger.error(f"[{source_name}] Request error for term='{term}': {e}")
                    continue

                if self.delay_range[1] > 0:
                    await asyncio.sleep(random.uniform(*self.delay_range))

        logger.info(f"[{source_name}] Collected {len(results)} opportunities")
        return results

    def _parse_post(
        self, post: dict, source_name: str, seen_urls: set[str]
    ) -> CollectedItem | None:
        url = post.get("link", "")
        if not url or url in seen_urls:
            return None
        seen_urls.add(url)

        title_html = post.get("title", {}).get("rendered", "")
        title = unescape(self._strip_html(title_html))

        content_html = post.get("content", {}).get("rendered", "")
        content_text = self._strip_html(content_html)

        excerpt_html = post.get("excerpt", {}).get("rendered", "")
        excerpt = self._strip_html(excerpt_html)

        meta = post.get("meta", {})
        meta_text = ""
        if isinstance(meta, dict):
            for k, v in meta.items():
                if v and str(v).strip():
                    meta_text += f"{k}: {v}\n"

        raw_text = ""
        if meta_text:
            raw_text += meta_text + "\n"
        if excerpt:
            raw_text += f"Excerpt: {excerpt}\n\n"
        raw_text += content_text

        return CollectedItem(
            url=url,
            title=title,
            source=source_name,
            source_type="wordpress",
            raw_text=raw_text,
            collected_at=datetime.utcnow(),
            kind="opportunity",
            source_group="opportunities",
            lang_hint="en",
            metadata={"search_source": "wordpress_rest_api"},
        )

    @staticmethod
    def _strip_html(html: str) -> str:
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
        except ImportError:
            import re
            return re.sub(r"<[^>]+>", "", html).strip()
