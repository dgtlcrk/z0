"""UTC time and duration helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(tz=UTC)


def isoformat_utc(value: datetime | None = None) -> str:
    """Return a normalized UTC ISO-8601 timestamp."""

    selected = utc_now() if value is None else value

    if selected.tzinfo is None:
        selected = selected.replace(tzinfo=UTC)
    else:
        selected = selected.astimezone(UTC)

    return selected.isoformat()


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC."""

    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def total_seconds(
    value: timedelta | int | float,
) -> int:
    """Return a non-negative whole-second duration."""

    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
    else:
        seconds = int(value)

    return max(0, seconds)


def human_duration(
    value: timedelta | int | float,
) -> str:
    """Format a compact human-readable duration."""

    seconds = total_seconds(value)

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    parts: list[str] = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if remaining_seconds or not parts:
        parts.append(f"{remaining_seconds}s")

    return " ".join(parts)
