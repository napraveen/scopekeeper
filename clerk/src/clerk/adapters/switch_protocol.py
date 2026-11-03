"""Real Switch Agent Protocol 0.31 adapter (WebSocket stream, ping/pong, placements, HTTP ops)."""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

import httpx
import structlog

from clerk.domain.models import ChatApp, RoomsConfig
from clerk.ports.protocols import (
    ClockPort,
    MessageRef,
    Reference,
    RoomDocumentSpec,
    RoomRef,
    RoomSpec,
    SwitchEvent,
    SwitchMessage,
)

logger = structlog.get_logger(__name__)

_FORBIDDEN_ACK_ONLY: frozenset[str] = frozenset(
    {"ok", "okay", "thanks", "thank you", "on it", "got it", "acknowledged", "ack"}
)


class SwitchBudgetExceededError(RuntimeError):
    """Raised when Switch returns HTTP 429 BudgetExceeded."""


class WebSocketStreamProtocol(Protocol):
    """Minimal protocol for a WebSocket client connection (real or fake in contract tests)."""

    def __aiter__(self) -> AsyncIterator[str | bytes]: ...

    async def send(self, data: str) -> None: ...

    async def close(self) -> None: ...


WebSocketFactory = Callable[[str, dict[str, str]], Any]


def _default_ws_factory(url: str, headers: dict[str, str]) -> Any:
    """Connect using the standard `websockets` library."""
    import websockets

    return websockets.connect(url, additional_headers=headers)


class SwitchProtocolAdapter:
    """Production SwitchPort adapter over Switch 0.31 WebSocket stream and HTTP operations."""

    def __init__(
        self,
        *,
        base_url: str,
        ws_url: str | None = None,
        agent_id: str,
        api_key: str,
        rooms_config: RoomsConfig,
        clock: ClockPort,
        connection_id: str | None = None,
        forbid_client_room: bool = True,
        min_post_interval_seconds: float = 0.0,
        reconnect_base_delay: float = 0.2,
        reconnect_max_delay: float = 5.0,
        max_reconnect_attempts: int | None = None,
        http_client: httpx.AsyncClient | None = None,
        ws_factory: WebSocketFactory | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        if ws_url:
            self._ws_url = ws_url.rstrip("/")
        elif self._base_url.startswith("https://"):
            self._ws_url = "wss://" + self._base_url.removeprefix("https://")
        else:
            self._ws_url = "ws://" + self._base_url.removeprefix("http://")

        self._agent_id = agent_id
        self._api_key = api_key
        self._rooms_config = rooms_config
        self._clock = clock
        self._connection_id = connection_id or str(uuid.uuid4())
        self._forbid_client_room = forbid_client_room
        self._min_post_interval_seconds = min_post_interval_seconds
        self._reconnect_base_delay = reconnect_base_delay
        self._reconnect_max_delay = reconnect_max_delay
        self._max_reconnect_attempts = max_reconnect_attempts

        self._owns_http_client = http_client is None
        self._http = http_client or httpx.AsyncClient(base_url=self._base_url, timeout=15.0)
        self._ws_factory: WebSocketFactory = ws_factory or _default_ws_factory

        # Connection state
        self._generation: int | None = None
        self._cursor: int | None = None
        self._heartbeat_interval: float = 2.0
        self._connected_rooms: set[str] = set()
        self._placements: dict[str, str] = {}
        self._placement_list_shape: bool = False
        self._document_ids: dict[tuple[str, str], str] = {}
        self._held_roles: set[tuple[str, str]] = set()
        self._last_post_mono: dict[str, float] = {}
        self._pongs_sent: int = 0
        self._reconnect_count: int = 0
        self._stopped: bool = False
        self._last_eviction: dict[str, Any] | None = None
        self._last_refused: dict[str, Any] | None = None

        # Room registry (name <-> id)
        self._room_refs_by_name: dict[str, RoomRef] = {}
        self._room_id_to_name: dict[str, str] = {}
        self._precreated_pool_index: int = 1
        self._init_room_registry()

        # Async coordination
        self._connected_event = asyncio.Event()
        self._event_queue: asyncio.Queue[SwitchEvent] = asyncio.Queue()
        self._ws_task: asyncio.Task[None] | None = None
        self._bg_tasks: set[asyncio.Task[Any]] = set()

    def _init_room_registry(self) -> None:
        client_id = self._rooms_config.rooms.client.id
        if client_id.startswith("<"):
            client_id = "room-acme-client"
        intake_id = self._rooms_config.rooms.intake.id
        if intake_id.startswith("<"):
            intake_id = "room-acme-intake"
        delivery_id = self._rooms_config.rooms.delivery.id
        if delivery_id.startswith("<"):
            delivery_id = "room-acme-delivery"

        for ref in (
            RoomRef(id=client_id, name="acme-client", app=ChatApp.DISCORD),
            RoomRef(id=intake_id, name="acme-intake", app=ChatApp.SLACK),
            RoomRef(id=delivery_id, name="acme-delivery", app=ChatApp.SLACK),
        ):
            self._room_refs_by_name[ref.name] = ref
            self._room_id_to_name[ref.id] = ref.name

    @property
    def connection_id(self) -> str:
        """Return the client-generated Switch connection UUID."""
        return self._connection_id

    @property
    def generation(self) -> int | None:
        """Return the latest generation number from `connection_state`."""
        return self._generation

    @property
    def cursor(self) -> int | None:
        """Return the latest seen sequence cursor."""
        return self._cursor

    @property
    def pongs_sent(self) -> int:
        """Return total number of WebSocket `pong` frames sent."""
        return self._pongs_sent

    @property
    def reconnect_count(self) -> int:
        """Return total number of WebSocket reconnect attempts."""
        return self._reconnect_count

    @property
    def stopped(self) -> bool:
        """Return True if the adapter has stopped (e.g. due to `taken_over` eviction)."""
        return self._stopped

    @property
    def last_eviction(self) -> dict[str, Any] | None:
        """Return the payload of the last `evicted` control frame, if any."""
        return self._last_eviction

    def get_room_ref(self, name_or_id: str) -> RoomRef:
        """Look up a known RoomRef by room name or Switch room UUID."""
        if name_or_id in self._room_refs_by_name:
            return self._room_refs_by_name[name_or_id]
        if name_or_id in self._room_id_to_name:
            r_name = self._room_id_to_name[name_or_id]
            return self._room_refs_by_name[r_name]
        ref = RoomRef(id=name_or_id, name=name_or_id, app=ChatApp.SLACK)
        self._room_refs_by_name[name_or_id] = ref
        self._room_id_to_name[name_or_id] = name_or_id
        return ref

    def _is_client_room(self, room: RoomRef | str) -> bool:
        if isinstance(room, RoomRef):
            r_id, r_name = room.id, room.name
        else:
            r_id = room
            r_name = self._room_id_to_name.get(room, room)
        client_ref = self._room_refs_by_name.get("acme-client")
        client_id = client_ref.id if client_ref else "room-acme-client"
        return r_name == "acme-client" or r_id in {"acme-client", client_id}

    def _check_room_allowed(self, room: RoomRef | str) -> None:
        """Raise PermissionError if Clerk attempts to touch `acme-client`."""
        if self._forbid_client_room and self._is_client_room(room):
            raise PermissionError(
                "Clerk is forbidden by architectural guardrail from accessing acme-client."
            )

    def _check_not_ack_only(self, text: str) -> None:
        cleaned = text.strip().rstrip(".!").lower()
        if cleaned in _FORBIDDEN_ACK_ONLY:
            raise ValueError(f"Refusing to post acknowledgement-only message: {text!r}")

    async def _enforce_rate_limit(self, room_id: str) -> None:
        if self._min_post_interval_seconds <= 0:
            return
        now_m = time.monotonic()
        last_m = self._last_post_mono.get(room_id)
        if last_m is not None:
            elapsed = now_m - last_m
            if elapsed < self._min_post_interval_seconds:
                await asyncio.sleep(self._min_post_interval_seconds - elapsed)
        self._last_post_mono[room_id] = time.monotonic()

    def _auth_headers(self, session_id: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Switch-Connection-Id": self._connection_id,
        }
        if session_id:
            headers["X-Switch-Session-Id"] = session_id
        return headers

    async def register_agent(
        self,
        *,
        registration_key: str,
        name: str = "clerk",
        display_name: str = "Clerk",
        description: str = "ScopeKeeper contract, pricing, ledger, and handover service",
        overwrite: bool = True,
    ) -> tuple[str, str]:
        """Register a custom agent via `POST /agents` and update credentials."""
        payload: dict[str, Any] = {
            "name": name,
            "description": description,
            "display_name": display_name,
            "icon_url": None,
            "connector_type": "custom",
            "integration_profile": {
                "connection_model": "always_on",
                "message_exchange": True,
                "pre_invocation_mediation": [],
                "post_invocation_mediation": [],
                "event_reporting": [],
                "command_capabilities": {
                    "reset": "unsupported",
                    "compact": "unsupported",
                    "interrupt": "unsupported",
                },
            },
            "tools": [],
            "models": [],
            "metadata": {},
            "overwrite": overwrite,
        }
        resp = await self._http.post(
            f"{self._base_url}/agents",
            headers={"Authorization": f"Bearer {registration_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        self._agent_id = str(data["id"])
        self._api_key = str(data["api_key"])
        return (self._agent_id, self._api_key)

    async def connect(self) -> None:
        """Start the background WebSocket stream + independent ping/pong loop and bind rooms."""
        self._stopped = False
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._run_ws_loop())

        # Bind initial room session placements for allowed rooms
        for name, ref in list(self._room_refs_by_name.items()):
            if self._forbid_client_room and name == "acme-client":
                continue
            try:
                await self._ensure_placement(ref)
            except Exception as exc:
                logger.warning("switch.initial_placement_failed", room=name, error=str(exc))

    async def close(self) -> None:
        """Stop the WebSocket background task and close the HTTP client if owned."""
        self._stopped = True
        if self._ws_task is not None and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        for task in list(self._bg_tasks):
            if not task.done():
                task.cancel()
        if self._owns_http_client:
            await self._http.aclose()

    def _build_ws_url(self) -> str:
        params = [
            f"connection_id={self._connection_id}",
            "scope=all",
            "filter=all",
        ]
        allowed_rooms = [
            ref.id
            for name, ref in self._room_refs_by_name.items()
            if not (self._forbid_client_room and name == "acme-client")
        ]
        if allowed_rooms:
            params.append(f"rooms={','.join(allowed_rooms)}")
        if self._cursor is not None:
            params.append(f"start_from={self._cursor}")
        else:
            params.append("start_from=head")
        if self._generation is not None:
            params.append(f"expected_generation={self._generation}")
        query = "&".join(params)
        return f"{self._ws_url}/agents/{self._agent_id}/connection/ws?{query}"

    async def _run_ws_loop(self) -> None:
        """Maintain the WebSocket connection, replying immediately to `ping` frames."""
        attempt = 0
        while not self._stopped:
            ws_url = self._build_ws_url()
            headers = {"Authorization": f"Bearer {self._api_key}"}
            should_reconnect = False
            try:
                async with self._ws_factory(ws_url, headers) as ws:
                    attempt = 0
                    async for raw_frame in ws:
                        text_frame = (
                            raw_frame.decode("utf-8")
                            if isinstance(raw_frame, bytes)
                            else str(raw_frame)
                        )
                        if not text_frame.strip():
                            continue
                        frame = json.loads(text_frame)
                        action = await self._handle_ws_frame(ws, frame)
                        if action == "stop":
                            self._stopped = True
                            should_reconnect = False
                            break
                        if action == "reconnect":
                            should_reconnect = True
                            break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("switch.ws_disconnected", error=str(exc), attempt=attempt)
                should_reconnect = not self._stopped

            if self._stopped or not should_reconnect:
                break

            attempt += 1
            self._reconnect_count += 1
            if (
                self._max_reconnect_attempts is not None
                and attempt > self._max_reconnect_attempts
            ):
                self._stopped = True
                break

            delay = min(
                self._reconnect_max_delay,
                self._reconnect_base_delay * (2 ** (attempt - 1)),
            )
            jitter = random.uniform(0.0, delay * 0.2)
            await asyncio.sleep(delay + jitter)

    async def _handle_ws_frame(
        self, ws: WebSocketStreamProtocol, frame: dict[str, Any]
    ) -> Literal["continue", "reconnect", "stop"]:
        """Process a single WebSocket frame immediately without blocking on consumers."""
        event_type = str(frame.get("event") or "")
        data: dict[str, Any] = frame.get("data") or {}
        seq_id = frame.get("id")
        if isinstance(seq_id, int):
            self._cursor = max(self._cursor or 0, seq_id)

        # 1. Immediate heartbeat ping/pong (must never block on LLM or git)
        if event_type == "ping":
            pong_payload = json.dumps({"type": "pong", "cursor": self._cursor or 0})
            await ws.send(pong_payload)
            self._pongs_sent += 1
            return "continue"

        # 2. Connection state snapshot
        if event_type == "connection_state":
            gen = data.get("generation")
            if isinstance(gen, int):
                self._generation = gen
            cur = data.get("cursor")
            if isinstance(cur, int):
                self._cursor = cur
            hb = data.get("heartbeat_interval_seconds")
            if isinstance(hb, (int, float)):
                self._heartbeat_interval = float(hb)
            rooms = data.get("rooms")
            if isinstance(rooms, list):
                self._connected_rooms = {str(r) for r in rooms}
            self._connected_event.set()
            return "continue"

        # 3. Sequence gap -> catch up via read_context in a background task
        if event_type == "gap":
            to_seq = data.get("to_sequence")
            if isinstance(to_seq, int):
                self._cursor = max(self._cursor or 0, to_seq)
            task = asyncio.create_task(self._recover_from_gap(data))
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
            return "continue"

        # 4. Subscription changed
        if event_type == "subscription_changed":
            rooms = data.get("rooms")
            if isinstance(rooms, list):
                self._connected_rooms = {str(r) for r in rooms}
            return "continue"

        # 5. Room released -> drop cached session placement so next op rebinds
        if event_type == "room_released":
            released_room = str(data.get("room_id") or "")
            self._placements.pop(released_room, None)
            return "continue"

        # 6. Evicted -> stop on taken_over; reconnect on heartbeat_lapsed
        if event_type == "evicted":
            self._last_eviction = data
            code = str(data.get("code") or "")
            if code == "taken_over":
                logger.error("switch.evicted_taken_over", reason=data.get("reason"))
                return "stop"
            logger.warning("switch.evicted_reconnecting", code=code, reason=data.get("reason"))
            return "reconnect"

        # 7. Refused
        if event_type == "refused":
            self._last_refused = data
            status = int(data.get("status") or 400)
            if status in {401, 403}:
                return "stop"
            if status == 409:
                self._generation = None
            return "reconnect"

        # 8. Room events (message, command, room_join)
        inner_type = str(data.get("type") or event_type)
        if inner_type in {"message", "command", "room_join"}:
            seq = data.get("sequence")
            if isinstance(seq, int):
                self._cursor = max(self._cursor or 0, seq)
            sw_event = self._translate_room_event(frame, data, inner_type)
            if sw_event is not None:
                self._event_queue.put_nowait(sw_event)
        return "continue"

    def _translate_room_event(
        self, frame: dict[str, Any], data: dict[str, Any], inner_type: str
    ) -> SwitchEvent | None:
        room_id = str(data.get("room_id") or "")
        room_name = self._room_id_to_name.get(room_id, room_id)
        if self._forbid_client_room and (room_name == "acme-client" or room_id == "acme-client"):
            return None

        payload: dict[str, Any] = data.get("payload") or {}
        evt_id = str(
            payload.get("message_id")
            or frame.get("id")
            or data.get("sequence")
            or f"evt-{uuid.uuid4().hex[:8]}"
        )
        sender_name = str(payload.get("sender_name") or payload.get("sender") or "system")
        sender_id = str(payload.get("sender") or sender_name)
        body = str(payload.get("body") or payload.get("command") or "")
        raw_ts = payload.get("timestamp")
        if isinstance(raw_ts, (int, float)):
            ts_iso = datetime.fromtimestamp(raw_ts / 1000.0, tz=UTC).isoformat()
        elif isinstance(raw_ts, str) and raw_ts:
            ts_iso = raw_ts
        else:
            ts_iso = self._clock.now().isoformat()

        ev_type: Literal["message", "command", "system"] = "message"
        if inner_type == "command":
            ev_type = "command"
        elif inner_type == "room_join":
            ev_type = "system"

        msg_link = str(
            payload.get("message_link")
            or f"https://slack.com/archives/{room_name}/p{evt_id}"
        )
        return SwitchEvent(
            id=evt_id,
            type=ev_type,
            room_id=room_id,
            room_name=room_name,
            sender_name=sender_name,
            sender_id=sender_id,
            text=body,
            ts=ts_iso,
            message_link=msg_link,
            thread_id=payload.get("thread_id"),
            is_agent=payload.get("sender_kind") == "agent",
        )

    async def _recover_from_gap(self, gap_data: dict[str, Any]) -> None:
        """Call `read_context` for rooms affected by a `gap` control frame."""
        rooms = gap_data.get("rooms") or []
        all_rooms = bool(gap_data.get("all_rooms"))
        target_refs: list[RoomRef] = []
        if all_rooms or not rooms:
            for name, ref in self._room_refs_by_name.items():
                if not (self._forbid_client_room and name == "acme-client"):
                    target_refs.append(ref)
        else:
            for r_id in rooms:
                ref = self.get_room_ref(str(r_id))
                if not (self._forbid_client_room and self._is_client_room(ref)):
                    target_refs.append(ref)

        for ref in target_refs:
            try:
                missed_msgs = await self.read_context(ref)
                for m in missed_msgs:
                    self._event_queue.put_nowait(
                        SwitchEvent(
                            id=m.id,
                            type="message",
                            room_id=ref.id,
                            room_name=ref.name,
                            sender_name=m.sender,
                            sender_id=m.sender,
                            text=m.text,
                            ts=m.ts,
                            message_link=m.url,
                            thread_id=m.thread_id,
                        )
                    )
            except Exception as exc:
                logger.warning("switch.gap_recovery_failed", room=ref.name, error=str(exc))

    async def events(self) -> AsyncIterator[SwitchEvent]:
        """Yield inbound SwitchEvents from the WebSocket stream."""
        while not self._stopped or not self._event_queue.empty():
            try:
                ev = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                yield ev
            except TimeoutError:
                if self._stopped and self._event_queue.empty():
                    break

    async def _ensure_placement(self, room: RoomRef) -> str:
        """Bind `sess-<room.id>` to `room.id` via `POST /agents/{id}/connection/placements`."""
        self._check_room_allowed(room)
        existing = self._placements.get(room.id)
        if existing is not None:
            return existing

        session_id = f"sess-{room.id}"
        url = f"{self._base_url}/agents/{self._agent_id}/connection/placements"
        headers = self._auth_headers()

        if not self._placement_list_shape:
            dict_body: dict[str, Any] = {
                "connection_id": self._connection_id,
                "placements": {session_id: room.id},
            }
            if self._generation is not None:
                dict_body["generation"] = self._generation
            resp = await self._http.post(url, headers=headers, json=dict_body)
            if resp.status_code in {400, 422}:
                self._placement_list_shape = True
            else:
                resp.raise_for_status()
                self._placements[room.id] = session_id
                return session_id

        list_body: dict[str, Any] = {
            "connection_id": self._connection_id,
            "placements": [{"session_id": session_id, "room_id": room.id}],
        }
        if self._generation is not None:
            list_body["generation"] = self._generation
        resp = await self._http.post(url, headers=headers, json=list_body)
        resp.raise_for_status()
        self._placements[room.id] = session_id
        return session_id

    async def _call_op(
        self,
        operation: str,
        arguments: dict[str, Any],
        *,
        room: RoomRef | None = None,
    ) -> Any:
        """Invoke `POST /agents/{agent_id}/ops/{operation}` with session placement headers."""
        session_id: str | None = None
        if room is not None:
            session_id = await self._ensure_placement(room)

        url = f"{self._base_url}/agents/{self._agent_id}/ops/{operation}"
        headers = self._auth_headers(session_id=session_id)
        resp = await self._http.post(url, headers=headers, json=arguments)

        if resp.status_code == 409 and room is not None:
            # Placement expired or reattached -> re-bind placement once and retry
            self._placements.pop(room.id, None)
            session_id = await self._ensure_placement(room)
            headers = self._auth_headers(session_id=session_id)
            resp = await self._http.post(url, headers=headers, json=arguments)

        if resp.status_code == 403:
            raise PermissionError(f"Switch operation {operation!r} forbidden: {resp.text}")
        if resp.status_code == 429:
            raise SwitchBudgetExceededError(
                f"Switch budget exceeded on {operation!r}: {resp.text}"
            )
        if resp.status_code == 400:
            raise ValueError(f"Switch operation {operation!r} bad arguments: {resp.text}")
        resp.raise_for_status()

        data = resp.json()
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        return data

    async def post(self, room: RoomRef, text: str, thread: str | None = None) -> MessageRef:
        """Post a message to `room` via `ops/post_message`."""
        self._check_room_allowed(room)
        self._check_not_ack_only(text)
        await self._enforce_rate_limit(room.id)

        result = await self._call_op(
            "post_message",
            {"body": text, "thread_id": thread},
            room=room,
        )
        event_id = str((result or {}).get("event_id") or f"msg-{uuid.uuid4().hex[:8]}")
        now_iso = self._clock.now().isoformat()
        return MessageRef(
            id=event_id,
            room_id=room.id,
            room_name=room.name,
            url=f"https://slack.com/archives/{room.name}/p{event_id}",
            sender=self._agent_id,
            text=text,
            ts=now_iso,
            thread_id=thread,
        )

    async def send_targeted(
        self,
        room: RoomRef,
        targets: list[str],
        text: str,
        target_roles: list[str] | None = None,
        thread: str | None = None,
    ) -> MessageRef:
        """Send a targeted message to bare agent names/roles via `ops/send_targeted_message`."""
        self._check_room_allowed(room)
        self._check_not_ack_only(text)
        await self._enforce_rate_limit(room.id)

        bare_names = [t.strip().lstrip("@") for t in targets if t.strip()]
        bare_roles = [r.strip().lstrip("@") for r in (target_roles or []) if r.strip()]

        result = await self._call_op(
            "send_targeted_message",
            {
                "body": text,
                "target_names": bare_names,
                "target_roles": bare_roles,
                "thread_id": thread,
            },
            room=room,
        )
        event_id = str((result or {}).get("event_id") or f"msg-{uuid.uuid4().hex[:8]}")
        now_iso = self._clock.now().isoformat()
        return MessageRef(
            id=event_id,
            room_id=room.id,
            room_name=room.name,
            url=f"https://slack.com/archives/{room.name}/p{event_id}",
            sender=self._agent_id,
            text=text,
            ts=now_iso,
            thread_id=thread,
        )

    async def read_context(
        self, room: RoomRef, since: str | None = None
    ) -> list[SwitchMessage]:
        """Read recent messages in `room` via `ops/read_context`."""
        self._check_room_allowed(room)
        result = await self._call_op(
            "read_context",
            {
                "limit": 50,
                "since": since,
                "before": None,
                "room_id": room.id,
            },
        )
        messages: list[SwitchMessage] = []
        if not isinstance(result, dict):
            return messages

        for thread_obj in result.get("threads", []):
            if not isinstance(thread_obj, dict):
                continue
            root = thread_obj.get("root")
            if isinstance(root, dict):
                messages.append(self._parse_context_msg(room, root))
            for reply in thread_obj.get("replies", []):
                if isinstance(reply, dict):
                    messages.append(self._parse_context_msg(room, reply))

        for flat_msg in result.get("messages", []):
            if isinstance(flat_msg, dict):
                messages.append(self._parse_context_msg(room, flat_msg))

        return messages

    def _parse_context_msg(self, room: RoomRef, raw: dict[str, Any]) -> SwitchMessage:
        msg_id = str(raw.get("message_id") or raw.get("id") or f"msg-{uuid.uuid4().hex[:6]}")
        sender = str(raw.get("sender_name") or raw.get("sender") or "unknown")
        text = str(raw.get("body") or raw.get("text") or "")
        ts_val = raw.get("timestamp") or raw.get("ts")
        if isinstance(ts_val, (int, float)):
            ts_str = datetime.fromtimestamp(ts_val / 1000.0, tz=UTC).isoformat()
        elif isinstance(ts_val, str) and ts_val:
            ts_str = ts_val
        else:
            ts_str = self._clock.now().isoformat()
        return SwitchMessage(
            id=msg_id,
            room_id=room.id,
            sender=sender,
            text=text,
            ts=ts_str,
            thread_id=raw.get("thread_id"),
            url=str(raw.get("url") or f"https://slack.com/archives/{room.name}/p{msg_id}"),
        )

    async def create_room(self, spec: RoomSpec) -> RoomRef:
        """Create a new Switch room or fall back to pre-created `acme-cr-001`..`acme-cr-010`."""
        try:
            result = await self._call_op(
                "create_room",
                {
                    "name": spec.name,
                    "description": spec.description,
                    "agent_names": [a.lstrip("@") for a in spec.agent_names],
                    "user_names": [u.lstrip("@") for u in spec.user_names],
                    "channel_type": "channel_public",
                    "bridge_id": None,
                    "internal_only": False,
                    "admin_mode": False,
                    "instructions": spec.instructions,
                    "reference_ids": [r.id for r in spec.references],
                    "linked_rooms": [],
                    "group_name": spec.group_name,
                    "roles": [
                        {
                            "name": r.name,
                            "instructions": r.instructions,
                            "exclusive": r.exclusive,
                        }
                        for r in spec.roles
                    ],
                },
            )
            room_id = str((result or {}).get("id") or f"room-{spec.name}")
            room_name = str((result or {}).get("name") or spec.name)
            ref = RoomRef(id=room_id, name=room_name, app=ChatApp.SLACK)
            self._room_refs_by_name[room_name] = ref
            self._room_id_to_name[room_id] = room_name
            for doc in spec.docs:
                await self.upsert_document(ref, doc)
            return ref
        except Exception as exc:
            logger.warning("switch.create_room_fallback", room=spec.name, error=str(exc))
            pool_name = spec.name or f"acme-cr-{self._precreated_pool_index:03d}"
            self._precreated_pool_index = min(10, self._precreated_pool_index + 1)
            ref = RoomRef(id=f"room-{pool_name}", name=pool_name, app=ChatApp.SLACK)
            self._room_refs_by_name[pool_name] = ref
            self._room_id_to_name[ref.id] = pool_name
            for human in spec.user_names:
                await self.invite(ref, human, is_human=True)
            for agent in spec.agent_names:
                await self.invite(ref, agent, is_human=False)
            for r in spec.references:
                await self.attach_reference(ref, r)
            for doc in spec.docs:
                await self.upsert_document(ref, doc)
            return ref

    async def archive_room(self, room: RoomRef) -> None:
        """Archive a completed change room via `ops/archive_room`."""
        self._check_room_allowed(room)
        await self._call_op("archive_room", {"room_id": room.id})
        self._placements.pop(room.id, None)

    async def invite(self, room: RoomRef, member: str, is_human: bool = False) -> None:
        """Invite an agent (`invite_agent_to_room`) or user (`add_users_to_room`)."""
        self._check_room_allowed(room)
        clean_member = member.strip().lstrip("@")
        if is_human:
            await self._call_op(
                "add_users_to_room",
                {"room_id": room.id, "user_names": [clean_member]},
            )
        else:
            await self._call_op(
                "invite_agent_to_room",
                {
                    "room_id": room.id,
                    "agent_name": clean_member,
                    "include_subagents": False,
                },
            )

    async def link(self, a: RoomRef, b: RoomRef, description: str) -> None:
        """Link room `a` to room `b` via `ops/link_rooms`."""
        await self._call_op(
            "link_rooms",
            {
                "source_room_id": a.id,
                "target_room_id": b.id,
                "label": description,
            },
        )

    async def attach_reference(self, room: RoomRef, ref: Reference) -> None:
        """Attach a reference to `room` via `ops/attach_reference_to_room`."""
        self._check_room_allowed(room)
        await self._call_op(
            "attach_reference_to_room",
            {"room_id": room.id, "reference_id": ref.id},
        )

    async def upsert_document(self, room: RoomRef, doc: RoomDocumentSpec) -> None:
        """Create or update a room document via `create_room_document` / `update_room_document`."""
        self._check_room_allowed(room)
        key = (room.id, doc.name)
        existing_id = self._document_ids.get(key)
        if existing_id is None:
            result = await self._call_op(
                "create_room_document",
                {
                    "name": doc.name,
                    "description": doc.description,
                    "instructions": doc.instructions,
                    "content": doc.content,
                },
                room=room,
            )
            doc_id = str((result or {}).get("document_id") or f"doc-{doc.name}")
            self._document_ids[key] = doc_id
        else:
            await self._call_op(
                "update_room_document",
                {
                    "document_id": existing_id,
                    "name": doc.name,
                    "description": doc.description,
                    "instructions": doc.instructions,
                    "content": doc.content,
                },
                room=room,
            )

    async def role_holder(self, room: RoomRef, role: str) -> str | None:
        """Query `ops/get_role_detail` (explicit `room_id`; no placement in `acme-client`)."""
        clean_role = role.strip().lstrip("@")
        result = await self._call_op(
            "get_role_detail",
            {"room_id": room.id, "role_name": clean_role},
        )
        if not isinstance(result, dict):
            return None
        held_by = result.get("held_by") or []
        if not isinstance(held_by, list) or not held_by:
            return None
        first = held_by[0]
        if isinstance(first, dict):
            name = first.get("name")
            return str(name) if name else None
        return str(first) if first else None

    async def assume_role(self, room: RoomRef, role: str) -> None:
        """Assume `role` in `room` via `ops/assume_role`."""
        self._check_room_allowed(room)
        clean_role = role.strip().lstrip("@")
        await self._call_op("assume_role", {"role": clean_role}, room=room)
        self._held_roles.add((room.id, clean_role))

    async def release_role(self, room: RoomRef, role: str) -> None:
        """Release active role in `room` via `ops/release_role`."""
        self._check_room_allowed(room)
        clean_role = role.strip().lstrip("@")
        await self._call_op("release_role", {}, room=room)
        self._held_roles.discard((room.id, clean_role))

    async def set_runtime_state(
        self,
        room: RoomRef,
        state: Literal["working", "awaiting-input", "idle"],
        detail: str | None = None,
    ) -> None:
        """Report live runtime status via `POST /agents/{agent_id}/runtime-state`."""
        self._check_room_allowed(room)
        url = f"{self._base_url}/agents/{self._agent_id}/runtime-state"
        payload = {
            "room_id": room.id,
            "state": state,
            "thread_id": None,
            "anchor_event_id": None,
            "deeplink_url": None,
            "detail": detail,
            "control_capabilities": None,
        }
        resp = await self._http.post(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()

    async def renew_leases(self) -> int:
        """Renew held role leases via `POST /agents/{agent_id}/leases/renew`."""
        url = f"{self._base_url}/agents/{self._agent_id}/leases/renew"
        resp = await self._http.post(url, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        return int(data.get("renewed", 0)) if isinstance(data, dict) else 0

    async def list_participants(self, room: RoomRef) -> list[dict[str, Any]]:
        """Fetch room participants via `GET /agents/rooms/{room_id}/participants`."""
        url = f"{self._base_url}/agents/rooms/{room.id}/participants"
        resp = await self._http.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and isinstance(data.get("participants"), list):
            return list(data["participants"])
        return []
