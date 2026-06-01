"""Time formatting helpers for user-facing notifications.

Mexico City stopped observing DST in 2022, so it is a fixed UTC-6 year-round.
Using a fixed offset avoids depending on the `tzdata` package inside the
container (which may be absent and would raise ZoneInfoNotFoundError)."""

from datetime import datetime, timedelta, timezone

CDMX = timezone(timedelta(hours=-6))

_MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


def now_utc() -> datetime:
    """Timezone-aware current UTC time (replaces deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)


def cdmx_date() -> "datetime.date":
    """Today's date in Mexico City local time (for once-per-day idempotency)."""
    return datetime.now(CDMX).date()


def deadline_label(deadline_iso: str) -> str:
    """Human label for an ISO 'YYYY-MM-DD' deadline relative to today (CDMX).
    Returns '' for empty/unparseable input. Examples: 'cierra hoy',
    'cierra mañana', 'cierra en 5 días', 'cerró hace 2 días'."""
    if not deadline_iso:
        return ""
    try:
        d = datetime.strptime(deadline_iso.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return ""
    days = (d - cdmx_date()).days
    if days < 0:
        n = -days
        return f"cerró hace {n} día" + ("" if n == 1 else "s")
    if days == 0:
        return "cierra hoy"
    if days == 1:
        return "cierra mañana"
    return f"cierra en {days} días"


def fmt_cdmx(dt_utc: datetime | None = None) -> str:
    """Format a UTC datetime as Mexico City local time, e.g. '31 may 2026, 16:17 (CDMX)'.
    A naive datetime is assumed to be UTC (matching datetime.utcnow())."""
    if dt_utc is None:
        dt_utc = now_utc()
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    local = dt_utc.astimezone(CDMX)
    return f"{local.day} {_MESES[local.month - 1]} {local.year}, {local:%H:%M} (CDMX)"
