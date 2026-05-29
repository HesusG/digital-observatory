"""Append-only event log for agent interactions.

Every agent transition (Tess scored, Carla drafted, Edu's verdict, Pablo
published, user approved/skipped) is recorded as an immutable row. Unlike the
`drafts` collection — which holds current *state* and is overwritten on each
revise loop — this log preserves the full *timeline* of what happened.

Storage mirrors observatory/storage/state.py: a connect-per-call SQLite store
sharing the same `data/state.db` file (the `events` and `state` tables coexist).
`append()` also notifies an in-process bus so the SSE stream can fan out live
events; the bus is notification-only — SQLite remains the source of truth.
"""
import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from config.settings import settings

logger = logging.getLogger(__name__)

# Canonical event types (reference; not enforced at write time).
EVENT_TYPES = frozenset({
    "tess.scored", "tess.skipped",
    "carla.drafted",
    "edu.approved", "edu.revise", "edu.reject",
    "pablo.published", "pablo.failed",
    "user.approved", "user.skipped", "user.edited",
})

_COLUMNS = (
    "seq", "id", "ts", "agent", "event_type",
    "item_url", "draft_id", "platform", "lang", "run_id", "payload",
)


class EventBus:
    """In-process pub/sub for SSE fan-out. Each subscriber gets a bounded queue;
    publish never blocks — it drops on a full queue (the client recovers missed
    events via its next since_seq query)."""

    def __init__(self, maxsize: int = 100):
        self.maxsize = maxsize
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self.maxsize)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow/dead subscriber; it will catch up via since_seq


# Module-level bus shared by the singleton EventLog and the SSE endpoint.
_BUS = EventBus()


class EventLog:
    def __init__(self, db_path: Path | str | None = None, bus: EventBus | None = None):
        self.db_path = str(db_path or settings.state_db_path)
        self.bus = bus if bus is not None else _BUS
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "  seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  id TEXT NOT NULL,"
                "  ts TEXT NOT NULL,"
                "  agent TEXT NOT NULL,"
                "  event_type TEXT NOT NULL,"
                "  item_url TEXT,"
                "  draft_id TEXT,"
                "  platform TEXT,"
                "  lang TEXT,"
                "  run_id TEXT,"
                "  payload TEXT"
                ")"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id)")

    def append(
        self,
        agent: str,
        event_type: str,
        *,
        item_url: Optional[str] = None,
        draft_id: Optional[str] = None,
        platform: Optional[str] = None,
        lang: Optional[str] = None,
        run_id: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> dict:
        ev_id = uuid4().hex
        ts = datetime.utcnow().isoformat()
        payload_json = json.dumps(payload, ensure_ascii=False) if payload is not None else None
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO events "
                "(id, ts, agent, event_type, item_url, draft_id, platform, lang, run_id, payload) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ev_id, ts, agent, event_type, item_url, draft_id, platform, lang, run_id, payload_json),
            )
            seq = cur.lastrowid
        event = {
            "seq": seq, "id": ev_id, "ts": ts, "agent": agent, "event_type": event_type,
            "item_url": item_url, "draft_id": draft_id, "platform": platform,
            "lang": lang, "run_id": run_id, "payload": payload,
        }
        try:
            self.bus.publish(event)
        except Exception:  # bus must never break a write
            logger.exception("event bus publish failed for seq=%s", seq)
        return event

    def list(
        self,
        since_seq: int = 0,
        limit: int = 200,
        agent: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> list[dict]:
        query = (
            "SELECT seq, id, ts, agent, event_type, item_url, draft_id, "
            "platform, lang, run_id, payload FROM events WHERE seq > ?"
        )
        params: list = [since_seq]
        if agent:
            query += " AND agent = ?"
            params.append(agent)
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        query += " ORDER BY seq ASC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def latest_seq(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT MAX(seq) FROM events").fetchone()
        return row[0] or 0

    @staticmethod
    def _row_to_dict(row) -> dict:
        d = dict(zip(_COLUMNS, row))
        if d.get("payload"):
            try:
                d["payload"] = json.loads(d["payload"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d


# ---- Module-level singleton + thin wrappers (emission points import these) ----

_LOG: Optional[EventLog] = None


def _log() -> EventLog:
    global _LOG
    if _LOG is None:
        _LOG = EventLog()
    return _LOG


def append_event(agent: str, event_type: str, **kwargs) -> dict:
    return _log().append(agent, event_type, **kwargs)


def list_events(since_seq: int = 0, limit: int = 200,
                agent: Optional[str] = None, run_id: Optional[str] = None) -> list[dict]:
    return _log().list(since_seq=since_seq, limit=limit, agent=agent, run_id=run_id)


def latest_seq() -> int:
    return _log().latest_seq()


def bus() -> EventBus:
    return _BUS
