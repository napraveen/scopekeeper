"""Domain models, config schemas, and frontend data contract types."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class Category(StrEnum):
    """Ask classification category against the signed Statement of Work."""

    DEFECT = "DEFECT"
    IN_SCOPE = "IN_SCOPE"
    UNCLEAR = "UNCLEAR"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    DUPLICATE = "DUPLICATE"
    ALREADY_DECIDED = "ALREADY_DECIDED"


class AskStatus(StrEnum):
    """Lifecycle states of a client ask."""

    RECEIVED = "received"
    CLASSIFIED = "classified"
    QUESTION_PENDING = "question_pending"
    TICKETED = "ticketed"
    CHANGE_OPEN = "change_open"
    LINKED = "linked"
    REMINDED = "reminded"
    CHANGE_SENT = "change_sent"
    APPROVED = "approved"
    SWAPPED = "swapped"
    DECLINED = "declined"
    BUILDING = "building"
    PREVIEW = "preview"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"


class ChangeRequestStatus(StrEnum):
    """Lifecycle states of an out-of-scope change request."""

    ESTIMATING = "estimating"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_APPROVAL = "awaiting_approval"
    SENT = "sent"
    DECIDED = "decided"
    CLOSED = "closed"


class WorkItemStatus(StrEnum):
    """Lifecycle states of a Builder work item."""

    QUEUED = "queued"
    BUILDING = "building"
    PR_OPEN = "pr_open"
    PREVIEW = "preview"
    MERGED = "merged"
    ACCEPTED = "accepted"


class Confidence(StrEnum):
    """Estimate confidence tier."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OptionKey(StrEnum):
    """Change order option keys."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ChatApp(StrEnum):
    """Supported bridged chat applications."""

    DISCORD = "discord"
    SLACK = "slack"
    MATTERMOST = "mattermost"
    TEAMS = "teams"


class CamelModel(BaseModel):
    """Base model configured for camelCase JSON serialization matching the frontend contract."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ── Frontend Data Contract Models ─────────────────────────────────────────────


class ChatLink(CamelModel):
    """Pointer to a message or room in a bridged chat app."""

    app: ChatApp
    room: str
    url: str


class Ask(CamelModel):
    """A single client ask tracked by Clerk."""

    id: str
    quote: str
    requester: str
    created_at: str
    status: AskStatus
    category: Category | None = None
    clause_ids: list[str] = Field(default_factory=list)
    related_item: str | None = None
    decision_id: str | None = None
    confidence: float | None = None
    reason: str | None = None
    cr_id: str | None = None
    question_id: str | None = None
    work_item_ids: list[str] = Field(default_factory=list)
    source: ChatLink


class Question(CamelModel):
    """A clarifying question asked by Scout on Clerk's behalf."""

    id: str
    ask_id: str
    text: str
    choices: list[str]
    answer: str | None = None
    asked_at: str
    answered_at: str | None = None


class EstimateVersion(CamelModel):
    """Hour sizing and confidence for a full or smaller scope option."""

    title: str | None = None
    p50_hours: int
    p90_hours: int
    confidence: Confidence


class SimilarMerge(CamelModel):
    """Historical git merge commit referenced during estimation."""

    ref: str
    hours: int


class Estimate(CamelModel):
    """Structured code & history estimate posted by the Estimator."""

    full: EstimateVersion
    smaller: EstimateVersion | None = None
    touches: list[str] = Field(default_factory=list)
    similar: list[SimilarMerge] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    posted_at: str = ""


class OptionQuote(CamelModel):
    """One priced option (A, B, C, or D) in a change request."""

    key: OptionKey
    label: str
    description: str
    hours: int
    price_cents: int
    milestone_id: str | None = None
    shift_days: int
    new_due: str | None = None
    swap_out: list[str] | None = None
    swap_in: str | None = None
    draft: bool | None = None


class EnvelopeResult(CamelModel):
    """Outcome of checking a change request against the autonomous pricing envelope."""

    passed: bool
    failed_rules: list[str] = Field(default_factory=list)


class ChangeRequest(CamelModel):
    """An out-of-scope change request with estimate, options, approvals, and client choice."""

    id: str
    ask_id: str
    title: str
    room: ChatLink
    created_at: str
    status: ChangeRequestStatus
    estimate: Estimate | None = None
    confirmed_hours: int | None = None
    confirmed_by: str | None = None
    options: list[OptionQuote] = Field(default_factory=list)
    envelope: EnvelopeResult | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    approved_options: list[OptionKey] | None = None
    client_choice: OptionKey | Literal["DECLINE"] | None = None
    decided_at: str | None = None


class WorkItem(CamelModel):
    """An approved development ticket and branch assigned to the Builder."""

    id: str
    ask_id: str
    cr_id: str | None = None
    title: str
    branch: str
    pr_url: str | None = None
    preview_url: str | None = None
    status: WorkItemStatus


class DeskState(CamelModel):
    """Current holder and mode of the @client-desk role."""

    holder: Literal["priya", "scout"]
    mode: Literal["copilot", "autopilot"]
    since: str
    next_handover_at: str
    next_holder: Literal["priya", "scout"]


class ChangeOrdersOverview(CamelModel):
    """Monthly change order counts."""

    sent: int
    approved: int
    pending: int
    swaps: int


class GoodwillOverview(CamelModel):
    """Monthly goodwill hours usage."""

    used_hours: float
    bucket_hours: float


class Overview(CamelModel):
    """Dashboard KPI overview for a given month."""

    month: str
    revenue_protected_cents: int
    change_orders: ChangeOrdersOverview
    goodwill: GoodwillOverview
    median_ask_to_decision_minutes: float
    asks_by_category: dict[Category, int]


class LedgerEntry(CamelModel):
    """Single row in the audit ledger."""

    date: str
    ref: str
    title: str
    hours: float
    amount_cents: int
    approved_by: str | None = None
    link: ChatLink | None = None
    kind: Literal["change_order", "swap", "goodwill", "defect", "in_scope"]


class PlanItem(CamelModel):
    """One deliverable item within a project milestone."""

    id: str
    title: str
    deliverable: str
    hours: int
    status: Literal["done", "in_progress", "unstarted"]
    done_on: str | None = None
    priority: int | None = None

    @field_validator("done_on", mode="before")
    @classmethod
    def _coerce_done_on(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, date):
            return v.isoformat()
        return str(v)


class Milestone(CamelModel):
    """Project milestone containing scheduled plan items."""

    id: str
    name: str
    due: str
    items: list[PlanItem]

    @field_validator("due", mode="before")
    @classmethod
    def _coerce_due(cls, v: Any) -> str:
        if isinstance(v, date):
            return v.isoformat()
        return str(v)


class Plan(CamelModel):
    """Project delivery plan and weekly capacity."""

    capacity_hours_per_week: int = Field(gt=0)
    milestones: list[Milestone]


class Member(CamelModel):
    """Human or AI agent room participant."""

    id: str
    name: str
    kind: Literal["person", "agent"]
    side: Literal["client", "agency"]
    vendor: Literal["OpenCode", "Claude Code", "Codex", "Custom"] | None = None


class RoomRoleHolder(CamelModel):
    """Room role name and current holder."""

    name: str
    holder: str | None = None


class Room(CamelModel):
    """Switch room representation in the topology map."""

    id: str
    name: str
    app: ChatApp
    kind: Literal["client", "intake", "delivery", "change"]
    members: list[Member]
    roles: list[RoomRoleHolder]
    references: list[str]


class RoomLink(CamelModel):
    """Directed link between two Switch rooms."""

    from_: str = Field(alias="from")
    to: str
    description: str


class RoomMap(CamelModel):
    """Complete room topology for the dashboard React Flow view."""

    rooms: list[Room]
    links: list[RoomLink]


class StreamEvent(CamelModel):
    """Live Server-Sent Event payload broadcast to the dashboard."""

    id: str
    ts: str
    type: str
    actor: str
    text: str
    ask_id: str | None = None
    cr_id: str | None = None
    room_id: str | None = None
    link: ChatLink | None = None
    data: Any | None = None


# ── Configuration Models (config/*.yaml) ──────────────────────────────────────


class DeliverableSpec(CamelModel):
    """A deliverable clause in config/scope-map.yaml."""

    id: str
    clause: str
    title: str
    includes: list[str] = Field(default_factory=list)


class ExclusionSpec(CamelModel):
    """An explicit exclusion clause in config/scope-map.yaml."""

    clause: str
    text: str


class SwapPolicyConfig(CamelModel):
    """Scope swap rules in config/scope-map.yaml."""

    allowed: bool
    tolerance: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    only_unstarted: bool


class ChangePolicyConfig(CamelModel):
    """Change control policy in config/scope-map.yaml."""

    goodwill_hours_per_month: int = Field(ge=0)
    goodwill_suggest_below_hours: int = Field(ge=0)
    swap: SwapPolicyConfig


class ScopeMapConfig(CamelModel):
    """Validated schema for config/scope-map.yaml."""

    project: str
    client: str
    sow_version: str
    warranty_days: int = Field(ge=0)
    deliverables: list[DeliverableSpec]
    exclusions: list[ExclusionSpec]
    change_policy: ChangePolicyConfig


class ContingencyConfig(CamelModel):
    """Confidence contingency multipliers in config/rate-card.yaml."""

    high: Decimal = Field(ge=Decimal("0"))
    medium: Decimal = Field(ge=Decimal("0"))
    low: Decimal = Field(ge=Decimal("0"))

    def for_confidence(self, confidence: Confidence) -> Decimal:
        """Return the contingency multiplier for a given confidence level."""
        if confidence == Confidence.HIGH:
            return self.high
        if confidence == Confidence.MEDIUM:
            return self.medium
        return self.low


class RateCardConfig(CamelModel):
    """Validated schema for config/rate-card.yaml."""

    currency: str
    blended_rate: Decimal = Field(gt=Decimal("0"))
    contingency: ContingencyConfig
    round_to: int = Field(gt=0)


class EnvelopeConfig(CamelModel):
    """Validated schema for config/envelope.yaml."""

    max_price_usd: Decimal = Field(ge=Decimal("0"))
    min_confidence: Confidence
    milestone_impact_days: int = Field(ge=0)
    client_in_good_standing: bool


class FlipScheduleConfig(CamelModel):
    """Handover times and participants in config/schedule.yaml."""

    to_agent_at: str = Field(pattern=r"^\d{2}:\d{2}$")
    to_person_at: str = Field(pattern=r"^\d{2}:\d{2}$")
    agent: str
    person: str


class DemoScheduleConfig(CamelModel):
    """Simulated clock start time in config/schedule.yaml."""

    simulated_start: str


class ScheduleConfig(CamelModel):
    """Validated schema for config/schedule.yaml."""

    agency_timezone: str
    client_timezone: str
    flip: FlipScheduleConfig
    morning_brief_at: str = Field(pattern=r"^\d{2}:\d{2}$")
    demo: DemoScheduleConfig


class RoomGroupConfig(BaseModel):
    """Switch room group metadata in config/rooms.yaml."""

    name: str
    color: str


class RoomEndpointConfig(BaseModel):
    """Room name and Switch room ID in config/rooms.yaml."""

    name: str
    id: str


class RoomsMapConfig(BaseModel):
    """Core rooms mapping in config/rooms.yaml."""

    client: RoomEndpointConfig
    intake: RoomEndpointConfig
    delivery: RoomEndpointConfig
    change_room_prefix: str


class HandlesConfig(BaseModel):
    """Agent @handles in config/rooms.yaml."""

    scout: str
    estimator: str
    builder: str
    clerk: str


class PersonConfig(BaseModel):
    """Human participant metadata and governance roles in config/rooms.yaml."""

    display: str
    username: str
    side: Literal["client", "agency"]
    roles: list[str] = Field(default_factory=list)


class RoomsConfig(BaseModel):
    """Validated schema for config/rooms.yaml."""

    group: RoomGroupConfig
    rooms: RoomsMapConfig
    handles: HandlesConfig
    people: dict[str, PersonConfig]

    def role_holder_username(self, role: str) -> str | None:
        """Return the configured username holding a human governance role, if any."""
        for person in self.people.values():
            if role in person.roles:
                return person.username
        return None

    def is_authorized(self, sender_name: str, role: str) -> bool:
        """Check whether a sender (username or display name) holds the required role."""
        normalized = sender_name.strip().lstrip("@").lower()
        for key, person in self.people.items():
            if role in person.roles and normalized in {
                key.lower(),
                person.username.lower(),
                person.display.lower(),
            }:
                return True
        return False


class DecisionRecord(CamelModel):
    """A recorded scope/architecture decision."""

    id: str
    date: str
    text: str
    link: str
    source: Literal["seed", "client", "agency"]

    @field_validator("date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> str:
        if isinstance(v, date):
            return v.isoformat()
        return str(v)


class SeedGoodwillRecord(BaseModel):
    """Seed goodwill entry in config/seed-ledger.yaml."""

    id: str
    ask_id: str
    hours: int = Field(gt=0)
    reason: str
    approved_by: str
    month: str
    date: str | None = None
    link: str | None = None


class SeedLedgerConfig(BaseModel):
    """Validated schema for config/seed-ledger.yaml."""

    decisions: list[DecisionRecord] = Field(default_factory=list)
    asks: list[dict[str, Any]] = Field(default_factory=list)
    change_requests: list[dict[str, Any]] = Field(default_factory=list)
    goodwill: list[SeedGoodwillRecord] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    """Structured output returned by LLM classification and refined by post-rules."""

    category: Category
    clause_ids: list[str] = Field(default_factory=list)
    related_item: str | None = None
    decision_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    question: str | None = None
    choices: list[str] = Field(default_factory=list)


# ── Switch Template Models (switch/templates/*.template.yaml) ─────────────────


class SwitchTemplateParam(BaseModel):
    """Parameter definition in a Switch template."""

    type: str
    label: str | None = None
    default: Any | None = None
    input: str | None = None


class SwitchTemplateAgent(BaseModel):
    """Agent definition in a Switch template."""

    name: str
    display_name: str
    description: str
    provider: str
    location: str
    directory: str
    addressing: str
    allow_existing: bool = True
    instructions: str


class SwitchTemplateRole(BaseModel):
    """Role definition inside a room in a Switch template."""

    name: str
    exclusive: bool = False
    instructions: str


class SwitchTemplateDoc(BaseModel):
    """Attached document inside a room in a Switch template."""

    name: str
    description: str
    instructions: str
    content: str


class SwitchTemplateRoom(BaseModel):
    """Room definition in a Switch template."""

    name: str
    description: str
    bridge: str | None = None
    channel_type: str = "channel_public"
    agents: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    instructions: str
    roles: list[SwitchTemplateRole] = Field(default_factory=list)
    docs: list[SwitchTemplateDoc] = Field(default_factory=list)
    kickoff: str | None = None


class SwitchTemplateLink(BaseModel):
    """Link between rooms in a Switch template."""

    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    label: str


class SwitchTemplateGroup(BaseModel):
    """Room group metadata in a Switch template."""

    name: str
    description: str
    color: str


class SwitchTemplate(BaseModel):
    """Complete schema for switch/templates/*.template.yaml."""

    version: int = Field(ge=1)
    params: dict[str, SwitchTemplateParam] = Field(default_factory=dict)
    agents: list[SwitchTemplateAgent] = Field(default_factory=list)
    group: SwitchTemplateGroup
    rooms: list[SwitchTemplateRoom] = Field(default_factory=list)
    links: list[SwitchTemplateLink] = Field(default_factory=list)
    form: dict[str, Any] = Field(default_factory=dict)

