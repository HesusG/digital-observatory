import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from observatory.collectors.wordpress import WordPressCollector


@pytest.fixture
def wp_config(tmp_path):
    config = tmp_path / "wp.yaml"
    config.write_text("""sites:
  - name: TestSite
    base_url: https://test.example.com
    enabled: true
  - name: DisabledSite
    base_url: https://disabled.example.com
    enabled: false
""")
    return config


def test_loads_enabled_sites_only(wp_config):
    collector = WordPressCollector(config_path=wp_config)
    assert len(collector.sites) == 1
    assert collector.sites[0]["name"] == "TestSite"


def test_missing_config_file():
    collector = WordPressCollector(config_path=Path("/nonexistent.yaml"))
    assert collector.sites == []


SAMPLE_WP_RESPONSE = [
    {
        "link": "https://test.example.com/opp/1",
        "title": {"rendered": "AI Fellowship 2026"},
        "content": {"rendered": "<p>Apply now for this AI fellowship.</p>"},
        "excerpt": {"rendered": "<p>Short desc</p>"},
        "meta": {},
    }
]


@pytest.mark.asyncio
@patch("observatory.collectors.wordpress.httpx.AsyncClient")
async def test_collect_returns_items(mock_client_cls, wp_config):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_WP_RESPONSE

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    collector = WordPressCollector(config_path=wp_config, keywords=["AI"], delay_range=(0, 0))
    items = await collector.collect()

    assert len(items) == 1
    assert items[0].title == "AI Fellowship 2026"
    assert items[0].source == "TestSite"
    assert items[0].source_type == "wordpress"
    assert "Apply now" in items[0].raw_text


@pytest.mark.asyncio
@patch("observatory.collectors.wordpress.httpx.AsyncClient")
async def test_collect_handles_rate_limit(mock_client_cls, wp_config):
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = SAMPLE_WP_RESPONSE

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[rate_limit_response, ok_response])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    collector = WordPressCollector(config_path=wp_config, keywords=["AI"], delay_range=(0, 0))
    items = await collector.collect()

    assert len(items) == 1
