import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from observatory.outputs.telegram import format_alert_message, send_telegram_alert


def test_format_alert_message_basic():
    msg = format_alert_message(
        title="AI Fellowship",
        url="https://example.com",
        source="TestSource",
        score=9,
        summary="Great opportunity",
        category="fellowship",
    )
    assert "AI Fellowship" in msg
    assert "9/10" in msg
    assert "FELLOWSHIP" in msg
    assert "https://example.com" in msg


def test_format_alert_message_general_category():
    msg = format_alert_message(
        title="Test", url="https://x.com", source="S", score=8,
        summary="Sum", category="general",
    )
    assert "Type:" not in msg


@pytest.mark.asyncio
@patch("observatory.outputs.telegram.httpx.AsyncClient")
async def test_send_alert_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    result = await send_telegram_alert(
        title="Test", url="https://x.com", source="S", score=9,
        summary="Sum", category="grant",
        token="fake-token", chat_id="123",
    )
    assert result is True


@pytest.mark.asyncio
async def test_send_alert_not_configured():
    result = await send_telegram_alert(
        title="Test", url="https://x.com", source="S", score=9,
        summary="Sum", token="", chat_id="",
    )
    assert result is False
