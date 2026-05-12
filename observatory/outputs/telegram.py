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
    token = token if token is not None else settings.telegram_bot_token
    chat_id = chat_id if chat_id is not None else settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("Telegram not configured. Skipping alert.")
        return False

    message = format_alert_message(title, url, source, score, summary, category)
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(api_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
        return False
