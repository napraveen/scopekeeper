"""Periodic timeout worker for 10-minute Estimator reminders and 30-minute heuristic fallbacks."""

from __future__ import annotations

import asyncio
import contextlib

from clerk.services.change_requests import ChangeRequestService


class EstimatorTimeoutWorker:
    """Background worker checking Estimator 10m reminders and 30m heuristic fallbacks."""

    def __init__(
        self,
        *,
        cr_service: ChangeRequestService,
        check_interval_seconds: float = 30.0,
    ) -> None:
        self._cr_service = cr_service
        self._check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def run_once(self) -> list[str]:
        """Check all open ChangeRequests once and return triggered timeout action tags."""
        return await self._cr_service.check_estimator_timeouts()

    async def start(self) -> None:
        """Start the periodic timeout loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop the periodic timeout loop."""
        self._running = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._check_interval_seconds)
            if not self._running:
                break
            with contextlib.suppress(Exception):
                await self.run_once()
