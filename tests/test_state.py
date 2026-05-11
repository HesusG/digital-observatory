import os
import pytest
from observatory.storage.state import PipelineState


@pytest.fixture
def state(tmp_path):
    db_path = tmp_path / "test_state.db"
    return PipelineState(db_path)


def test_init_creates_tables(state):
    assert state.get("nonexistent") is None


def test_set_and_get(state):
    state.set("last_run", "2026-05-11T10:00:00")
    assert state.get("last_run") == "2026-05-11T10:00:00"


def test_set_overwrites(state):
    state.set("key", "value1")
    state.set("key", "value2")
    assert state.get("key") == "value2"


def test_should_send_weekly_email_true_when_never_sent(state):
    assert state.should_send_weekly_email(interval_days=7) is True


def test_should_send_weekly_email_false_when_recent(state):
    state.mark_weekly_email_sent()
    assert state.should_send_weekly_email(interval_days=7) is False


def test_should_send_weekly_email_true_after_interval(state):
    from datetime import datetime, timedelta
    old_date = (datetime.now() - timedelta(days=8)).isoformat()
    state.set("last_weekly_email", old_date)
    assert state.should_send_weekly_email(interval_days=7) is True
