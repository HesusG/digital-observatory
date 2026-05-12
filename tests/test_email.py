import pytest
from unittest.mock import patch, MagicMock
from observatory.outputs.email import render_weekly_digest, send_weekly_email


def test_render_weekly_digest():
    items = [
        {"title": "AI PhD", "source": "DAAD", "category": "scholarship", "score": 9, "url": "https://x.com"},
        {"title": "ML Job", "source": "LinkedIn", "category": "job", "score": 6, "url": "https://y.com"},
    ]
    html = render_weekly_digest(items)
    assert "AI PhD" in html
    assert "ML Job" in html
    assert "2</strong>" in html


def test_render_empty_digest():
    html = render_weekly_digest([])
    assert "0</strong>" in html


@pytest.mark.asyncio
async def test_send_email_not_configured():
    result = await send_weekly_email(
        items=[],
        smtp_server="",
        sender="",
        password="",
        receiver="",
    )
    assert result is False


@pytest.mark.asyncio
@patch("observatory.outputs.email.smtplib.SMTP")
async def test_send_email_success(mock_smtp_cls):
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    items = [{"title": "Test", "source": "S", "category": "general", "score": 5, "url": "https://x.com"}]
    result = await send_weekly_email(
        items=items,
        smtp_server="smtp.test.com",
        smtp_port=587,
        sender="test@test.com",
        password="pass",
        receiver="recv@test.com",
    )
    assert result is True
