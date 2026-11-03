"""Unit tests for date shifts, milestone impact, and IST/ET timezone handover math."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from clerk.domain.dates import (
    compute_shift_days,
    format_handover_window,
    format_month_day,
    is_autopilot_window,
    next_handover,
    parse_hhmm,
    shift_due_date,
    to_agency_time,
    to_client_time,
)
from clerk.domain.models import Plan, ScheduleConfig


@pytest.mark.parametrize(
    ("hours", "expected_shift_days", "expected_new_due"),
    [
        (200, 12, "2026-12-24"),
        (56, 3, "2026-12-15"),
        (3, 0, "2026-12-12"),
        (0, 0, "2026-12-12"),
        (-5, 0, "2026-12-12"),
        (40, 2, "2026-12-14"),
        (20, 1, "2026-12-13"),
    ],
)
def test_compute_shift_days_and_due_dates(
    plan: Plan,
    hours: int,
    expected_shift_days: int,
    expected_new_due: str,
) -> None:
    """Verify exact shift days and new due dates for M2 (due 2026-12-12)."""
    shift = compute_shift_days(hours, plan.capacity_hours_per_week)
    assert shift == expected_shift_days
    assert shift_due_date("2026-12-12", shift) == expected_new_due


def test_compute_shift_days_validation() -> None:
    """Verify error handling for non-positive weekly capacity."""
    with pytest.raises(ValueError, match="positive"):
        compute_shift_days(10, 0)


def test_format_month_day_and_shift_due_date() -> None:
    """Verify calendar day shifting and 'Month D' formatting."""
    assert shift_due_date("2026-12-12", 12) == "2026-12-24"
    assert shift_due_date("2026-12-25", 10) == "2027-01-04"
    assert format_month_day("2026-12-12") == "December 12"
    assert format_month_day("2026-12-24") == "December 24"


def test_timezone_conversion_and_handover_window(schedule_config: ScheduleConfig) -> None:
    """Verify IST <-> ET conversions and dual-timezone handover string."""
    tz = ZoneInfo(schedule_config.agency_timezone)
    dt_ist = datetime(2026, 11, 5, 19, 0, tzinfo=tz)
    dt_et = to_client_time(dt_ist, schedule_config)
    assert dt_et.hour == 8
    assert dt_et.minute == 30
    assert to_agency_time(dt_et, schedule_config).hour == 19

    # Naive datetime raises ValueError
    with pytest.raises(ValueError, match="timezone-aware"):
        to_agency_time(datetime(2026, 11, 5, 19, 0), schedule_config)
    with pytest.raises(ValueError, match="timezone-aware"):
        to_client_time(datetime(2026, 11, 5, 19, 0), schedule_config)

    window_str = format_handover_window(dt_ist, schedule_config)
    assert window_str == "09:30 IST (11:00 PM ET)"


def test_parse_hhmm_validation() -> None:
    """Verify HH:MM parsing and invalid format error."""
    assert parse_hhmm("19:00").hour == 19
    with pytest.raises(ValueError, match="Expected HH:MM"):
        parse_hhmm("1900")


def test_autopilot_window_and_next_handover(schedule_config: ScheduleConfig) -> None:
    """Verify day vs night autopilot windows (19:00 IST -> 09:30 IST) and next handover."""
    tz = ZoneInfo(schedule_config.agency_timezone)

    # 18:55 IST -> daytime (Priya / copilot)
    dt_day = datetime(2026, 11, 5, 18, 55, tzinfo=tz)
    assert is_autopilot_window(dt_day, schedule_config) is False
    handover_at, holder = next_handover(dt_day, schedule_config)
    assert holder == "scout"
    assert handover_at.isoformat() == "2026-11-05T19:00:00+05:30"
    assert format_handover_window(dt_day, schedule_config) == "09:30 IST (11:00 PM ET)"

    # 19:00 IST -> evening handover (Scout / autopilot)
    dt_evening = datetime(2026, 11, 5, 19, 0, tzinfo=tz)
    assert is_autopilot_window(dt_evening, schedule_config) is True
    handover_at_2, holder_2 = next_handover(dt_evening, schedule_config)
    assert holder_2 == "priya"
    assert handover_at_2.isoformat() == "2026-11-06T09:30:00+05:30"

    # 02:15 IST (next morning before 09:30) -> still Scout / autopilot
    dt_late_night = datetime(2026, 11, 6, 2, 15, tzinfo=tz)
    assert is_autopilot_window(dt_late_night, schedule_config) is True
    handover_at_3, holder_3 = next_handover(dt_late_night, schedule_config)
    assert holder_3 == "priya"
    assert handover_at_3.isoformat() == "2026-11-06T09:30:00+05:30"
