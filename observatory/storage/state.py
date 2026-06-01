import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PipelineState:
    def __init__(self, db_path: Path | str = "data/state.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS state "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )

    def get(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM state WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    def set(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (key, value),
            )

    def should_send_weekly_email(self, interval_days: int = 7) -> bool:
        last_sent = self.get("last_weekly_email")
        if not last_sent:
            return True
        last_dt = datetime.fromisoformat(last_sent)
        return (datetime.now() - last_dt).days >= interval_days

    def mark_weekly_email_sent(self):
        self.set("last_weekly_email", datetime.now().isoformat())

    def should_send_daily_digest(self) -> bool:
        # Once per CDMX calendar day. We store the CDMX date string on mark, so
        # the comparison is consistent regardless of the server's UTC clock.
        from observatory.timefmt import cdmx_date

        last = self.get("last_daily_digest_date")
        return last != cdmx_date().isoformat()

    def mark_daily_digest_sent(self):
        from observatory.timefmt import cdmx_date

        self.set("last_daily_digest_date", cdmx_date().isoformat())

    def should_notify_drafts(self, pending_count: int) -> bool:
        """Notify at most once per CDMX day, and only if the number of pending
        drafts increased since the last notice (so a new batch re-pings, but a
        re-run with the same backlog doesn't)."""
        from observatory.timefmt import cdmx_date

        today = cdmx_date().isoformat()
        last_date = self.get("last_drafts_notice_date")
        last_count = int(self.get("last_drafts_notice_count") or 0)
        if last_date == today and pending_count <= last_count:
            return False
        return pending_count > 0

    def mark_drafts_notified(self, pending_count: int):
        from observatory.timefmt import cdmx_date

        self.set("last_drafts_notice_date", cdmx_date().isoformat())
        self.set("last_drafts_notice_count", str(pending_count))
