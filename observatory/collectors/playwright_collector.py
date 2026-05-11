import asyncio
import logging
import random
import time
from datetime import datetime

from observatory.collectors.base import BaseCollector
from observatory.storage.models import CollectedItem

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
)

SITE_CONFIGS = {
    "finland": {
        "name": "Studyinfo.fi",
        "search_url": "https://opintopolku.fi/konfo/en/haku?keyword={query}",
        "link_pattern": "/konfo/en/toteutus/,/konfo/en/koulutus/",
        "base_domain": "https://opintopolku.fi",
        "max_detail_pages": 3,
        "default_query": "artificial intelligence",
    },
    "canada": {
        "name": "EduCanada",
        "search_url": "https://www.educanada.ca/scholarships-bourses/non_can/search-recherche.aspx?sk={query}",
        "link_pattern": "/scholarships-bourses/",
        "base_domain": "https://www.educanada.ca",
        "max_detail_pages": 5,
        "default_query": "artificial intelligence education",
    },
    "germany": {
        "name": "DAAD.de",
        "search_url": "https://www2.daad.de/deutschland/studienangebote/studiengang/en/?a=result&q={query}&degree%5B%5D=3&fos=4&sc=1",
        "link_pattern": "/studiengang/,detail",
        "base_domain": "https://www2.daad.de",
        "max_detail_pages": 5,
        "default_query": "artificial intelligence",
    },
}


class PlaywrightCollector(BaseCollector):
    name = "playwright"
    source_type = "playwright"

    def __init__(self, enabled_sites: list[str] | None = None):
        self.enabled_sites = enabled_sites or list(SITE_CONFIGS.keys())

    async def collect(self) -> list[CollectedItem]:
        if sync_playwright is None:
            logger.warning("Playwright not installed. Skipping browser-based scrapers.")
            return []
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> list[CollectedItem]:
        items = []
        for site_key in self.enabled_sites:
            config = SITE_CONFIGS.get(site_key)
            if not config:
                continue
            try:
                site_items = self._scrape_site(config)
                items.extend(site_items)
            except Exception as e:
                logger.error(f"Error scraping {config['name']}: {e}")
        return items

    def _scrape_site(self, config: dict) -> list[CollectedItem]:
        results = []
        query = config["default_query"]
        search_url = config["search_url"].format(query=query.replace(" ", "+"))

        logger.info(f"[Playwright] Opening browser for {config['name']}: {search_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=BROWSER_UA)
            page = context.new_page()

            try:
                page.goto(search_url, wait_until="networkidle", timeout=30000)
                time.sleep(random.uniform(2.0, 4.0))

                html = page.content()
                if BeautifulSoup is None:
                    logger.warning("BeautifulSoup not installed, cannot parse links")
                    return results

                soup = BeautifulSoup(html, "html.parser")
                patterns = [p.strip() for p in config["link_pattern"].split(",")]

                urls = set()
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(pat in href for pat in patterns):
                        full_url = href if href.startswith("http") else f"{config['base_domain']}{href}"
                        urls.add(full_url)

                logger.info(f"[Playwright] {config['name']}: {len(urls)} links found")

                for url in list(urls)[: config["max_detail_pages"]]:
                    try:
                        page.goto(url, wait_until="networkidle", timeout=20000)
                        time.sleep(random.uniform(1.0, 3.0))
                        raw_text = page.locator("body").inner_text()
                        title = page.title()

                        results.append(
                            CollectedItem(
                                url=url,
                                title=title,
                                source=config["name"],
                                source_type="playwright",
                                raw_text=raw_text,
                                collected_at=datetime.utcnow(),
                                metadata={"scrape_method": "playwright"},
                            )
                        )
                        logger.info(f"  -> Extracted: {title[:50]}...")
                    except Exception as e:
                        logger.error(f"Error visiting {url}: {e}")
            except Exception as e:
                logger.error(f"Error during {config['name']} scraping: {e}")
            finally:
                browser.close()

        return results
