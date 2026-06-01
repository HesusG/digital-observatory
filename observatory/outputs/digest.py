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


def _format_drafts_notice(drafts: list[dict]) -> str:
    """Summary message for article drafts awaiting the user's approval."""
    from collections import Counter

    by_platform = Counter(
        str((d.get("metadata") or {}).get("platform", "?")) for d in drafts
    )
    parts = ", ".join(f"{n} {p}" for p, n in by_platform.items())
    lines = [
        f"📝 <b>{len(drafts)} borradores listos para revisar</b>",
        f"🕐 {_e(fmt_cdmx())}",
        "",
        _e(parts),
        "",
        "Ábrelos en la pestaña <b>Bandeja</b> del cuarto.",
    ]
    return "\n".join(lines).strip()


async def send_drafts_awaiting_notice(drafts: list[dict]) -> bool:
    """Notify Telegram that article drafts are awaiting approval. Returns False
    when there's nothing pending."""
    if not drafts:
        return False
    return await _send_message(_format_drafts_notice(drafts))


async def send_daily_opportunity_digest(items: list[dict]) -> bool:
    """items: [{title, url, score}]. Sends a single Telegram message with the
    day's top opportunities. Returns True if sent, False if nothing qualified."""
    top = pick_top_opportunities(
        items, settings.daily_digest_top_n, settings.high_affinity_threshold
    )
    if not top:
        return False
    return await _send_message(_format_digest(top))
