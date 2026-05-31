import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config.settings import settings
from observatory.timefmt import fmt_cdmx

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


TOP_HIGHLIGHT_COUNT = 10
LONG_TAIL_MAX = 90           # extra rows after the top — keeps total HTML well under Gmail clip
WHY_SNIPPET_CHARS = 140


def _why_snippet(item: dict) -> str:
    """Short blurb explaining the score, for the long-tail list."""
    src = item.get("reasoning") or item.get("summary") or ""
    src = " ".join(src.split())  # collapse whitespace
    if len(src) <= WHY_SNIPPET_CHARS:
        return src
    return src[: WHY_SNIPPET_CHARS - 1].rstrip() + "…"


def render_weekly_digest(items: list[dict]) -> str:
    """Sort items by score desc, split into highlighted top and compact tail.
    The tail items each get a short 'why' snippet derived from the LLM's
    reasoning / summary fields so the user can skim them without clicking."""
    sorted_items = sorted(
        items,
        key=lambda it: (int(it.get("score", 0) or 0), it.get("title", "")),
        reverse=True,
    )
    top = sorted_items[:TOP_HIGHLIGHT_COUNT]
    # Long tail: skip zero-score (unevaluated noise) then cap by count so the
    # whole email stays under Gmail's 102KB clip threshold.
    long_tail_candidates = [
        it for it in sorted_items[TOP_HIGHLIGHT_COUNT:]
        if int(it.get("score", 0) or 0) > 0
    ]
    rest = long_tail_candidates[:LONG_TAIL_MAX]
    for it in rest:
        it["why"] = _why_snippet(it)
    overflow = max(0, len(long_tail_candidates) - len(rest))

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("weekly_digest.html")
    return template.render(
        items=sorted_items,
        top=top,
        rest=rest,
        total=len(sorted_items),
        top_count=len(top),
        rest_count=len(rest),
        overflow_count=overflow,
    )


async def send_weekly_email(
    items: list[dict],
    smtp_server: str | None = None,
    smtp_port: int | None = None,
    sender: str | None = None,
    password: str | None = None,
    receiver: str | None = None,
) -> bool:
    smtp_server = smtp_server if smtp_server is not None else settings.smtp_server
    smtp_port = smtp_port if smtp_port is not None else settings.smtp_port
    sender = sender if sender is not None else settings.email_sender
    password = password if password is not None else settings.email_password
    receiver = receiver if receiver is not None else settings.email_receiver

    if not all([smtp_server, sender, password, receiver]):
        logger.warning("Email not configured. Skipping weekly digest.")
        return False

    html = render_weekly_digest(items)

    # Also build a plain-text fallback for clients that can't render HTML.
    sorted_items = sorted(
        items, key=lambda it: int(it.get("score", 0) or 0), reverse=True
    )
    plain_lines = [
        f"Radar de Oportunidades — {len(items)} en los últimos "
        f"{settings.weekly_email_interval_days} días.",
        f"Generado: {fmt_cdmx()}",
        "",
        "TOP HIGHLIGHTS:",
    ]
    for it in sorted_items[:TOP_HIGHLIGHT_COUNT]:
        plain_lines.append(
            f"  [{it.get('score', 0)}/10] {it.get('title', '')}  ({it.get('source','')})"
        )
        plain_lines.append(f"    {it.get('url', '')}")
    plain_text = "\n".join(plain_lines)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"Radar de Oportunidades: top {min(len(items), TOP_HIGHLIGHT_COUNT)} de {len(items)}"
    )
    msg["From"] = sender
    msg["To"] = receiver
    # Order matters in multipart/alternative — last attached = preferred by client.
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    def _send():
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

    try:
        await asyncio.to_thread(_send)
        logger.info(f"Weekly email sent to {receiver} with {len(items)} opportunities.")
        return True
    except Exception as e:
        logger.error(f"Failed to send weekly email: {e}")
        return False
