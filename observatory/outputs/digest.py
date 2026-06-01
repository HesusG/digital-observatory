import logging

from config.settings import settings
from observatory.outputs.telegram import _e, _send_message
from observatory.timefmt import fmt_cdmx

logger = logging.getLogger(__name__)


def pick_top_opportunities(items: list[dict], n: int, min_score: int) -> list[dict]:
    """Pure: filter items with score >= min_score, sort by score desc, take n."""
    eligible = [i for i in items if int(i.get("score", 0) or 0) >= min_score]
    eligible.sort(key=lambda i: int(i.get("score", 0) or 0), reverse=True)
    return eligible[:n]


def _format_digest(items: list[dict]) -> str:
    # HTML mode (Telegram): escape user-provided fields so scraped titles with
    # < > & don't break parsing.
    lines = [f"📬 <b>Oportunidades destacadas</b> ({len(items)})", f"🕐 {_e(fmt_cdmx())}", ""]
    for i in items:
        lines.append(f"⭐ <b>{_e(i.get('score', 0))}/10</b> — {_e(i.get('title', ''))}")
        if i.get("url"):
            lines.append(_e(i["url"]))
        lines.append("")
    return "\n".join(lines).strip()


async def send_daily_opportunity_digest(items: list[dict]) -> bool:
    """items: [{title, url, score}]. Sends a single Telegram message with the
    day's top opportunities. Returns True if sent, False if nothing qualified."""
    top = pick_top_opportunities(
        items, settings.daily_digest_top_n, settings.high_affinity_threshold
    )
    if not top:
        return False
    return await _send_message(_format_digest(top))
