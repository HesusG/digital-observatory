import pytest
from unittest.mock import patch
from observatory.collectors.playwright_collector import PlaywrightCollector, SITE_CONFIGS


def test_site_configs_defined():
    assert "finland" in SITE_CONFIGS
    assert "canada" in SITE_CONFIGS
    assert "germany" in SITE_CONFIGS


def test_collector_filters_enabled_sites():
    collector = PlaywrightCollector(enabled_sites=["finland", "germany"])
    assert len(collector.enabled_sites) == 2


@pytest.mark.asyncio
async def test_collect_without_playwright_installed():
    with patch("observatory.collectors.playwright_collector.sync_playwright", None):
        collector = PlaywrightCollector(enabled_sites=["finland"])
        items = await collector.collect()
        assert items == []
