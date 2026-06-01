from datetime import datetime, timezone

from observatory.timefmt import fmt_cdmx


def test_naive_utc_converted_to_cdmx_minus6():
    # 2026-05-31 22:17 UTC -> 16:17 CDMX (UTC-6)
    s = fmt_cdmx(datetime(2026, 5, 31, 22, 17))
    assert s == "31 may 2026, 16:17 (CDMX)"


def test_aware_utc_also_works():
    s = fmt_cdmx(datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))
    # 03:00 UTC -> 21:00 previous day CDMX
    assert s == "31 dic 2025, 21:00 (CDMX)"
