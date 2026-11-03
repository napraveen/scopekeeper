"""SystemClock and SimulatedClock implementations of ClockPort."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def parse_clock_offset(offset_str: str) -> timedelta:
    """Parse a relative time offset such as '+10h', '+30m', '+2d', or '-1h'."""
    cleaned = offset_str.strip()
    match = re.match(
        r"^([+-]?\d+(?:\.\d+)?)\s*(s|sec|secs|m|min|mins|h|hr|hrs|hours?|d|days?)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"Invalid clock offset {offset_str!r}; expected e.g. '+10h' or '+30m'")
    amount = float(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("s"):
        return timedelta(seconds=amount)
    if unit.startswith("m"):
        return timedelta(minutes=amount)
    if unit.startswith("h"):
        return timedelta(hours=amount)
    return timedelta(days=amount)


class SystemClock:
    """Wall-clock time with an optional offset."""

    def __init__(self, timezone_name: str = "Asia/Kolkata") -> None:
        self._tz = ZoneInfo(timezone_name)
        self._offset = timedelta(0)

    def now(self) -> datetime:
        """Return the current timezone-aware datetime plus any configured offset."""
        return datetime.now(tz=self._tz) + self._offset

    def set_time(self, dt: datetime) -> None:
        """Set the clock offset so `now()` returns `dt`."""
        if dt.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        self._offset = dt.astimezone(self._tz) - datetime.now(tz=self._tz)

    def advance(self, delta: timedelta) -> datetime:
        """Advance the clock offset by `delta`."""
        self._offset += delta
        return self.now()


class SimulatedClock:
    """Deterministic controllable clock for tests and demo mode."""

    def __init__(
        self,
        start_iso: str = "2026-11-05T19:00:00+05:30",
        timezone_name: str = "Asia/Kolkata",
    ) -> None:
        self._tz = ZoneInfo(timezone_name)
        parsed = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=self._tz)
        self._current = parsed.astimezone(self._tz)

    def now(self) -> datetime:
        """Return the simulated timezone-aware datetime."""
        return self._current

    def set_time(self, dt: datetime) -> None:
        """Set the simulated clock to `dt`."""
        if dt.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        self._current = dt.astimezone(self._tz)

    def advance(self, delta: timedelta) -> datetime:
        """Advance the simulated clock by `delta` and return the new time."""
        self._current = self._current + delta
        return self._current
