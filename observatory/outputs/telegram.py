import logging
from html import escape

import httpx

from config.settings import settings
from observatory.timefmt import fmt_cdmx

logger = logging.getLogger(__name__)

# Telegram HTML parse mode: only & < > are special, and we escape them. This
# avoids the Markdown-injection failures where a scraped title containing
# [ ] * _ ( ) made the API return 400 and the message silently failed.
TELEGRAM_TIMEOUT_SEC = 8.0


def _e(v: object) -> str:
    """Escape a value for Telegram HTML mode."""
    return escape(str(v if v is not None else ""), quote=False)


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
        cat_line = f"🏷️ <b>Categoría:</b> {_e(category.upper())}\n"

    return (
        f"⭐ <b>¡Coincidencia alta! ({_e(score)}/10)</b>\n\n"
        f"📌 <b>{_e(title)}</b>\n\n"
        f"📰 <b>Fuente:</b> {_e(source)}\n"
        f"{cat_line}"
        f"📝 {_e(summary)}\n\n"
        f"🔗 {_e(url)}\n"
        f"🕐 {_e(fmt_cdmx())}"
    )


async def _send_message(
    text: str,
    token: str | None = None,
    chat_id: str | None = None,
) -> bool:
    """Send one HTML message to Telegram. Returns True on success."""
    token = token if token is not None else settings.telegram_bot_token
    chat_id = chat_id if chat_id is not None else settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("Telegram not configured. Skipping message.")
        return False

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT_SEC) as client:
            resp = await client.post(api_url, json=payload)
            resp.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        # 4xx = our content/config problem (won't fix itself); 5xx = Telegram side.
        body = e.response.text[:300] if e.response is not None else ""
        logger.error("Telegram HTTP %s: %s", e.response.status_code, body)
        return False
    except httpx.TimeoutException:
        logger.error("Telegram send timed out after %ss", TELEGRAM_TIMEOUT_SEC)
        return False
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
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
