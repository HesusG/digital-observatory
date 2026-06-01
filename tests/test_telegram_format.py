from observatory.outputs.telegram import format_alert_message, _e
from observatory.outputs.digest import _format_digest


def test_html_escapes_dangerous_chars():
    msg = format_alert_message("A & B <x>", "http://u", "S", 9, "sum & <y>", "cat")
    assert "&amp;" in msg
    assert "&lt;x&gt;" in msg
    # raw unescaped ampersand-x should not appear
    assert "A & B <x>" not in msg


def test_markdown_chars_pass_through_safely():
    # brackets/asterisks/underscores no longer break parsing in HTML mode
    msg = format_alert_message("[Beca] *Fulbright* _2026_ (x)", "http://u", "S", 8, "s", "c")
    assert "[Beca] *Fulbright* _2026_ (x)" in msg


def test_digest_escapes():
    out = _format_digest([{"score": 9, "title": "X & <Y>", "url": "http://u"}])
    assert "&amp;" in out and "&lt;Y&gt;" in out


def test_e_handles_none():
    assert _e(None) == ""
