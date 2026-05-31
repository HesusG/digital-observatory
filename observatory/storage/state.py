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
        last = self.get("last_daily_digest")
        if not last:
            return True
        return datetime.fromisoformat(last).date() < datetime.now().date()

    def mark_daily_digest_sent(self):
        self.set("last_daily_digest", datetime.now().isoformat())
