from datetime import timedelta

from observatory.timefmt import deadline_label, cdmx_date


def _iso(days_from_today: int) -> str:
    return (cdmx_date() + timedelta(days=days_from_today)).isoformat()


def test_empty_and_garbage():
    assert deadline_label("") == ""
    assert deadline_label("not-a-date") == ""


def test_relative_labels():
    assert deadline_label(_iso(0)) == "cierra hoy"
    assert deadline_label(_iso(1)) == "cierra mañana"
    assert deadline_label(_iso(5)) == "cierra en 5 días"
    assert deadline_label(_iso(-1)) == "cerró hace 1 día"
    assert deadline_label(_iso(-3)) == "cerró hace 3 días"


def test_alert_includes_deadline():
    from observatory.outputs.telegram import format_alert_message
    msg = format_alert_message("T", "u", "S", 9, "s", "scholarship", deadline=_iso(2))
    assert "cierra en 2 días" in msg
