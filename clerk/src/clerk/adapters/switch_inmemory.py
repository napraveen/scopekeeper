"""In-memory SwitchPort implementation mirroring Switch 0.31 rooms, roles, placements, and rules."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

from clerk.domain.models import (
    ChatApp,
    Member,
    Room,
    RoomLink,
    RoomMap,
    RoomRoleHolder,
    RoomsConfig,
)
from clerk.domain.parsing import (
    ClerkModeMessage,
    ClerkQuestionMessage,
    ClerkReadyMessage,
    ParseError,
    parse_clerk_to_scout_message,
)
from clerk.domain.templates import render_handover_greeting
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

_FORBIDDEN_ACK_ONLY: frozenset[str] = frozenset(
    {"ok", "okay", "thanks", "thank you", "on it", "got it", "acknowledged", "ack"}
)


@dataclass
class InMemoryRoomState:
    """Internal state for one simulated Switch room."""

    ref: RoomRef
    kind: Literal["client", "intake", "delivery", "change"]
    instructions: str = ""
    archived: bool = False
    members: set[str] = field(default_factory=set)
    roles: dict[str, str | None] = field(default_factory=dict)
    references: dict[str, Reference] = field(default_factory=dict)
    documents: dict[str, RoomDocumentSpec] = field(default_factory=dict)
    messages: list[MessageRef] = field(default_factory=list)
    runtime_state: tuple[Literal["working", "awaiting-input", "idle"], str | None] = (
        "idle",
        None,
    )


class InMemorySwitch:
    """Full in-memory SwitchPort implementation for tests and offline demos."""

    def __init__(
        self,
        rooms_config: RoomsConfig,
        clock: ClockPort,
        *,
        auto_scout_relay: bool = True,
        allow_room_creation: bool = True,
    ) -> None:
        self._rooms_config = rooms_config
        self._clock = clock
        self._auto_scout_relay = auto_scout_relay
        self._allow_room_creation = allow_room_creation
        self._connected = False
        self._msg_seq = 0
        self._evt_seq = 0
        self._rooms_by_id: dict[str, InMemoryRoomState] = {}
        self._rooms_by_name: dict[str, InMemoryRoomState] = {}
        self._placements: dict[str, str] = {}
        self._links: list[RoomLink] = []
        self._queue: asyncio.Queue[SwitchEvent] = asyncio.Queue()

        self._init_default_rooms()

    def _init_default_rooms(self) -> None:
        client_id = self._rooms_config.rooms.client.id
        if client_id.startswith("<"):
            client_id = "room-acme-client"
        intake_id = self._rooms_config.rooms.intake.id
        if intake_id.startswith("<"):
            intake_id = "room-acme-intake"
        delivery_id = self._rooms_config.rooms.delivery.id
        if delivery_id.startswith("<"):
            delivery_id = "room-acme-delivery"

        client_state = InMemoryRoomState(
            ref=RoomRef(id=client_id, name="acme-client", app=ChatApp.DISCORD),
            kind="client",
            members={"sam", "priya", "acme-scout"},
            roles={"client-desk": None},
        )
        intake_state = InMemoryRoomState(
            ref=RoomRef(id=intake_id, name="acme-intake", app=ChatApp.SLACK),
            kind="intake",
            members={"priya", "acme-scout", "clerk"},
            roles={},
        )
        delivery_state = InMemoryRoomState(
            ref=RoomRef(id=delivery_id, name="acme-delivery", app=ChatApp.SLACK),
            kind="delivery",
            members={
                "priya",
                "ravi",
                "aisha",
                "clerk",
                "acme-estimator",
                "acme-builder",
            },
            roles={"account-manager": "priya", "delivery-lead": "ravi"},
        )

        for st in (client_state, intake_state, delivery_state):
            self._rooms_by_id[st.ref.id] = st
            self._rooms_by_name[st.ref.name] = st

        self._links.extend(
            [
                RoomLink(
                    **{
                        "from": "acme-client",
                        "to": "acme-intake",
                        "description": "asks in, client-ready answers out",
                    }
                ),
                RoomLink(
                    **{
                        "from": "acme-intake",
                        "to": "acme-client",
                        "description": "asks in, client-ready answers out",
                    }
                ),
                RoomLink(
                    **{
                        "from": "acme-intake",
                        "to": "acme-delivery",
                        "description": "approved work becomes tickets",
                    }
                ),
                RoomLink(
                    **{
                        "from": "acme-delivery",
                        "to": "acme-intake",
                        "description": "approved work becomes tickets",
                    }
                ),
            ]
        )

    # ── Room Lookup & Guard Helpers ───────────────────────────────────────────

    def get_room_ref(self, name_or_id: str) -> RoomRef:
        """Resolve a RoomRef by room name or Switch room ID."""
        if name_or_id in self._rooms_by_id:
            return self._rooms_by_id[name_or_id].ref
        if name_or_id in self._rooms_by_name:
            return self._rooms_by_name[name_or_id].ref
        raise KeyError(f"Unknown room {name_or_id!r}")

    def _resolve_state(self, room: RoomRef | str) -> InMemoryRoomState:
        key = room if isinstance(room, str) else room.id
        if key in self._rooms_by_id:
            return self._rooms_by_id[key]
        name_key = room if isinstance(room, str) else room.name
        if name_key in self._rooms_by_name:
            return self._rooms_by_name[name_key]
        # Auto-register pre-created pool rooms like acme-cr-004 if referenced
        if isinstance(room, RoomRef):
            st = InMemoryRoomState(
                ref=room,
                kind="change",
                members={"priya", "ravi", "clerk", "acme-estimator", "acme-builder"},
                roles={"account-manager": "priya", "delivery-lead": "ravi"},
            )
            self._rooms_by_id[room.id] = st
            self._rooms_by_name[room.name] = st
            return st
        raise KeyError(f"Unknown Switch room {room!r}")

    def _guard_clerk_not_in_client_room(self, room: RoomRef | str, actor: str = "clerk") -> None:
        st = self._resolve_state(room)
        if actor == "clerk" and (st.ref.name == "acme-client" or st.kind == "client"):
            raise PermissionError(
                "Clerk is forbidden from posting or binding a session placement in acme-client."
            )

    def _guard_not_ack_only(self, text: str) -> None:
        cleaned = text.strip().rstrip(".!").lower()
        if cleaned in _FORBIDDEN_ACK_ONLY:
            raise ValueError(
                f"Acknowledgement-only message {text!r} is forbidden by room protocol."
            )

    def _bind_placement(self, room: RoomRef) -> None:
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        self._placements[f"sess-{room.id}"] = room.id

    # ── SwitchPort Implementation ─────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect Clerk to acme-intake and acme-delivery (never acme-client)."""
        self._connected = True
        self._bind_placement(self.get_room_ref("acme-intake"))
        self._bind_placement(self.get_room_ref("acme-delivery"))

    def events(self) -> AsyncIterator[SwitchEvent]:
        """Yield inbound SwitchEvents from the queue."""

        async def _gen() -> AsyncIterator[SwitchEvent]:
            while True:
                ev = await self._queue.get()
                yield ev

        return _gen()

    def _append_message(
        self,
        st: InMemoryRoomState,
        *,
        sender: str,
        text: str,
        thread: str | None = None,
        enqueue_event: bool = False,
        is_agent: bool = True,
    ) -> MessageRef:
        self._msg_seq += 1
        msg_id = f"msg-{self._msg_seq:04d}"
        ts = self._clock.now().isoformat()
        domain = (
            "https://discord.com/channels/acme"
            if st.ref.app == ChatApp.DISCORD
            else "https://slack.com/archives"
        )
        url = f"{domain}/{st.ref.name}/{msg_id}"
        msg = MessageRef(
            id=msg_id,
            room_id=st.ref.id,
            room_name=st.ref.name,
            url=url,
            sender=sender,
            text=text,
            ts=ts,
            thread_id=thread,
        )
        st.messages.append(msg)

        if enqueue_event:
            self._evt_seq += 1
            ev = SwitchEvent(
                id=f"sw-evt-{self._evt_seq:04d}",
                type="message",
                room_id=st.ref.id,
                room_name=st.ref.name,
                sender_name=sender,
                sender_id=sender,
                text=text,
                ts=ts,
                message_link=url,
                thread_id=thread,
                is_agent=is_agent,
            )
            self._queue.put_nowait(ev)

        return msg

    async def post(self, room: RoomRef, text: str, thread: str | None = None) -> MessageRef:
        """Post a message as Clerk into `room` (forbids acme-client and ack-only text)."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        self._guard_not_ack_only(text)
        self._bind_placement(room)
        st = self._resolve_state(room)
        msg = self._append_message(st, sender="clerk", text=text, thread=thread)
        if st.ref.name == "acme-intake" and self._auto_scout_relay:
            await self._maybe_handle_clerk_to_scout(text)
        return msg

    async def send_targeted(
        self,
        room: RoomRef,
        targets: list[str],
        text: str,
        target_roles: list[str] | None = None,
        thread: str | None = None,
    ) -> MessageRef:
        """Send a targeted message as Clerk in `room`."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        self._guard_not_ack_only(text)
        self._bind_placement(room)
        st = self._resolve_state(room)
        msg = self._append_message(st, sender="clerk", text=text, thread=thread)
        norm_targets = {t.lstrip("@").lower() for t in targets}
        if (
            st.ref.name == "acme-intake"
            and self._auto_scout_relay
            and ("acme-scout" in norm_targets or "scout" in norm_targets)
        ):
            await self._maybe_handle_clerk_to_scout(text)
        return msg

    async def _maybe_handle_clerk_to_scout(self, text: str) -> None:
        """Simulate Console Scout reacting to MODE, READY, and QUESTION in acme-intake."""
        try:
            parsed = parse_clerk_to_scout_message(text)
        except ParseError:
            return

        client_state = self._resolve_state("acme-client")
        if isinstance(parsed, ClerkModeMessage):
            if parsed.mode == "autopilot":
                client_state.roles["client-desk"] = "acme-scout"
                greeting = render_handover_greeting("Sam", "11 PM", "Priya")
                self._append_message(client_state, sender="acme-scout", text=greeting)
            else:
                client_state.roles["client-desk"] = None
        elif isinstance(parsed, ClerkReadyMessage):
            # Scout only posts automatically in autopilot mode or when READY is sent
            self._append_message(client_state, sender="acme-scout", text=parsed.text)
        elif isinstance(parsed, ClerkQuestionMessage):
            choices_line = " ".join(f"{idx}) {c}" for idx, c in enumerate(parsed.choices, 1))
            q_client_text = f"{parsed.text}\nChoices: {choices_line}"
            self._append_message(client_state, sender="acme-scout", text=q_client_text)

    async def read_context(self, room: RoomRef, since: str | None = None) -> list[SwitchMessage]:
        """Return messages in `room`."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        st = self._resolve_state(room)
        return [
            SwitchMessage(
                id=m.id,
                room_id=m.room_id,
                sender=m.sender,
                text=m.text,
                ts=m.ts,
                thread_id=m.thread_id,
                url=m.url,
            )
            for m in st.messages
            if since is None or m.ts >= since
        ]

    async def create_room(self, spec: RoomSpec) -> RoomRef:
        """Create a new Switch change room or raise RuntimeError if disabled."""
        if not self._allow_room_creation:
            raise RuntimeError("Dynamic room creation is disabled on this Switch server")

        room_id = f"room-{spec.name}"
        ref = RoomRef(id=room_id, name=spec.name, app=ChatApp.SLACK)
        members = {"clerk", *(a.lstrip("@") for a in spec.agent_names), *spec.user_names}
        roles: dict[str, str | None] = {
            "account-manager": "priya",
            "delivery-lead": "ravi",
        }
        for r in spec.roles:
            roles.setdefault(r.name, None)
        refs = {r.id: r for r in spec.references}
        docs = {d.name: d for d in spec.docs}
        st = InMemoryRoomState(
            ref=ref,
            kind="change",
            instructions=spec.instructions,
            members=members,
            roles=roles,
            references=refs,
            documents=docs,
        )
        self._rooms_by_id[ref.id] = st
        self._rooms_by_name[ref.name] = st
        self._bind_placement(ref)
        return ref

    async def archive_room(self, room: RoomRef) -> None:
        """Mark `room` as archived."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        st = self._resolve_state(room)
        st.archived = True

    async def invite(self, room: RoomRef, member: str, is_human: bool = False) -> None:
        """Add `member` to `room`."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        st = self._resolve_state(room)
        st.members.add(member.lstrip("@"))

    async def link(self, a: RoomRef, b: RoomRef, description: str) -> None:
        """Add a directional room link from `a` to `b`."""
        link_obj = RoomLink(**{"from": a.name, "to": b.name, "description": description})
        if not any(existing.from_ == a.name and existing.to == b.name for existing in self._links):
            self._links.append(link_obj)

    async def attach_reference(self, room: RoomRef, ref: Reference) -> None:
        """Attach `ref` to `room`."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        st = self._resolve_state(room)
        st.references[ref.id] = ref

    async def upsert_document(self, room: RoomRef, doc: RoomDocumentSpec) -> None:
        """Create or update a room document in `room`."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        self._bind_placement(room)
        st = self._resolve_state(room)
        st.documents[doc.name] = doc

    async def role_holder(self, room: RoomRef, role: str) -> str | None:
        """Return the current holder of `role` in `room` (allowed to query acme-client)."""
        st = self._resolve_state(room)
        return st.roles.get(role)

    async def assume_role(self, room: RoomRef, role: str) -> None:
        """Assume `role` in `room` as Clerk (forbidden in acme-client)."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        st = self._resolve_state(room)
        st.roles[role] = "clerk"

    async def release_role(self, room: RoomRef, role: str) -> None:
        """Release `role` in `room` as Clerk (forbidden in acme-client)."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        st = self._resolve_state(room)
        if st.roles.get(role) == "clerk":
            st.roles[role] = None

    async def set_runtime_state(
        self,
        room: RoomRef,
        state: Literal["working", "awaiting-input", "idle"],
        detail: str | None = None,
    ) -> None:
        """Set Clerk's live runtime state in `room`."""
        self._guard_clerk_not_in_client_room(room, actor="clerk")
        st = self._resolve_state(room)
        st.runtime_state = (state, detail)

    # ── Test & Simulation Helpers ─────────────────────────────────────────────

    def post_as(
        self,
        sender: str,
        room_name_or_id: str,
        text: str,
        *,
        is_agent: bool = False,
        enqueue_event: bool = True,
    ) -> MessageRef:
        """Simulate a human or non-Clerk agent posting a message in `room_name_or_id`."""
        st = self._resolve_state(room_name_or_id)
        return self._append_message(
            st,
            sender=sender,
            text=text,
            enqueue_event=enqueue_event,
            is_agent=is_agent,
        )

    def assume_role_as(self, agent_name: str, room_name_or_id: str, role: str) -> None:
        """Simulate `agent_name` assuming `role` in `room_name_or_id`."""
        st = self._resolve_state(room_name_or_id)
        st.roles[role] = agent_name

    def release_role_as(self, agent_name: str, room_name_or_id: str, role: str) -> None:
        """Simulate `agent_name` releasing `role` in `room_name_or_id`."""
        st = self._resolve_state(room_name_or_id)
        if st.roles.get(role) == agent_name:
            st.roles[role] = None

    def messages_in(self, room_name_or_id: str) -> list[MessageRef]:
        """Return all messages posted in `room_name_or_id`."""
        st = self._resolve_state(room_name_or_id)
        return list(st.messages)

    def documents_in(self, room_name_or_id: str) -> dict[str, RoomDocumentSpec]:
        """Return all room documents in `room_name_or_id`."""
        st = self._resolve_state(room_name_or_id)
        return dict(st.documents)

    def is_archived(self, room_name_or_id: str) -> bool:
        """Return True if `room_name_or_id` has been archived."""
        return self._resolve_state(room_name_or_id).archived

    def drain_events_nowait(self) -> list[SwitchEvent]:
        """Drain and return all queued SwitchEvents without blocking."""
        items: list[SwitchEvent] = []
        while not self._queue.empty():
            items.append(self._queue.get_nowait())
        return items

    def build_room_map(self) -> RoomMap:
        """Build the Frontend Data Contract RoomMap from live room state."""
        member_catalog: dict[str, Member] = {
            "sam": Member(id="sam", name="Sam", kind="person", side="client"),
            "priya": Member(id="priya", name="Priya", kind="person", side="agency"),
            "ravi": Member(id="ravi", name="Ravi", kind="person", side="agency"),
            "aisha": Member(id="aisha", name="Aisha", kind="person", side="agency"),
            "acme-scout": Member(
                id="acme-scout",
                name="Scout",
                kind="agent",
                side="agency",
                vendor="OpenCode",
            ),
            "clerk": Member(
                id="clerk",
                name="Clerk",
                kind="agent",
                side="agency",
                vendor="Custom",
            ),
            "acme-estimator": Member(
                id="acme-estimator",
                name="Estimator",
                kind="agent",
                side="agency",
                vendor="Claude Code",
            ),
            "acme-builder": Member(
                id="acme-builder",
                name="Builder",
                kind="agent",
                side="agency",
                vendor="Codex",
            ),
        }
        rooms_out: list[Room] = []
        for st in self._rooms_by_name.values():
            members = [
                member_catalog.get(
                    m,
                    Member(id=m, name=m, kind="person", side="agency"),
                )
                for m in sorted(st.members)
            ]
            roles = [
                RoomRoleHolder(name=r_name, holder=r_holder)
                for r_name, r_holder in st.roles.items()
            ]
            rooms_out.append(
                Room(
                    id=st.ref.id,
                    name=st.ref.name,
                    app=st.ref.app,
                    kind=st.kind,
                    members=members,
                    roles=roles,
                    references=sorted(st.references.keys()),
                )
            )
        return RoomMap(rooms=rooms_out, links=list(self._links))
