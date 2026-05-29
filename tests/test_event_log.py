import asyncio

import pytest

from observatory.storage.event_log import EventBus, EventLog


def _log(tmp_path) -> EventLog:
    # Isolated bus per instance so tests don't cross-talk via the module singleton.
    return EventLog(tmp_path / "state.db", bus=EventBus())


def test_append_returns_full_event(tmp_path):
    log = _log(tmp_path)
    ev = log.append(
        "tess", "tess.scored",
        item_url="https://x/y", run_id="run1", payload={"score": 8},
    )
    assert ev["seq"] >= 1
    assert ev["id"] and ev["ts"]
    assert ev["agent"] == "tess"
    assert ev["event_type"] == "tess.scored"
    assert ev["item_url"] == "https://x/y"
    assert ev["run_id"] == "run1"
    assert ev["payload"] == {"score": 8}


def test_seq_is_monotonic_increasing(tmp_path):
    log = _log(tmp_path)
    a = log.append("tess", "tess.scored")
    b = log.append("carla", "carla.drafted")
    c = log.append("edu", "edu.approved")
    assert a["seq"] < b["seq"] < c["seq"]


def test_payload_round_trips_as_json(tmp_path):
    log = _log(tmp_path)
    log.append("edu", "edu.revise", payload={"reasoning": "trim it", "fail": ["platform"]})
    rows = log.list()
    assert rows[-1]["payload"] == {"reasoning": "trim it", "fail": ["platform"]}


def test_list_since_seq_excludes_seen(tmp_path):
    log = _log(tmp_path)
    a = log.append("tess", "tess.scored")
    b = log.append("carla", "carla.drafted")
    rows = log.list(since_seq=a["seq"])
    assert [r["seq"] for r in rows] == [b["seq"]]


def test_list_filters_by_agent(tmp_path):
    log = _log(tmp_path)
    log.append("tess", "tess.scored")
    log.append("carla", "carla.drafted")
    log.append("tess", "tess.skipped")
    rows = log.list(agent="tess")
    assert {r["event_type"] for r in rows} == {"tess.scored", "tess.skipped"}
    assert all(r["agent"] == "tess" for r in rows)


def test_list_filters_by_run_id(tmp_path):
    log = _log(tmp_path)
    log.append("tess", "tess.scored", run_id="A")
    log.append("tess", "tess.scored", run_id="B")
    rows = log.list(run_id="B")
    assert [r["run_id"] for r in rows] == ["B"]


def test_list_respects_limit_and_order(tmp_path):
    log = _log(tmp_path)
    for i in range(5):
        log.append("tess", "tess.scored", payload={"i": i})
    rows = log.list(limit=3)
    assert len(rows) == 3
    assert [r["payload"]["i"] for r in rows] == [0, 1, 2]  # oldest-first


def test_latest_seq(tmp_path):
    log = _log(tmp_path)
    assert log.latest_seq() == 0
    log.append("tess", "tess.scored")
    last = log.append("carla", "carla.drafted")
    assert log.latest_seq() == last["seq"]


def test_append_publishes_to_bus(tmp_path):
    bus = EventBus()
    log = EventLog(tmp_path / "state.db", bus=bus)
    q = bus.subscribe()
    ev = log.append("pablo", "pablo.published", draft_id="d1")
    got = q.get_nowait()
    assert got["seq"] == ev["seq"]
    assert got["event_type"] == "pablo.published"


def test_bus_drops_when_full_never_raises(tmp_path):
    bus = EventBus()
    log = EventLog(tmp_path / "state.db", bus=bus)
    q = bus.subscribe()
    # Fill the subscriber queue past its bound; append must not raise.
    for _ in range(bus.maxsize + 10):
        log.append("tess", "tess.scored")
    assert q.qsize() == bus.maxsize  # capped, no crash


def test_module_wrappers_use_singleton(tmp_path, monkeypatch):
    from observatory.storage import event_log as el
    monkeypatch.setattr(el, "_LOG", EventLog(tmp_path / "state.db", bus=EventBus()))
    el.append_event("tess", "tess.scored", payload={"ok": True})
    rows = el.list_events()
    assert rows[-1]["event_type"] == "tess.scored"
    assert el.latest_seq() == rows[-1]["seq"]
