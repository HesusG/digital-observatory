import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


def format_alert_message(
    title: str,
    url: str,
    source: str,
    score: int,
    summary: str,
    category: str = "general",
) -> str:
    cat_line = ""
    if category and category != "general":
        cat_line = f"*Type:* {category.upper()}\n"

    return (
        f"\U0001f31f *HIGH MATCH! ({score}/10)* \U0001f31f\n\n"
        f"*Source:* {source}\n"
        f"{cat_line}"
        f"*Title:* {title}\n"
        f"*AI Summary:* {summary}\n\n"
        f"\U0001f517 *Link:* {url}"
    )


async def _send_message(
    text: str,
    token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    """Send one Markdown message to Telegram. Returns True on success."""
    token = token if token is not None else settings.telegram_bot_token
    chat_id = chat_id if chat_id is not None else settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("Telegram not configured. Skipping message.")
        return False

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(api_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


async def send_telegram_alert(
    title: str,
    url: str,
    source: str,
    score: int,
    summary: str,
    category: str = "general",
    token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    message = format_alert_message(title, url, source, score, summary, category)
    return await _send_message(message, token=token, chat_id=chat_id)
