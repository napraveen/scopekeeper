"""APScheduler + SimulatedClock handover scheduler for 19:00 IST and 09:30 IST shifts."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from clerk.db.tables import RoleShiftRow
from clerk.domain.dates import parse_hhmm
from clerk.domain.models import ScheduleConfig
from clerk.ports.protocols import ClockPort
from clerk.services.change_requests import ChangeRequestService
from clerk.services.flip import FlipService

logger = structlog.get_logger(__name__)


def find_crossed_handover_events(
    prev_dt: datetime,
    curr_dt: datetime,
    schedule: ScheduleConfig,
    *,
    include_exact_start: bool = False,
) -> list[tuple[datetime, Literal["autopilot", "copilot"]]]:
    """Return chronological (timestamp, mode) handover boundaries crossed in (prev_dt, curr_dt]."""
    agency_tz = ZoneInfo(schedule.agency_timezone)
    start_ist = prev_dt.astimezone(agency_tz)
    end_ist = curr_dt.astimezone(agency_tz)
    if end_ist < start_ist:
        return []

    to_agent_t = parse_hhmm(schedule.flip.to_agent_at)
    to_person_t = parse_hhmm(schedule.flip.to_person_at)

    events: list[tuple[datetime, Literal["autopilot", "copilot"]]] = []
    day_cursor = start_ist.date() - timedelta(days=1)
    end_date = end_ist.date() + timedelta(days=1)

    while day_cursor <= end_date:
        evening_dt = datetime.combine(day_cursor, to_agent_t, tzinfo=agency_tz)
        morning_dt = datetime.combine(day_cursor, to_person_t, tzinfo=agency_tz)
        candidates: list[tuple[datetime, Literal["autopilot", "copilot"]]] = [
            (morning_dt, "copilot"),
            (evening_dt, "autopilot"),
        ]
        for boundary_dt, mode in candidates:
            in_window = (
                start_ist <= boundary_dt <= end_ist
                if include_exact_start
                else start_ist < boundary_dt <= end_ist
            )
            if in_window:
                events.append((boundary_dt, mode))
        day_cursor += timedelta(days=1)

    events.sort(key=lambda pair: pair[0])
    return events


class HandoverScheduler:
    """Schedules 19:00 IST and 09:30 IST handovers on APScheduler and SimulatedClock."""

    def __init__(
        self,
        *,
        flip_service: FlipService,
        clock: ClockPort,
        schedule: ScheduleConfig,
        cr_service: ChangeRequestService | None = None,
    ) -> None:
        self._flip_service = flip_service
        self._clock = clock
        self._schedule = schedule
        self._cr_service = cr_service
        self._agency_tz = ZoneInfo(schedule.agency_timezone)
        self._last_checked_dt: datetime = clock.now().astimezone(self._agency_tz)
        self._executed_boundaries: set[str] = set()
        self._apscheduler: AsyncIOScheduler | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Return True if the APScheduler instance is running."""
        return self._running

    @property
    def apscheduler(self) -> AsyncIOScheduler | None:
        """Return the underlying APScheduler AsyncIOScheduler."""
        return self._apscheduler

    def start(self) -> None:
        """Configure and start APScheduler CronTriggers for 19:00 IST and 09:30 IST."""
        if self._running:
            return
        to_agent_t = parse_hhmm(self._schedule.flip.to_agent_at)
        to_person_t = parse_hhmm(self._schedule.flip.to_person_at)

        scheduler = AsyncIOScheduler(timezone=self._agency_tz)
        scheduler.add_job(
            self.trigger_evening_handover,
            CronTrigger(
                hour=to_agent_t.hour,
                minute=to_agent_t.minute,
                timezone=self._agency_tz,
            ),
            id="flip_to_autopilot",
            replace_existing=True,
        )
        scheduler.add_job(
            self.trigger_morning_handover,
            CronTrigger(
                hour=to_person_t.hour,
                minute=to_person_t.minute,
                timezone=self._agency_tz,
            ),
            id="flip_to_copilot",
            replace_existing=True,
        )
        scheduler.start()
        self._apscheduler = scheduler
        self._running = True

    def stop(self) -> None:
        """Shut down the APScheduler instance cleanly."""
        if self._apscheduler is not None and self._running:
            self._apscheduler.shutdown(wait=False)
        self._apscheduler = None
        self._running = False

    async def trigger_evening_handover(self) -> RoleShiftRow:
        """Execute the 19:00 IST handover (`MODE autopilot` -> Scout assumes `@client-desk`)."""
        return await self._flip_service.flip_to_autopilot()

    async def trigger_morning_handover(self) -> RoleShiftRow:
        """Execute the 09:30 IST handover (morning brief + `MODE copilot`)."""
        return await self._flip_service.flip_to_copilot(post_brief=True)

    async def tick(self, *, include_exact_start: bool = False) -> list[RoleShiftRow]:
        """Evaluate current ClockPort time and execute any crossed 19:00 / 09:30 IST handovers."""
        curr_dt = self._clock.now().astimezone(self._agency_tz)
        prev_dt = self._last_checked_dt

        crossed = find_crossed_handover_events(
            prev_dt,
            curr_dt,
            self._schedule,
            include_exact_start=include_exact_start or (prev_dt == curr_dt),
        )
        self._last_checked_dt = curr_dt

        shifts: list[RoleShiftRow] = []
        saved_now = self._clock.now()
        for boundary_dt, mode in crossed:
            key = f"{boundary_dt.isoformat()}::{mode}"
            if key in self._executed_boundaries:
                continue
            self._executed_boundaries.add(key)

            # Set clock to exact boundary timestamp during handover execution
            self._clock.set_time(boundary_dt)
            if mode == "autopilot":
                shift = await self._flip_service.flip_to_autopilot()
            else:
                shift = await self._flip_service.flip_to_copilot(post_brief=True)
            shifts.append(shift)

        if crossed:
            self._clock.set_time(saved_now)

        if self._cr_service is not None:
            await self._cr_service.check_estimator_timeouts()

        return shifts
