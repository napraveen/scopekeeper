"""Switch event consumer worker connecting SwitchPort to WorkflowOrchestrator."""

from __future__ import annotations

import asyncio
import contextlib

import structlog

from clerk.domain.models import ChatApp
from clerk.ports.protocols import RoomRef, SwitchEvent, SwitchPort
from clerk.services.workflow import WorkflowOrchestrator

logger = structlog.get_logger(__name__)


class SwitchConsumerWorker:
    """Async background worker consuming Switch events and reporting live runtime-state."""

    def __init__(
        self,
        *,
        switch: SwitchPort,
        orchestrator: WorkflowOrchestrator,
        poll_interval_seconds: float = 10.0,
    ) -> None:
        self._switch = switch
        self._orchestrator = orchestrator
        self._poll_interval_seconds = poll_interval_seconds
        self._running = False
        self._consumer_task: asyncio.Task[None] | None = None
        self._poller_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Connect to Switch and start the event consumer and poller tasks."""
        if self._running:
            return
        self._running = True
        await self._switch.connect()
        self._consumer_task = asyncio.create_task(self._consume_loop())
        if self._poll_interval_seconds > 0:
            self._poller_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop all worker tasks cleanly."""
        self._running = False
        for task in (self._consumer_task, self._poller_task):
            if task is not None and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        close_fn = getattr(self._switch, "close", None)
        if callable(close_fn):
            await close_fn()

    async def process_one(self, event: SwitchEvent) -> None:
        """Process a single SwitchEvent while reporting `working` / `idle` runtime state."""
        room_ref = RoomRef(id=event.room_id, name=event.room_name, app=ChatApp.SLACK)
        is_client = event.room_name == "acme-client" or event.room_id == "acme-client"

        if not is_client:
            with contextlib.suppress(Exception):
                await self._switch.set_runtime_state(
                    room_ref,
                    "working",
                    detail=f"Processing event {event.id}",
                )
        try:
            await self._orchestrator.handle_switch_event(event)
        except Exception as exc:
            logger.error(
                "worker.event_failed",
                switch_event_id=event.id,
                room=event.room_name,
                error=str(exc),
            )
        finally:
            if not is_client:
                with contextlib.suppress(Exception):
                    await self._switch.set_runtime_state(room_ref, "idle", detail=None)

    async def _consume_loop(self) -> None:
        async for event in self._switch.events():
            if not self._running:
                break
            await self.process_one(event)

    async def _poll_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._poll_interval_seconds)
            if not self._running:
                break
            with contextlib.suppress(Exception):
                await self._orchestrator.poll_open_work_items()
            renew_fn = getattr(self._switch, "renew_leases", None)
            if callable(renew_fn):
                with contextlib.suppress(Exception):
                    await renew_fn()
