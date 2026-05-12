import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config.settings import settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_weekly_digest(items: list[dict]) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("weekly_digest.html")
    return template.render(items=items)


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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Weekly Opportunity Radar: {len(items)} opportunities found"
    msg["From"] = sender
    msg["To"] = receiver
    msg.attach(MIMEText(html, "html"))

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
