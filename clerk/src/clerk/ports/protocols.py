"""Port protocols and value objects for Switch, LLM, GitHost, Preview, and Clock."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from clerk.domain.models import ChatApp

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass(frozen=True)
class RoomRef:
    """Reference to a Switch room."""

    id: str
    name: str
    app: ChatApp = ChatApp.SLACK


@dataclass(frozen=True)
class MessageRef:
    """Reference to a message posted in a Switch room."""

    id: str
    room_id: str
    room_name: str
    url: str
    sender: str
    text: str
    ts: str
    thread_id: str | None = None


@dataclass(frozen=True)
class SwitchMessage:
    """Message returned by Switch read_context."""

    id: str
    room_id: str
    sender: str
    text: str
    ts: str
    thread_id: str | None = None
    url: str = ""


@dataclass(frozen=True)
class SwitchEvent:
    """Inbound event from the Switch Agent Protocol stream."""

    id: str
    type: Literal["message", "command", "system"]
    room_id: str
    room_name: str
    sender_name: str
    sender_id: str
    text: str
    ts: str
    message_link: str = ""
    thread_id: str | None = None
    is_agent: bool = False


@dataclass(frozen=True)
class RoomRoleSpec:
    """Specification for defining a Switch room role."""

    name: str
    instructions: str
    exclusive: bool = False


@dataclass(frozen=True)
class RoomDocumentSpec:
    """Specification for creating or updating a Switch room document."""

    name: str
    description: str
    instructions: str
    content: str


@dataclass(frozen=True)
class Reference:
    """External reference attached to a Switch room."""

    id: str
    title: str
    url: str
    description: str = ""


@dataclass(frozen=True)
class RoomSpec:
    """Specification for creating a new Switch room (e.g. acme-cr-NNN)."""

    name: str
    description: str
    group_name: str = "Acme Web Portal"
    instructions: str = ""
    agent_names: list[str] = field(default_factory=list)
    user_names: list[str] = field(default_factory=list)
    roles: list[RoomRoleSpec] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    docs: list[RoomDocumentSpec] = field(default_factory=list)


@dataclass(frozen=True)
class TicketRef:
    """Reference to a created development issue or local ticket."""

    id: str
    ask_id: str
    title: str
    url: str


@dataclass(frozen=True)
class PullRequestRef:
    """Reference to a pull request on a work-item branch."""

    work_id: str
    branch: str
    title: str
    url: str


@runtime_checkable
class SwitchPort(Protocol):
    """Port interface for Switch Agent Protocol operations and event streaming."""

    async def connect(self) -> None:
        """Connect to the Switch stream and initialize room placements."""
        ...

    def events(self) -> AsyncIterator[SwitchEvent]:
        """Yield inbound Switch events."""
        ...

    async def post(self, room: RoomRef, text: str, thread: str | None = None) -> MessageRef:
        """Post a message to a Switch room (must raise PermissionError for acme-client)."""
        ...

    async def send_targeted(
        self,
        room: RoomRef,
        targets: list[str],
        text: str,
        target_roles: list[str] | None = None,
        thread: str | None = None,
    ) -> MessageRef:
        """Send a targeted message to specific agent names or room roles."""
        ...

    async def read_context(self, room: RoomRef, since: str | None = None) -> list[SwitchMessage]:
        """Read recent messages in a room."""
        ...

    async def create_room(self, spec: RoomSpec) -> RoomRef:
        """Create a new Switch room in the room group."""
        ...

    async def archive_room(self, room: RoomRef) -> None:
        """Archive a completed change room."""
        ...

    async def invite(self, room: RoomRef, member: str, is_human: bool = False) -> None:
        """Invite an agent or human user to a room."""
        ...

    async def link(self, a: RoomRef, b: RoomRef, description: str) -> None:
        """Link room `a` to room `b` with a directional label."""
        ...

    async def attach_reference(self, room: RoomRef, ref: Reference) -> None:
        """Attach an external reference to a room."""
        ...

    async def upsert_document(self, room: RoomRef, doc: RoomDocumentSpec) -> None:
        """Create or update a room-scoped document."""
        ...

    async def role_holder(self, room: RoomRef, role: str) -> str | None:
        """Return the current agent name holding `role` in `room`, or None if unheld."""
        ...

    async def assume_role(self, room: RoomRef, role: str) -> None:
        """Assume `role` in `room`."""
        ...

    async def release_role(self, room: RoomRef, role: str) -> None:
        """Release `role` in `room`."""
        ...

    async def set_runtime_state(
        self,
        room: RoomRef,
        state: Literal["working", "awaiting-input", "idle"],
        detail: str | None = None,
    ) -> None:
        """Report live runtime status for native chat indicators."""
        ...


@runtime_checkable
class LLMPort(Protocol):
    """Port interface for structured JSON classification and constrained text generation."""

    async def json(self, system: str, user: str, schema: type[TModel]) -> TModel:
        """Generate a validated Pydantic model instance at temperature 0."""
        ...

    async def text(self, system: str, user: str, max_words: int = 120) -> str:
        """Generate concise plain-text wording at temperature 0."""
        ...


@runtime_checkable
class GitHostPort(Protocol):
    """Port interface for tickets, branches, and pull-request discovery."""

    async def create_ticket(self, ask_id: str, title: str, body: str) -> TicketRef:
        """Create a GitHub issue or local `tickets/ASK-NNNN.md` ticket."""
        ...

    async def ensure_branch(self, branch: str) -> str:
        """Ensure the target work-item branch exists or is registered."""
        ...

    async def find_pull_request(self, branch: str) -> PullRequestRef | None:
        """Poll for an open pull request matching `branch`."""
        ...


@runtime_checkable
class PreviewPort(Protocol):
    """Port interface for deploying and retrieving branch preview URLs."""

    async def deploy_preview(self, work_id: str, branch: str) -> str:
        """Deploy or register a preview environment for `branch` and return its URL."""
        ...


@runtime_checkable
class ClockPort(Protocol):
    """Port interface for reading or advancing the current timezone-aware time."""

    def now(self) -> datetime:
        """Return the current timezone-aware datetime."""
        ...

    def set_time(self, dt: datetime) -> None:
        """Set the clock to an exact timezone-aware datetime."""
        ...

    def advance(self, delta: timedelta) -> datetime:
        """Advance the clock by `delta` and return the new datetime."""
        ...
