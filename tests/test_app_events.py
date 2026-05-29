import pytest
from fastapi.testclient import TestClient

from observatory.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_events_shape_and_filter_forwarding(client, monkeypatch):
    from observatory.storage import event_log

    captured = {}

    def fake_list(since_seq=0, limit=200, agent=None, run_id=None):
        captured.update(since_seq=since_seq, limit=limit, agent=agent, run_id=run_id)
        return [{"seq": 5, "agent": "tess", "event_type": "tess.scored"}]

    monkeypatch.setattr(event_log, "list_events", fake_list)
    monkeypatch.setattr(event_log, "latest_seq", lambda: 5)

    r = client.get("/api/events?since_seq=3&agent=tess&run_id=R&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["latest_seq"] == 5
    assert body["events"][0]["event_type"] == "tess.scored"
    # Empty-string query params become None filters.
    assert captured == {"since_seq": 3, "limit": 10, "agent": "tess", "run_id": "R"}


def test_get_events_blank_agent_passes_none(client, monkeypatch):
    from observatory.storage import event_log
    captured = {}
    monkeypatch.setattr(event_log, "list_events",
                        lambda **kw: captured.update(kw) or [])
    monkeypatch.setattr(event_log, "latest_seq", lambda: 0)
    r = client.get("/api/events")
    assert r.status_code == 200
    assert captured["agent"] is None and captured["run_id"] is None


def test_get_events_rejects_unknown_agent(client):
    r = client.get("/api/events?agent=bogus")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_event_stream_replays_backlog_then_exits_on_disconnect(monkeypatch):
    """The SSE generator replays stored events (id: + data: lines) and exits
    cleanly once the client disconnects — no infinite hang."""
    from observatory import app as appmod

    monkeypatch.setattr(
        appmod.event_log, "list_events",
        lambda since_seq=0, limit=1000: [
            {"seq": 1, "agent": "tess", "event_type": "tess.scored"},
            {"seq": 2, "agent": "carla", "event_type": "carla.drafted"},
        ],
    )

    class FakeRequest:
        headers: dict = {}

        async def is_disconnected(self):
            return True  # bus loop exits immediately after the replay

    chunks = [c async for c in appmod._event_stream(FakeRequest(), 0)]
    blob = "".join(chunks)
    assert "id: 1" in blob and "id: 2" in blob
    assert "tess.scored" in blob and "carla.drafted" in blob
