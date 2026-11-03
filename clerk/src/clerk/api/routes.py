# ruff: noqa: B008
"""FastAPI router implementing all Section 10 REST and SSE endpoints for ScopeKeeper."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from ruamel.yaml import YAML

from clerk.adapters.clock import parse_clock_offset
from clerk.api.auth import APIError, require_admin_token
from clerk.api.sse import EventBroadcaster
from clerk.db.repositories import LedgerRepository
from clerk.domain.dates import (
    is_autopilot_window,
    next_handover,
    to_agency_time,
    to_client_time,
)
from clerk.domain.goodwill import can_grant_goodwill
from clerk.domain.models import (
    AskStatus,
    Category,
    ChatApp,
    DeskState,
    EnvelopeConfig,
    Member,
    OptionKey,
    Plan,
    RateCardConfig,
    Room,
    RoomLink,
    RoomMap,
    RoomRoleHolder,
    ScheduleConfig,
    ScopeMapConfig,
)
from clerk.services.workflow import WorkflowOrchestrator
from clerk.settings import ConfigBundle, Settings

router = APIRouter(prefix="/api")


class CamelBody(BaseModel):
    """Base request model accepting both camelCase and snake_case keys."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class GoodwillRequest(CamelBody):
    hours: float | None = None
    reason: str | None = None


class ApproveCRRequest(CamelBody):
    options: list[OptionKey] = Field(default_factory=list)


class DeclineCRRequest(CamelBody):
    reason: str = "Not aligned with current release schedule"


class PriceOverrideRequest(CamelBody):
    price_cents: int


class ConfigUpdateRequest(CamelBody):
    config: dict[str, Any] | None = None
    yaml: str | None = None
    note: str = "Updated via dashboard Settings"


class DemoClockRequest(CamelBody):
    offset: str | None = None
    iso: str | None = None


def _get_orchestrator(request: Request) -> WorkflowOrchestrator:
    orch: WorkflowOrchestrator = request.app.state.orchestrator
    return orch


def _get_repo(request: Request) -> LedgerRepository:
    repo: LedgerRepository = request.app.state.repo
    return repo


def _get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _get_broadcaster(request: Request) -> EventBroadcaster:
    broadcaster: EventBroadcaster = request.app.state.broadcaster
    return broadcaster


@router.get("/health")
async def get_health(request: Request) -> dict[str, Any]:
    """Liveness, Switch connection state, and current clock (no auth required)."""
    orch = _get_orchestrator(request)
    settings = _get_settings(request)
    stopped = bool(getattr(orch.switch, "stopped", False))
    return {
        "status": "ok",
        "switchConnected": not stopped,
        "clock": orch.clock.now().isoformat(),
        "demoMode": settings.demo_mode,
    }


@router.get("/overview")
async def get_overview(
    request: Request,
    month: str | None = Query(default=None),
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """KPIs for the current or requested month (`Overview` contract)."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    target_month = month or orch.clock.now().isoformat()[:7]
    bucket_hours = float(orch.config.scope_map.change_policy.goodwill_hours_per_month)
    overview = repo.compute_overview(month=target_month, bucket_hours=bucket_hours)
    return overview.model_dump(by_alias=True)


@router.get("/desk")
async def get_desk(
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Current @client-desk holder, mode, and next handover in IST and ET (`DeskState`)."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    now_dt = orch.clock.now()
    schedule = orch.config.schedule

    client_room = orch._room_ref("acme-client", ChatApp.DISCORD)
    live_holder = await orch.switch.role_holder(client_room, "client-desk")
    in_autopilot = live_holder is not None or is_autopilot_window(now_dt, schedule)

    holder: Literal["priya", "scout"] = "scout" if in_autopilot else "priya"
    mode: Literal["copilot", "autopilot"] = "autopilot" if in_autopilot else "copilot"
    next_holder: Literal["priya", "scout"] = "priya" if in_autopilot else "scout"

    shifts = repo.list_role_shifts()
    since_iso = shifts[-1].at if shifts else "2026-11-05T09:30:00+05:30"
    next_ist, _next_holder_calc = next_handover(now_dt, schedule)
    next_et = to_client_time(next_ist, schedule)

    desk = DeskState(
        holder=holder,
        mode=mode,
        since=since_iso,
        next_handover_at=next_ist.isoformat(),
        next_holder=next_holder,
    )
    payload = desk.model_dump(by_alias=True)
    payload["nextHandoverEt"] = next_et.isoformat()
    payload["clockIst"] = to_agency_time(now_dt, schedule).isoformat()
    payload["clockEt"] = to_client_time(now_dt, schedule).isoformat()
    return payload


@router.get("/asks")
async def list_asks(
    request: Request,
    category: Category | None = Query(default=None),
    status_filter: AskStatus | None = Query(default=None, alias="status"),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _token: str = Depends(require_admin_token),
) -> list[dict[str, Any]]:
    """List asks with optional filters for category, status, and dates."""
    repo = _get_repo(request)
    asks = repo.list_asks(category=category, status=status_filter)
    if from_date:
        asks = [a for a in asks if a.created_at >= from_date]
    if to_date:
        asks = [a for a in asks if a.created_at <= to_date]
    sliced = asks[offset : offset + limit]
    return [a.model_dump(by_alias=True) for a in sliced]


@router.get("/asks/{ask_id}")
async def get_ask_detail(
    ask_id: str,
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Ask detail with its question, event timeline, and work items."""
    repo = _get_repo(request)
    ask = repo.get_ask(ask_id)
    if ask is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"Ask {ask_id!r} not found.",
        )
    data = ask.model_dump(by_alias=True)
    question = repo.get_question(ask.question_id) if ask.question_id else None
    events = repo.list_events(ask_id=ask.id)
    work_items = repo.list_work_items(ask_id=ask.id)
    cr = repo.get_change_request(ask.cr_id) if ask.cr_id else None

    data["question"] = question.model_dump(by_alias=True) if question else None
    data["events"] = [e.model_dump(by_alias=True) for e in events]
    data["workItems"] = [w.model_dump(by_alias=True) for w in work_items]
    data["changeRequest"] = cr.model_dump(by_alias=True) if cr else None
    return data


@router.post("/asks/{ask_id}/goodwill")
async def post_ask_goodwill(
    ask_id: str,
    request: Request,
    body: GoodwillRequest | None = None,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Mark an ask as goodwill from the monthly bucket and post in `acme-delivery`."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    ask = repo.get_ask(ask_id)
    if ask is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"Ask {ask_id!r} not found.",
        )

    now_iso = orch.clock.now().isoformat()
    month = now_iso[:7]
    hours = body.hours if (body and body.hours is not None) else 2.0
    if body is None or body.hours is None:
        if ask.cr_id:
            cr = repo.get_change_request(ask.cr_id)
            if cr and cr.confirmed_hours:
                hours = float(cr.confirmed_hours)
            elif cr and cr.estimate:
                hours = float(cr.estimate.full.p50_hours)

    used = repo.used_goodwill_hours(month)
    if not can_grant_goodwill(hours, used, orch.config.scope_map.change_policy):
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="goodwill_exceeded",
            message=f"Cannot grant {hours:g}h goodwill for {ask.id}: monthly bucket exceeded.",
        )

    reason = (
        body.reason
        if (body and body.reason)
        else "Courtesy goodwill approved by Priya from the dashboard"
    )
    delivery_room = orch._room_ref("acme-delivery", ChatApp.SLACK)
    msg_ref = await orch.switch.post(
        delivery_room,
        f"Priya granted {hours:g}h goodwill for {ask.id} from the dashboard ({reason}).",
    )
    repo.create_goodwill(
        ask_id=ask.id,
        hours=hours,
        reason=reason,
        approved_by="priya",
        month=month,
        date_str=now_iso[:10],
        link=msg_ref.url,
        ts=now_iso,
    )
    updated_ask = repo.update_ask(
        ask.id,
        status=AskStatus.ACCEPTED,
        decided_at=now_iso,
        event_type="ask.accepted",
        event_text=f"{ask.id} granted as {hours:g}h goodwill by priya",
        actor="priya",
        ts=now_iso,
        message_link=msg_ref.url,
    )
    return updated_ask.model_dump(by_alias=True)


@router.get("/change-requests")
async def list_change_requests(
    request: Request,
    _token: str = Depends(require_admin_token),
) -> list[dict[str, Any]]:
    """List all change requests."""
    repo = _get_repo(request)
    return [cr.model_dump(by_alias=True) for cr in repo.list_change_requests()]


@router.get("/change-requests/{cr_id}")
async def get_change_request_detail(
    cr_id: str,
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Change request detail with estimate, options, envelope, events, and work items."""
    repo = _get_repo(request)
    cr = repo.get_change_request(cr_id)
    if cr is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"ChangeRequest {cr_id!r} not found.",
        )
    data = cr.model_dump(by_alias=True)
    events = repo.list_events(cr_id=cr.id)
    ask_work = repo.list_work_items(ask_id=cr.ask_id)
    data["events"] = [e.model_dump(by_alias=True) for e in events]
    data["workItems"] = [w.model_dump(by_alias=True) for w in ask_work]
    return data


@router.post("/change-requests/{cr_id}/approve")
async def approve_change_request(
    cr_id: str,
    request: Request,
    body: ApproveCRRequest | None = None,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Approve all or selected options; posts 'Priya approved A, C, D from the dashboard'."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    cr = repo.get_change_request(cr_id)
    if cr is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"ChangeRequest {cr_id!r} not found.",
        )
    options = body.options if (body and body.options) else None
    updated = await orch.cr_service.approve_change_request(
        cr.id,
        approved_by="priya",
        approved_options=options,
        from_dashboard=True,
    )
    return updated.model_dump(by_alias=True)


@router.post("/change-requests/{cr_id}/decline")
async def decline_change_request(
    cr_id: str,
    body: DeclineCRRequest,
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Decline a change request and post the reason in the room."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    cr = repo.get_change_request(cr_id)
    if cr is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"ChangeRequest {cr_id!r} not found.",
        )
    updated = await orch.cr_service.decline_change_request(
        cr.id,
        declined_by="priya",
        reason=body.reason,
    )
    return updated.model_dump(by_alias=True)


@router.patch("/change-requests/{cr_id}/options/{option_key}")
async def patch_change_request_option_price(
    cr_id: str,
    option_key: OptionKey,
    body: PriceOverrideRequest,
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Override one option's price (in cents) and log the override."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    cr = repo.get_change_request(cr_id)
    if cr is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"ChangeRequest {cr_id!r} not found.",
        )
    price_usd = Decimal(body.price_cents) / Decimal(100)
    try:
        updated = await orch.cr_service.override_option_price(
            cr.id,
            option_key=option_key,
            price_usd=price_usd,
            actor="priya",
        )
    except ValueError as exc:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_option",
            message=str(exc),
        ) from exc
    return updated.model_dump(by_alias=True)


@router.get("/rooms")
async def get_rooms_map(
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Return `RoomMap` (rooms, members, roles, links) for the React Flow diagram."""
    orch = _get_orchestrator(request)
    build_fn = getattr(orch.switch, "build_room_map", None)
    if callable(build_fn):
        rm: RoomMap = build_fn()
        return rm.model_dump(by_alias=True)

    # Construct RoomMap from config + active change rooms when using SwitchProtocolAdapter
    client_room = orch._room_ref("acme-client", ChatApp.DISCORD)
    holder = await orch.switch.role_holder(client_room, "client-desk")
    members_catalog = {
        "sam": Member(id="sam", name="Sam", kind="person", side="client"),
        "priya": Member(id="priya", name="Priya", kind="person", side="agency"),
        "ravi": Member(id="ravi", name="Ravi", kind="person", side="agency"),
        "aisha": Member(id="aisha", name="Aisha", kind="person", side="agency"),
        "acme-scout": Member(
            id="acme-scout", name="Scout", kind="agent", side="agency", vendor="OpenCode"
        ),
        "clerk": Member(
            id="clerk", name="Clerk", kind="agent", side="agency", vendor="Custom"
        ),
        "acme-estimator": Member(
            id="acme-estimator",
            name="Estimator",
            kind="agent",
            side="agency",
            vendor="Claude Code",
        ),
        "acme-builder": Member(
            id="acme-builder", name="Builder", kind="agent", side="agency", vendor="Codex"
        ),
    }
    rooms = [
        Room(
            id=client_room.id,
            name="acme-client",
            app=ChatApp.DISCORD,
            kind="client",
            members=[
                members_catalog["sam"],
                members_catalog["priya"],
                members_catalog["acme-scout"],
            ],
            roles=[RoomRoleHolder(name="client-desk", holder=holder)],
            references=["scope-summary"],
        ),
        Room(
            id="room-acme-intake",
            name="acme-intake",
            app=ChatApp.SLACK,
            kind="intake",
            members=[
                members_catalog["priya"],
                members_catalog["acme-scout"],
                members_catalog["clerk"],
            ],
            roles=[],
            references=["SOW.md", "scope-map.yaml", "plan.yaml"],
        ),
        Room(
            id="room-acme-delivery",
            name="acme-delivery",
            app=ChatApp.SLACK,
            kind="delivery",
            members=[
                members_catalog["priya"],
                members_catalog["ravi"],
                members_catalog["aisha"],
                members_catalog["clerk"],
                members_catalog["acme-estimator"],
                members_catalog["acme-builder"],
            ],
            roles=[
                RoomRoleHolder(name="account-manager", holder="priya"),
                RoomRoleHolder(name="delivery-lead", holder="ravi"),
            ],
            references=[
                "SOW.md",
                "scope-map.yaml",
                "plan.yaml",
                "rate-card.yaml",
                "envelope.yaml",
            ],
        ),
    ]
    links = [
        RoomLink.model_validate(
            {
                "from": "acme-client",
                "to": "acme-intake",
                "description": "asks in, client-ready answers out",
            }
        ),
        RoomLink.model_validate(
            {
                "from": "acme-intake",
                "to": "acme-delivery",
                "description": "approved work becomes tickets",
            }
        ),
    ]
    return RoomMap(rooms=rooms, links=links).model_dump(by_alias=True)


@router.get("/public/co/{cr_id}")
async def get_public_change_order(
    cr_id: str,
    request: Request,
) -> dict[str, Any]:
    """Read-only change order for the client public page `/co/:id` (no auth required)."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    cr = repo.get_change_request(cr_id)
    if cr is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"Change Order {cr_id!r} not found.",
        )
    ask = repo.get_ask(cr.ask_id)
    clause_id = ask.clause_ids[0] if (ask and ask.clause_ids) else "6.1"
    clause_text = "Changes outside the signed deliverables require a written Change Order."
    for ex in orch.config.scope_map.exclusions:
        if ex.clause == clause_id:
            clause_text = ex.text
            break
    for d in orch.config.scope_map.deliverables:
        if d.clause == clause_id:
            clause_text = f"{d.title}: {', '.join(d.includes)}"
            break

    data = cr.model_dump(by_alias=True)
    data["clientCompany"] = "Acme Inc."
    data["agencyCompany"] = "Pixel & Co"
    data["quote"] = ask.quote if ask else cr.title
    data["requester"] = ask.requester if ask else "Sam"
    data["clauseId"] = clause_id
    data["clauseText"] = clause_text
    return data


@router.get("/ledger")
async def get_ledger(
    request: Request,
    month: str | None = Query(default=None),
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Ledger summary (`overview`) and rows (`entries`) for `month`."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    target_month = month or orch.clock.now().isoformat()[:7]
    bucket_hours = float(orch.config.scope_map.change_policy.goodwill_hours_per_month)
    overview = repo.compute_overview(month=target_month, bucket_hours=bucket_hours)
    entries = repo.compute_ledger_entries(month=target_month)
    return {
        "month": target_month,
        "overview": overview.model_dump(by_alias=True),
        "entries": [e.model_dump(by_alias=True) for e in entries],
    }


@router.get("/invoice")
async def get_invoice_csv(
    request: Request,
    month: str | None = Query(default=None),
    _token: str = Depends(require_admin_token),
) -> Response:
    """CSV invoice download (`date,change,option,hours,price_usd,approved_by,link`)."""
    orch = _get_orchestrator(request)
    target_month = month or orch.clock.now().isoformat()[:7]
    csv_str = orch.invoice_service.render_csv_for_month(target_month)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="scopekeeper-invoice-{target_month}.csv"'
        },
    )


@router.get("/renewal")
async def get_renewal_report(
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Next-phase renewal report grouping out-of-scope asks with hours summed in code."""
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    report_md = await orch.renewal_service.generate_report()
    oos_asks = repo.list_asks(category=Category.OUT_OF_SCOPE)
    crs_by_ask = {cr.ask_id: cr for cr in repo.list_change_requests()}
    items = []
    total_hours = 0
    for ask in oos_asks:
        cr = crs_by_ask.get(ask.id)
        hrs = (
            cr.confirmed_hours
            if (cr and cr.confirmed_hours is not None)
            else (cr.estimate.full.p50_hours if (cr and cr.estimate) else 0)
        )
        total_hours += hrs
        items.append({"askId": ask.id, "quote": ask.quote, "hours": hrs})
    return {
        "report": report_md,
        "totalHours": total_hours,
        "items": items,
    }


_CONFIG_MODELS: dict[str, type[BaseModel]] = {
    "scope-map": ScopeMapConfig,
    "rate-card": RateCardConfig,
    "envelope": EnvelopeConfig,
    "plan": Plan,
    "schedule": ScheduleConfig,
}


@router.get("/config/{name}")
async def get_config_by_name(
    name: str,
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Read `scope-map`, `rate-card`, `envelope`, `plan`, or `schedule`."""
    if name not in _CONFIG_MODELS:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="unknown_config",
            message=f"Unknown config {name!r}; expected one of {sorted(_CONFIG_MODELS)}.",
        )
    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    attr_name = name.replace("-", "_")
    model_instance: BaseModel = (
        repo.get_plan() if name == "plan" else getattr(orch.config, attr_name)
    )
    return model_instance.model_dump(by_alias=True)


@router.put("/config/{name}")
async def update_config_by_name(
    name: str,
    body: ConfigUpdateRequest,
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Validate and update a config (`scope-map`, `rate-card`, `envelope`, `plan`, `schedule`)."""
    model_cls = _CONFIG_MODELS.get(name)
    if model_cls is None:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="unknown_config",
            message=f"Unknown config {name!r}; expected one of {sorted(_CONFIG_MODELS)}.",
        )

    orch = _get_orchestrator(request)
    repo = _get_repo(request)
    raw_data: Any = body.config
    if raw_data is None and body.yaml:
        yaml_parser = YAML(typ="safe")
        try:
            raw_data = yaml_parser.load(body.yaml)
        except Exception as exc:
            raise APIError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_yaml",
                message=f"YAML syntax error: {exc}",
            ) from exc

    if raw_data is None:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_payload",
            message="Provide either `config` JSON or `yaml` string.",
        )

    try:
        validated = model_cls.model_validate(raw_data)
    except Exception as exc:
        raise APIError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message=str(exc),
        ) from exc

    attr_name = name.replace("-", "_")
    if isinstance(validated, Plan):
        repo.save_plan(validated)

    # Update ConfigBundle in-place on orchestrator
    updated_bundle = ConfigBundle(
        config_dir=orch.config.config_dir,
        scope_map=validated if isinstance(validated, ScopeMapConfig) else orch.config.scope_map,
        rate_card=validated if isinstance(validated, RateCardConfig) else orch.config.rate_card,
        plan=validated if isinstance(validated, Plan) else orch.config.plan,
        envelope=validated if isinstance(validated, EnvelopeConfig) else orch.config.envelope,
        schedule=validated if isinstance(validated, ScheduleConfig) else orch.config.schedule,
        rooms=orch.config.rooms,
        seed_ledger=orch.config.seed_ledger,
        sow_markdown=orch.config.sow_markdown,
    )
    orch.config = updated_bundle
    request.app.state.config = updated_bundle

    now_iso = orch.clock.now().isoformat()
    if body.note:
        repo.create_decision(
            text=f"[{name}] {body.note}",
            date_str=now_iso[:10],
            link=f"https://slack.com/archives/acme-delivery/config-{attr_name}",
            source="agency",
        )

    return validated.model_dump(by_alias=True)


def _require_demo_mode(request: Request) -> None:
    settings = _get_settings(request)
    if not settings.demo_mode:
        raise APIError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="demo_mode_disabled",
            message="Demo controls are only enabled when DEMO_MODE=true.",
        )


@router.post("/demo/flip")
async def demo_flip(
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Toggle the @client-desk handover immediately (requires DEMO_MODE=true)."""
    _require_demo_mode(request)
    orch = _get_orchestrator(request)
    client_room = orch._room_ref("acme-client", ChatApp.DISCORD)
    holder = await orch.switch.role_holder(client_room, "client-desk")
    if holder is None:
        shift = await orch.flip_service.flip_to_autopilot()
    else:
        shift = await orch.flip_service.flip_to_copilot(post_brief=True)
    return {
        "role": shift.role,
        "fromHolder": shift.from_holder,
        "toHolder": shift.to_holder,
        "at": shift.at,
        "verified": shift.verified,
    }


@router.post("/demo/morning")
async def demo_morning(
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Trigger the 9:30 AM IST morning brief and copilot handover (requires DEMO_MODE=true)."""
    _require_demo_mode(request)
    orch = _get_orchestrator(request)
    shift = await orch.flip_service.flip_to_copilot(post_brief=True)
    return {
        "role": shift.role,
        "fromHolder": shift.from_holder,
        "toHolder": shift.to_holder,
        "at": shift.at,
        "verified": shift.verified,
    }


@router.post("/demo/clock")
async def demo_clock(
    body: DemoClockRequest,
    request: Request,
    _token: str = Depends(require_admin_token),
) -> dict[str, Any]:
    """Advance or set the simulated clock and trigger any crossed handovers."""
    _require_demo_mode(request)
    orch = _get_orchestrator(request)
    if body.offset:
        try:
            delta = parse_clock_offset(body.offset)
        except ValueError as exc:
            raise APIError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_offset",
                message=str(exc),
            ) from exc
        new_dt = orch.clock.advance(delta)
    elif body.iso:
        from datetime import datetime

        try:
            parsed = datetime.fromisoformat(body.iso.replace("Z", "+00:00"))
            orch.clock.set_time(parsed)
            new_dt = orch.clock.now()
        except ValueError as exc:
            raise APIError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_iso",
                message=str(exc),
            ) from exc
    else:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="missing_clock_arg",
            message="Provide either `offset` (e.g. '+10h') or `iso` timestamp.",
        )

    orch.repo.set_setting("clock_iso", new_dt.isoformat())
    shifts = await orch.scheduler.tick()
    return {
        "clock": new_dt.isoformat(),
        "handoversTriggered": len(shifts),
    }


@router.get("/stream")
async def stream_events(
    request: Request,
    limit: int = Query(default=25, ge=0, le=200),
    max_events: int | None = Query(default=None),
    _token: str = Depends(require_admin_token),
) -> StreamingResponse:
    """Server-Sent Events (SSE) stream of live `StreamEvent` payloads (`text/event-stream`)."""
    repo = _get_repo(request)
    broadcaster = _get_broadcaster(request)
    initial = repo.list_events(limit=limit) if limit > 0 else []
    generator = broadcaster.subscribe(initial_events=initial, max_events=max_events)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
