"""Server-Sent Events (SSE) broadcaster for `/api/stream`."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from clerk.domain.models import StreamEvent


class EventBroadcaster:
    """Fan-out broadcaster pushing live `StreamEvent` items to connected SSE clients."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[StreamEvent | None]] = set()

    def publish(self, event: StreamEvent) -> None:
        """Broadcast `event` to all active SSE subscriber queues."""
        for queue in list(self._subscribers):
            queue.put_nowait(event)

    def close_all(self) -> None:
        """Signal all active SSE streams to close cleanly (used on shutdown or tests)."""
        for queue in list(self._subscribers):
            queue.put_nowait(None)

    async def subscribe(
        self,
        *,
        initial_events: list[StreamEvent] | None = None,
        max_events: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield SSE-formatted `StreamEvent` payloads (`by_alias=True` camelCase)."""
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        self._subscribers.add(queue)
        emitted = 0
        try:
            for init_ev in initial_events or []:
                payload = init_ev.model_dump_json(by_alias=True)
                yield f"id: {init_ev.id}\nevent: {init_ev.type}\ndata: {payload}\n\n"
                emitted += 1
                if max_events is not None and emitted >= max_events:
                    return

            while True:
                item = await queue.get()
                if item is None:
                    break
                payload = item.model_dump_json(by_alias=True)
                yield f"id: {item.id}\nevent: {item.type}\ndata: {payload}\n\n"
                emitted += 1
                if max_events is not None and emitted >= max_events:
                    break
        finally:
            self._subscribers.discard(queue)
