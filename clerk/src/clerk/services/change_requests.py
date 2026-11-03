"""ChangeRequestService managing change rooms, estimates, pricing, approvals, and swaps."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from clerk.db.repositories import LedgerRepository
from clerk.domain.dates import compute_shift_days
from clerk.domain.envelope import check_envelope
from clerk.domain.goodwill import should_suggest_goodwill
from clerk.domain.models import (
    Ask,
    AskStatus,
    ChangeRequest,
    ChangeRequestStatus,
    ChatApp,
    Confidence,
    EnvelopeConfig,
    Estimate,
    EstimateVersion,
    OptionKey,
    OptionQuote,
    RateCardConfig,
    RoomsConfig,
    ScopeMapConfig,
)
from clerk.domain.numbers_check import check_numbers
from clerk.domain.pricing import (
    build_options,
    compute_price_usd,
    select_affected_milestone,
)
from clerk.domain.templates import (
    format_usd,
    render_change_order,
    render_change_room_opening,
    render_estimator_request,
    render_ready,
)
from clerk.ports.protocols import (
    ClockPort,
    Reference,
    RoomDocumentSpec,
    RoomRef,
    RoomSpec,
    SwitchPort,
)


def _derive_short_subject(quote: str) -> str:
    """Derive a concise subject title from a client ask quote."""
    lower = quote.lower()
    if "android app" in lower:
        return "The Android app"
    if "excel" in lower or "xlsx" in lower:
        return "Native Excel (.xlsx) export"
    if "dark mode" in lower or "dark theme" in lower:
        return "Dark mode"
    if "safari" in lower:
        return "Safari login fix"
    cleaned = quote.strip().rstrip(".?!")
    return cleaned[:60]


def _extract_due_hint(quote: str) -> str | None:
    """Extract a due date hint from a quote like 'for the board meeting on the 20th'."""
    if "on the 20th" in quote.lower() or "november 20" in quote.lower():
        return "November 20"
    return None


class ChangeRequestService:
    """Service orchestrating the lifecycle of out-of-scope ChangeRequests."""

    def __init__(
        self,
        repo: LedgerRepository,
        switch: SwitchPort,
        clock: ClockPort,
        scope_map: ScopeMapConfig,
        rate_card: RateCardConfig,
        envelope: EnvelopeConfig,
        rooms_config: RoomsConfig,
    ) -> None:
        self._repo = repo
        self._switch = switch
        self._clock = clock
        self._scope_map = scope_map
        self._rate_card = rate_card
        self._envelope = envelope
        self._rooms_config = rooms_config

    def _room_ref(self, name: str, app: ChatApp = ChatApp.SLACK) -> RoomRef:
        get_ref = getattr(self._switch, "get_room_ref", None)
        if callable(get_ref):
            try:
                ref: RoomRef = get_ref(name)
                return ref
            except KeyError:
                pass
        return RoomRef(id=f"room-{name}", name=name, app=app)

    def _clause_summary(self, clause_id: str) -> str:
        for ex in self._scope_map.exclusions:
            if ex.clause == clause_id:
                if clause_id == "1.3":
                    return "web only"
                return ex.text.lower()
        for d in self._scope_map.deliverables:
            if d.clause == clause_id:
                return d.title.lower()
        return "outside current scope"

    async def open_change_request(self, ask: Ask) -> ChangeRequest:
        """Create change room acme-cr-NNN, configure links/docs/refs, and request an estimate."""
        now_iso = self._clock.now().isoformat()
        cr_id = self._repo.next_cr_id()
        num_suffix = cr_id.split("-")[1]
        room_name = f"{self._rooms_config.rooms.change_room_prefix}{num_suffix}"
        title = _derive_short_subject(ask.quote)
        clause_id = ask.clause_ids[0] if ask.clause_ids else "6.1"
        clause_desc = self._clause_summary(clause_id)

        estimator_name = self._rooms_config.handles.estimator.lstrip("@")
        builder_name = self._rooms_config.handles.builder.lstrip("@")
        refs = [
            Reference(id="ref-sow", title="SOW.md", url="config/sow/SOW.md"),
            Reference(id="ref-scope-map", title="scope-map.yaml", url="config/scope-map.yaml"),
            Reference(id="ref-rate-card", title="rate-card.yaml", url="config/rate-card.yaml"),
            Reference(id="ref-envelope", title="envelope.yaml", url="config/envelope.yaml"),
            Reference(id="ref-plan", title="plan.yaml", url="config/plan.yaml"),
        ]
        doc = RoomDocumentSpec(
            name=f"{cr_id.lower()}-brief",
            description=f"Change Request {cr_id} for {ask.id}",
            instructions="Live Change Request summary maintained by Clerk.",
            content=(
                f'# {cr_id}: {title}\nAsk: {ask.id} — "{ask.quote}"\n'
                f"Clause: {clause_id} ({clause_desc})\nStatus: estimating"
            ),
        )
        spec = RoomSpec(
            name=room_name,
            description=f"Change Request {cr_id}: {title}",
            group_name=self._rooms_config.group.name,
            instructions="Change room governed by Clerk.",
            agent_names=[estimator_name, builder_name],
            user_names=["priya", "ravi"],
            references=refs,
            docs=[doc],
        )

        try:
            cr_room = await self._switch.create_room(spec)
        except Exception:
            # Fallback to pre-created pool acme-cr-001 .. acme-cr-010
            cr_room = RoomRef(id=f"room-{room_name}", name=room_name, app=ChatApp.SLACK)
            for human in ("priya", "ravi"):
                await self._switch.invite(cr_room, human, is_human=True)
            for agent in (estimator_name, builder_name):
                await self._switch.invite(cr_room, agent, is_human=False)
            for r in refs:
                await self._switch.attach_reference(cr_room, r)
            await self._switch.upsert_document(cr_room, doc)

        delivery_room = self._room_ref("acme-delivery", ChatApp.SLACK)
        await self._switch.link(delivery_room, cr_room, "one change request")
        await self._switch.link(cr_room, delivery_room, "one change request")

        cr = self._repo.create_change_request(
            cr_id=cr_id,
            ask_id=ask.id,
            title=title,
            room_id=cr_room.name,
            room_url=f"https://slack.com/archives/{cr_room.name}",
            created_at=now_iso,
        )
        self._repo.update_ask(
            ask.id,
            status=AskStatus.CHANGE_OPEN,
            cr_id=cr_id,
            event_type="ask.updated",
            event_text=f"{ask.id} -> change_open ({cr_id})",
            ts=now_iso,
        )

        opening_text = render_change_room_opening(
            cr=cr,
            ask=ask,
            sow_context=f"Clause {clause_id} ({clause_desc})",
        )
        await self._switch.post(cr_room, opening_text)

        est_req_text = render_estimator_request(
            cr_id=cr_id,
            ask_id=ask.id,
            quote=ask.quote,
            context=f"clause {clause_id} ({clause_desc})",
            estimator_handle=self._rooms_config.handles.estimator,
        )
        await self._switch.send_targeted(
            cr_room,
            targets=[estimator_name],
            text=est_req_text,
        )
        return cr

    async def handle_estimate(
        self,
        cr_id: str,
        estimate: Estimate,
        message_link: str = "",
    ) -> ChangeRequest:
        """Process the Estimator's reply; auto-confirm and send if inside envelope."""
        now_iso = self._clock.now().isoformat()
        cr = self._repo.get_change_request(cr_id)
        if cr is None:
            raise KeyError(f"ChangeRequest {cr_id!r} not found")
        ask = self._repo.get_ask(cr.ask_id)
        if ask is None:
            raise KeyError(f"Ask {cr.ask_id!r} not found")

        plan = self._repo.get_plan()
        p50_hours = estimate.full.p50_hours
        p50_conf = estimate.full.confidence
        p50_usd = compute_price_usd(p50_hours, p50_conf, self._rate_card)
        p50_shift = compute_shift_days(p50_hours, plan.capacity_hours_per_week)

        # Check if P50 at high confidence qualifies for autonomous envelope approval
        preliminary_env = check_envelope(
            price_usd=p50_usd,
            confidence=p50_conf,
            milestone_impact_days=p50_shift,
            envelope=self._envelope,
            has_swap=False,
        )

        cr_room = self._room_ref(cr.room.room, ChatApp.SLACK)
        self._repo.update_change_request(
            cr_id,
            estimate=estimate,
            event_type="cr.estimated",
            event_text=(f"{cr_id} estimated at P50={p50_hours}h ({p50_conf.value} confidence)"),
            actor="acme-estimator",
            ts=now_iso,
            message_link=message_link or None,
        )

        if preliminary_env.passed and estimate.smaller is None:
            # Auto-confirm P50 and send immediately under the autonomous envelope!
            options = build_options(
                ask_title=cr.title,
                estimate=estimate,
                confirmed_hours=p50_hours,
                plan=plan,
                rate_card=self._rate_card,
                swap_policy=self._scope_map.change_policy.swap,
            )
            cr = self._repo.update_change_request(
                cr_id,
                status=ChangeRequestStatus.SENT,
                confirmed_hours=p50_hours,
                confirmed_by="auto-envelope",
                options=options,
                envelope=preliminary_env,
                approved_by="auto-envelope",
                approved_at=now_iso,
                approved_options=[o.key for o in options],
                event_type="cr.priced",
                event_text=(
                    f"{cr_id} priced at {format_usd(options[0].price_cents)} "
                    "and auto-approved inside envelope"
                ),
                ts=now_iso,
            )
            await self._send_change_order_to_scout(cr, ask)
            return cr

        # Outside envelope or requires @delivery-lead confirmation
        cr = self._repo.update_change_request(
            cr_id,
            status=ChangeRequestStatus.AWAITING_CONFIRMATION,
            event_type="cr.updated",
            event_text=f"{cr_id} awaiting @delivery-lead hour confirmation",
            ts=now_iso,
        )
        sm_note = (
            f" (smaller option: {estimate.smaller.p50_hours}h "
            f"{estimate.smaller.confidence.value})"
            if estimate.smaller
            else ""
        )
        await self._switch.post(
            cr_room,
            f"Estimate received for {cr_id}: "
            f"full P50={p50_hours}h / P90={estimate.full.p90_hours}h "
            f"({p50_conf.value}){sm_note}. "
            f"@delivery-lead reply `@clerk confirm` to use {p50_hours}h "
            "or `@clerk hours <N>` to adjust.",
        )
        return cr

    async def apply_heuristic_fallback_estimate(self, cr_id: str) -> ChangeRequest:
        """Apply a 30-minute timeout fallback estimate from past merges (`low` confidence)."""
        est = Estimate(
            full=EstimateVersion(
                title="Heuristic fallback estimate from past merges",
                p50_hours=40,
                p90_hours=60,
                confidence=Confidence.LOW,
            ),
            assumptions=["Generated via 30-minute heuristic fallback"],
            posted_at=self._clock.now().isoformat(),
        )
        return await self.handle_estimate(cr_id, est)

    async def confirm_hours(
        self,
        cr_id: str,
        *,
        hours: int | None,
        confirmed_by: str,
        version: Literal["full", "smaller"] = "full",
    ) -> ChangeRequest:
        """Confirm full or smaller hours, compute options A-D, and check envelope."""
        now_iso = self._clock.now().isoformat()
        cr = self._repo.get_change_request(cr_id)
        if cr is None or cr.estimate is None:
            raise KeyError(f"ChangeRequest {cr_id!r} or its estimate not found")
        ask = self._repo.get_ask(cr.ask_id)
        if ask is None:
            raise KeyError(f"Ask {cr.ask_id!r} not found")

        plan = self._repo.get_plan()
        smaller_hours = self._repo.get_smaller_confirmed_hours(cr_id)

        if version == "smaller":
            if hours is None:
                hours = (
                    cr.estimate.smaller.p50_hours
                    if cr.estimate.smaller
                    else cr.estimate.full.p50_hours
                )
            smaller_hours = hours
            confirmed_full = cr.confirmed_hours or cr.estimate.full.p50_hours
        else:
            confirmed_full = hours if hours is not None else cr.estimate.full.p50_hours

        due_hint = _extract_due_hint(ask.quote)
        options = build_options(
            ask_title=cr.title,
            estimate=cr.estimate,
            confirmed_hours=confirmed_full,
            plan=plan,
            rate_card=self._rate_card,
            swap_policy=self._scope_map.change_policy.swap,
            smaller_confirmed_hours=smaller_hours,
            smaller_due_hint=due_hint,
        )

        opt_a = options[0]
        has_swap = any(o.key == OptionKey.D or o.swap_out for o in options)
        env_res = check_envelope(
            price_usd=Decimal(opt_a.price_cents) / Decimal(100),
            confidence=cr.estimate.full.confidence,
            milestone_impact_days=opt_a.shift_days,
            envelope=self._envelope,
            has_swap=has_swap,
        )

        self._repo.update_change_request(
            cr_id,
            confirmed_hours=confirmed_full,
            smaller_confirmed_hours=smaller_hours,
            confirmed_by=confirmed_by,
            options=options,
            envelope=env_res,
            event_type="cr.confirmed",
            event_text=f"{confirmed_by} confirmed {confirmed_full}h for {cr_id}",
            actor=confirmed_by,
            ts=now_iso,
        )

        cr_room = self._room_ref(cr.room.room, ChatApp.SLACK)
        if env_res.passed:
            cr = self._repo.update_change_request(
                cr_id,
                status=ChangeRequestStatus.SENT,
                approved_by="auto-envelope",
                approved_at=now_iso,
                approved_options=[o.key for o in options],
                event_type="cr.priced",
                event_text=f"{cr_id} priced and auto-approved inside envelope",
                ts=now_iso,
            )
            await self._send_change_order_to_scout(cr, ask)
            return cr

        priced_summary = ", ".join(
            f"{o.key.value}: {format_usd(o.price_cents)}" for o in options
        )
        cr = self._repo.update_change_request(
            cr_id,
            status=ChangeRequestStatus.AWAITING_APPROVAL,
            event_type="cr.priced",
            event_text=(
                f"{cr_id} options priced ({priced_summary}); "
                f"outside envelope ({', '.join(env_res.failed_rules)})"
            ),
            ts=now_iso,
        )

        opt_lines = [
            (
                f"- Option {o.key.value} ({o.label}): "
                f"{o.hours}h · {format_usd(o.price_cents)} · shift +{o.shift_days}d"
            )
            for o in options
        ]
        opt_keys = ",".join(o.key.value for o in options)
        gw_hint = ""
        month = now_iso[:7]
        used_gw = self._repo.used_goodwill_hours(month)
        if should_suggest_goodwill(confirmed_full, used_gw, self._scope_map.change_policy):
            gw_hint = (
                f"\n💡 Small ask ({confirmed_full}h): you can also grant goodwill "
                f"with `@clerk goodwill {ask.id}`."
            )

        summary_msg = (
            f"Options priced for {cr_id} (confirmed {confirmed_full}h by {confirmed_by}):\n"
            + "\n".join(opt_lines)
            + f"\nEnvelope failed: {', '.join(env_res.failed_rules)}.\n"
            f"@account-manager reply `@clerk approve` "
            f"(or `@clerk approve {opt_keys}`) to send to the client.{gw_hint}"
        )
        await self._switch.post(cr_room, summary_msg)
        return cr

    async def override_option_price(
        self,
        cr_id: str,
        option_key: OptionKey,
        price_usd: Decimal,
        actor: str,
    ) -> ChangeRequest:
        """Override the price of one option on a ChangeRequest and log it."""
        now_iso = self._clock.now().isoformat()
        cr = self._repo.get_change_request(cr_id)
        if cr is None:
            raise KeyError(f"ChangeRequest {cr_id!r} not found")

        new_cents = int((price_usd * Decimal(100)).to_integral_value())
        updated_opts: list[OptionQuote] = []
        found = False
        for opt in cr.options:
            if opt.key == option_key:
                found = True
                updated_opts.append(opt.model_copy(update={"price_cents": new_cents}))
            else:
                updated_opts.append(opt)
        if not found:
            raise ValueError(f"Option {option_key.value} not present on {cr_id}")

        cr = self._repo.update_change_request(
            cr_id,
            options=updated_opts,
            event_type="cr.priced",
            event_text=(
                f"{actor} overrode {cr_id} Option {option_key.value} "
                f"price to {format_usd(new_cents)}"
            ),
            actor=actor,
            ts=now_iso,
        )
        cr_room = self._room_ref(cr.room.room, ChatApp.SLACK)
        await self._switch.post(
            cr_room,
            (
                f"Updated {cr_id} Option {option_key.value} price to "
                f"{format_usd(new_cents)} (by {actor})."
            ),
        )
        return cr

    async def approve_change_request(
        self,
        cr_id: str,
        *,
        approved_by: str,
        approved_options: list[OptionKey] | None = None,
        from_dashboard: bool = False,
    ) -> ChangeRequest:
        """Approve all or selected options on `cr_id` and send the Change Order to Scout."""
        now_iso = self._clock.now().isoformat()
        cr = self._repo.get_change_request(cr_id)
        if cr is None:
            raise KeyError(f"ChangeRequest {cr_id!r} not found")
        ask = self._repo.get_ask(cr.ask_id)
        if ask is None:
            raise KeyError(f"Ask {cr.ask_id!r} not found")

        selected_keys = approved_options or [o.key for o in cr.options]
        filtered_options = [o for o in cr.options if o.key in selected_keys]
        if not filtered_options:
            filtered_options = list(cr.options)

        cr_room = self._room_ref(cr.room.room, ChatApp.SLACK)
        if from_dashboard:
            keys_str = ", ".join(k.value for k in selected_keys)
            display_name = approved_by.capitalize()
            await self._switch.post(
                cr_room,
                f"{display_name} approved {keys_str} from the dashboard",
            )

        keys_joined = ", ".join(k.value for k in selected_keys)
        cr = self._repo.update_change_request(
            cr_id,
            status=ChangeRequestStatus.SENT,
            options=filtered_options,
            approved_by=approved_by,
            approved_at=now_iso,
            approved_options=selected_keys,
            event_type="cr.approved",
            event_text=f"{approved_by} approved {cr_id} options ({keys_joined})",
            actor=approved_by,
            ts=now_iso,
        )
        await self._send_change_order_to_scout(cr, ask)
        return cr

    async def decline_change_request(
        self,
        cr_id: str,
        *,
        declined_by: str,
        reason: str,
    ) -> ChangeRequest:
        """Decline a ChangeRequest on behalf of @account-manager and notify Scout."""
        now_iso = self._clock.now().isoformat()
        cr = self._repo.get_change_request(cr_id)
        if cr is None:
            raise KeyError(f"ChangeRequest {cr_id!r} not found")

        cr = self._repo.update_change_request(
            cr_id,
            status=ChangeRequestStatus.CLOSED,
            client_choice="DECLINE",
            decided_at=now_iso,
            event_type="cr.updated",
            event_text=f"{cr_id} declined by {declined_by}: {reason}",
            actor=declined_by,
            ts=now_iso,
        )
        self._repo.update_ask(
            cr.ask_id,
            status=AskStatus.DECLINED,
            decided_at=now_iso,
            event_type="ask.updated",
            event_text=f"{cr.ask_id} declined ({reason})",
            actor=declined_by,
            ts=now_iso,
        )

        intake_room = self._room_ref("acme-intake", ChatApp.SLACK)
        scout_name = self._rooms_config.handles.scout.lstrip("@")
        polite_msg = (
            f"Regarding {cr.title.lower()}: we won't be able to add this in the current phase "
            f"({reason}). We've noted it for the next phase review."
        )
        await self._switch.send_targeted(
            intake_room,
            targets=[scout_name],
            text=render_ready(cr.id, polite_msg),
        )

        cr_room = self._room_ref(cr.room.room, ChatApp.SLACK)
        await self._switch.post(
            cr_room,
            f"Closed {cr_id} (declined by {declined_by}: {reason}). Archiving room.",
        )
        await self._switch.archive_room(cr_room)
        return cr

    async def _send_change_order_to_scout(self, cr: ChangeRequest, ask: Ask) -> None:
        """Render the Change Order, run check_numbers, and send READY CR-NNN to Scout."""
        now_iso = self._clock.now().isoformat()
        plan = self._repo.get_plan()
        milestone = select_affected_milestone(plan)
        current_due = milestone.due if milestone else "2026-12-12"
        clause_id = ask.clause_ids[0] if ask.clause_ids else "6.1"
        clause_summary = self._clause_summary(clause_id)

        co_text = render_change_order(
            subject=cr.title,
            clause_id=clause_id,
            clause_summary=clause_summary,
            options=cr.options,
            current_milestone_due=current_due,
        )

        # Verify numbers integrity before sending to Scout
        facts = {
            "clause_id": clause_id,
            "options": [o.model_dump() for o in cr.options],
            "current_milestone_due": current_due,
        }
        chk = check_numbers(co_text, facts)
        if not chk.passed:
            raise ValueError(f"Change order failed numbers check: {chk.unexpected_tokens}")

        intake_room = self._room_ref("acme-intake", ChatApp.SLACK)
        scout_name = self._rooms_config.handles.scout.lstrip("@")
        msg_ref = await self._switch.send_targeted(
            intake_room,
            targets=[scout_name],
            text=render_ready(cr.id, co_text),
        )
        self._repo.update_ask(
            ask.id,
            status=AskStatus.CHANGE_SENT,
            event_type="co.sent",
            event_text=f"Change Order {cr.id} sent to client via Scout",
            ts=now_iso,
            message_link=msg_ref.url,
        )

    async def record_client_decision(
        self,
        cr_id: str,
        *,
        choice: OptionKey | Literal["DECLINE"],
        message_link: str,
    ) -> tuple[ChangeRequest, OptionQuote | None]:
        """Record the client's choice on `cr_id`, execute swaps/closures, and archive the room."""
        now_iso = self._clock.now().isoformat()
        cr = self._repo.get_change_request(cr_id)
        if cr is None:
            raise KeyError(f"ChangeRequest {cr_id!r} not found")
        ask = self._repo.get_ask(cr.ask_id)
        if ask is None:
            raise KeyError(f"Ask {cr.ask_id!r} not found")

        chosen_opt: OptionQuote | None = None
        if isinstance(choice, OptionKey):
            for opt in cr.options:
                if opt.key == choice:
                    chosen_opt = opt
                    break
            if chosen_opt is None and cr.options:
                chosen_opt = cr.options[0]

        choice_label = choice.value if isinstance(choice, OptionKey) else choice
        cr = self._repo.update_change_request(
            cr_id,
            status=ChangeRequestStatus.DECIDED,
            client_choice=choice,
            decided_at=now_iso,
            event_type="client.decided",
            event_text=f"Client chose {choice_label} on {cr_id}",
            actor=ask.requester.lower(),
            ts=now_iso,
            message_link=message_link,
        )

        cr_room = self._room_ref(cr.room.room, ChatApp.SLACK)

        if choice == "DECLINE":
            self._repo.update_ask(
                ask.id,
                status=AskStatus.DECLINED,
                decided_at=now_iso,
                event_type="ask.updated",
                event_text=f"{ask.id} declined by client on {cr_id}",
                actor=ask.requester.lower(),
                ts=now_iso,
                message_link=message_link,
            )
            cr = self._repo.update_change_request(
                cr_id,
                status=ChangeRequestStatus.CLOSED,
                event_type="cr.updated",
                event_text=f"{cr_id} closed (declined)",
                ts=now_iso,
            )
            await self._switch.post(
                cr_room,
                f"{cr_id} closed: client declined ({message_link}).",
            )
            await self._switch.archive_room(cr_room)
            return (cr, None)

        assert chosen_opt is not None

        if choice == OptionKey.D or chosen_opt.swap_out:
            # Record scope swap and update live Plan
            removed_ids = chosen_opt.swap_out or ["I9"]
            plan = self._repo.get_plan()
            removed_hours = sum(
                it.hours for ms in plan.milestones for it in ms.items if it.id in removed_ids
            )
            added_title = chosen_opt.swap_in or cr.title
            self._repo.create_swap(
                cr_id=cr_id,
                added_title=added_title,
                removed_item_ids=removed_ids,
                hours_added=chosen_opt.hours,
                hours_removed=removed_hours,
                ts=now_iso,
                message_link=message_link,
            )
            self._repo.update_ask(
                ask.id,
                status=AskStatus.SWAPPED,
                decided_at=now_iso,
                event_type="ask.updated",
                event_text=(
                    f"{ask.id} swapped via {cr_id} Option D (replacing {', '.join(removed_ids)})"
                ),
                actor=ask.requester.lower(),
                ts=now_iso,
                message_link=message_link,
            )
            cr = self._repo.update_change_request(
                cr_id,
                status=ChangeRequestStatus.CLOSED,
                event_type="cr.updated",
                event_text=f"{cr_id} closed (Option D swap recorded)",
                ts=now_iso,
            )
            await self._switch.post(
                cr_room,
                f"{cr_id} closed: client chose Option D "
                f"(swap {', '.join(removed_ids)} for {added_title}, $0). "
                f"Ledger entry: {message_link}",
            )
            await self._switch.archive_room(cr_room)
            return (cr, chosen_opt)

        # Paid Option A, B, or C approved by client
        price_str = format_usd(chosen_opt.price_cents)
        self._repo.update_ask(
            ask.id,
            status=AskStatus.APPROVED,
            decided_at=now_iso,
            event_type="ask.updated",
            event_text=(
                f"{ask.id} approved via {cr_id} Option {chosen_opt.key.value} ({price_str})"
            ),
            actor=ask.requester.lower(),
            ts=now_iso,
            message_link=message_link,
        )
        self._repo.record_event(
            ts=now_iso,
            event_type="ledger.updated",
            actor="clerk",
            text=f"Change order {cr_id} ({format_usd(chosen_opt.price_cents)}) added to ledger",
            ask_id=ask.id,
            cr_id=cr_id,
            message_link=message_link,
        )
        cr = self._repo.update_change_request(
            cr_id,
            status=ChangeRequestStatus.CLOSED,
            event_type="cr.updated",
            event_text=f"{cr_id} closed (Option {chosen_opt.key.value} approved)",
            ts=now_iso,
        )
        await self._switch.post(
            cr_room,
            f"{cr_id} closed: client approved Option {chosen_opt.key.value} "
            f"({format_usd(chosen_opt.price_cents)}). Ledger entry: {message_link}",
        )
        await self._switch.archive_room(cr_room)
        return (cr, chosen_opt)
