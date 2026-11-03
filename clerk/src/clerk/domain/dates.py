"""Deterministic date-shift math and timezone conversions (IST / ET)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from clerk.domain.models import ScheduleConfig


def compute_shift_days(hours: int | Decimal, capacity_hours_per_week: int) -> int:
    """Compute calendar days added to a milestone for a given hour estimate.

    Formula: round_half_up(hours / capacity_hours_per_week * 7)
    Examples (capacity = 120):
      - 200 h -> 200 / 120 * 7 = 11.666... -> 12 days
      - 56 h  -> 56 / 120 * 7  = 3.266...  -> 3 days
      - 3 h   -> 3 / 120 * 7   = 0.175     -> 0 days
    """
    if capacity_hours_per_week <= 0:
        raise ValueError("capacity_hours_per_week must be positive")
    if hours <= 0:
        return 0
    raw = (Decimal(str(hours)) / Decimal(str(capacity_hours_per_week))) * Decimal("7")
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def shift_due_date(due_iso: str, shift_days: int) -> str:
    """Add `shift_days` calendar days to an ISO-8601 date string (YYYY-MM-DD)."""
    base = date.fromisoformat(due_iso)
    shifted = base + timedelta(days=shift_days)
    return shifted.isoformat()


def format_month_day(due_iso: str) -> str:
    """Format an ISO date (YYYY-MM-DD) as 'Month D', e.g. 'December 12'."""
    d = date.fromisoformat(due_iso)
    return f"{d.strftime('%B')} {d.day}"


def parse_hhmm(hhmm: str) -> time:
    """Parse an 'HH:MM' 24-hour string into a datetime.time object."""
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Expected HH:MM time string, got {hhmm!r}")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def to_agency_time(dt: datetime, schedule: ScheduleConfig) -> datetime:
    """Convert a timezone-aware datetime to the agency timezone (Asia/Kolkata)."""
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(ZoneInfo(schedule.agency_timezone))


def to_client_time(dt: datetime, schedule: ScheduleConfig) -> datetime:
    """Convert a timezone-aware datetime to the client timezone (America/New_York)."""
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(ZoneInfo(schedule.client_timezone))


def is_autopilot_window(now: datetime, schedule: ScheduleConfig) -> bool:
    """Return True if `now` falls within the overnight agent autopilot window.

    In default schedule: 19:00 IST to 09:30 IST next morning.
    """
    agency_now = to_agency_time(now, schedule)
    to_agent = parse_hhmm(schedule.flip.to_agent_at)
    to_person = parse_hhmm(schedule.flip.to_person_at)
    current_t = agency_now.timetz().replace(tzinfo=None)
    if to_agent > to_person:
        # Overnight window crossing midnight (e.g., 19:00 -> 09:30)
        return current_t >= to_agent or current_t < to_person
    return to_agent <= current_t < to_person


def next_handover(
    now: datetime, schedule: ScheduleConfig
) -> tuple[datetime, Literal["priya", "scout"]]:
    """Compute the next shift handover timestamp (in agency timezone) and next holder."""
    agency_tz = ZoneInfo(schedule.agency_timezone)
    agency_now = to_agency_time(now, schedule)
    to_agent = parse_hhmm(schedule.flip.to_agent_at)
    to_person = parse_hhmm(schedule.flip.to_person_at)
    current_t = agency_now.timetz().replace(tzinfo=None)

    if is_autopilot_window(now, schedule):
        # Currently held by scout; next handover is to_person (priya) at 09:30 IST
        target_date = (
            agency_now.date() + timedelta(days=1)
            if current_t >= to_agent
            else agency_now.date()
        )
        handover_dt = datetime.combine(target_date, to_person, tzinfo=agency_tz)
        return handover_dt, "priya"

    # Currently held by priya; next handover is to_agent (scout) at 19:00 IST today
    handover_dt = datetime.combine(agency_now.date(), to_agent, tzinfo=agency_tz)
    return handover_dt, "scout"


def format_handover_window(now: datetime, schedule: ScheduleConfig) -> str:
    """Format the autopilot window end in both IST and ET for the MODE autopilot command.

    Example: '09:30 IST (11:00 PM ET)'
    """
    handover_dt, _ = next_handover(now, schedule)
    if not is_autopilot_window(now, schedule):
        # If called just before or at evening flip, compute morning end time
        agency_tz = ZoneInfo(schedule.agency_timezone)
        agency_now = to_agency_time(now, schedule)
        to_person = parse_hhmm(schedule.flip.to_person_at)
        handover_dt = datetime.combine(
            agency_now.date() + timedelta(days=1), to_person, tzinfo=agency_tz
        )
    ist_str = handover_dt.strftime("%H:%M")
    et_dt = to_client_time(handover_dt, schedule)
    et_str = et_dt.strftime("%I:%M %p").lstrip("0")
    return f"{ist_str} IST ({et_str} ET)"
