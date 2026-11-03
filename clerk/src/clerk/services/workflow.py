"""WorkflowOrchestrator coordinating all ScopeKeeper services and Switch events."""

from __future__ import annotations

import re

from clerk.adapters.clock import parse_clock_offset
from clerk.db.repositories import LedgerRepository
from clerk.domain.goodwill import can_grant_goodwill
from clerk.domain.models import (
    Ask,
    AskStatus,
    Category,
    ChatApp,
    ClassificationResult,
    WorkItem,
    WorkItemStatus,
)
from clerk.domain.parsing import (
    ApproveCommand,
    ConfirmCommand,
    DeclineCommand,
    DemoControlCommand,
    GoodwillCommand,
    HoursCommand,
    IntakeAcceptMessage,
    IntakeAnswerMessage,
    IntakeAskMessage,
    IntakeDecisionMessage,
    IntakeDisputeMessage,
    IntakeDraftMessage,
    InvoiceCommand,
    LedgerCommand,
    MemoryQueryCommand,
    ParseError,
    PriceOverrideCommand,
    RenewalCommand,
    StatusCommand,
    parse_builder_done,
    parse_clerk_command,
    parse_estimator_reply,
    parse_intake_messages,
)
from clerk.domain.templates import (
    render_preview_ready,
    render_question,
    render_ready,
    render_verdicts,
    render_work_order,
)
from clerk.ports.protocols import (
    ClockPort,
    GitHostPort,
    LLMPort,
    PreviewPort,
    RoomRef,
    SwitchEvent,
    SwitchPort,
)
from clerk.services.brief import BriefService
from clerk.services.change_requests import ChangeRequestService
from clerk.services.classifier import ClassifierService
from clerk.services.flip import FlipService
from clerk.services.invoice import InvoiceService
from clerk.services.memory import MemoryService
from clerk.services.renewal import RenewalService
from clerk.settings import ConfigBundle
from clerk.workers.scheduler import HandoverScheduler


def _slugify(text: str) -> str:
    """Create a concise git branch slug from an ask quote."""
    lower = text.lower()
    if "safari" in lower:
        return "safari-login"
    if "dark mode" in lower or "dark theme" in lower:
        return "dark-mode"
    if "excel" in lower or "xlsx" in lower:
        return "excel-export"
    if "android" in lower:
        return "android-pwa"
    words = re.findall(r"[a-z0-9]+", lower)
    return "-".join(words[:4]) or "work"


def _concise_feature_name(quote: str) -> str:
    """Extract a concise feature name for preview notifications and PR titles."""
    lower = quote.lower()
    if "dark mode" in lower or "dark theme" in lower:
        return "dark mode"
    if "safari" in lower:
        return "Safari login fix"
    if "excel" in lower or "xlsx" in lower:
        return "Excel (.xlsx) export"
    return quote.strip().rstrip(".?!")[:50]


class WorkflowOrchestrator:
    """Top-level workflow coordinator for Clerk."""

    def __init__(
        self,
        *,
        config: ConfigBundle,
        repo: LedgerRepository,
        switch: SwitchPort,
        llm: LLMPort,
        git_host: GitHostPort,
        preview: PreviewPort,
        clock: ClockPort,
    ) -> None:
        self.config = config
        self.repo = repo
        self.switch = switch
        self.llm = llm
        self.git_host = git_host
        self.preview = preview
        self.clock = clock

        self.classifier = ClassifierService(llm=llm, scope_map=config.scope_map)
        self.brief_service = BriefService(
            repo=repo,
            switch=switch,
            clock=clock,
            scope_map=config.scope_map,
        )
        self.flip_service = FlipService(
            repo=repo,
            switch=switch,
            clock=clock,
            schedule=config.schedule,
            rooms_config=config.rooms,
            brief_service=self.brief_service,
        )
        self.cr_service = ChangeRequestService(
            repo=repo,
            switch=switch,
            clock=clock,
            scope_map=config.scope_map,
            rate_card=config.rate_card,
            envelope=config.envelope,
            rooms_config=config.rooms,
        )
        self.memory_service = MemoryService(repo=repo, llm=llm)
        self.renewal_service = RenewalService(repo=repo, llm=llm)
        self.invoice_service = InvoiceService(repo=repo, scope_map=config.scope_map)
        self.scheduler = HandoverScheduler(
            flip_service=self.flip_service,
            clock=clock,
            schedule=config.schedule,
            cr_service=self.cr_service,
        )

    def _room_ref(self, name: str, app: ChatApp = ChatApp.SLACK) -> RoomRef:
        get_ref = getattr(self.switch, "get_room_ref", None)
        if callable(get_ref):
            try:
                ref: RoomRef = get_ref(name)
                return ref
            except KeyError:
                pass
        return RoomRef(id=f"room-{name}", name=name, app=app)

    async def process_pending_switch_events(self) -> int:
        """Drain and process all queued SwitchEvents on an InMemorySwitch."""
        drain_fn = getattr(self.switch, "drain_events_nowait", None)
        if not callable(drain_fn):
            return 0
        count = 0
        while True:
            batch: list[SwitchEvent] = drain_fn()
            if not batch:
                break
            for ev in batch:
                await self.handle_switch_event(ev)
                count += 1
        return count

    async def handle_switch_event(self, event: SwitchEvent) -> None:
        """Process a single inbound SwitchEvent idempotently."""
        sender_norm = event.sender_name.strip().lstrip("@").lower()
        if sender_norm == "clerk":
            return

        if self.repo.is_event_processed(event.id):
            return
        self.repo.mark_event_processed(event.id, event.ts)

        self.repo.record_event(
            ts=event.ts,
            event_type="room.message",
            actor=event.sender_name,
            text=event.text,
            room_id=event.room_name,
            message_link=event.message_link or None,
        )

        text = event.text.strip()
        room_ref = self._room_ref(event.room_name, ChatApp.SLACK)

        # 1. acme-intake protocol messages from Scout
        if event.room_name == "acme-intake":
            await self._handle_intake_event(event, room_ref)
            return

        # 2. Estimator reply in a change room
        if "scopekeeper-estimate" in text or (
            sender_norm in {"acme-estimator", "estimator"} and "cr_id" in text
        ):
            try:
                parsed_est = parse_estimator_reply(text, posted_at=event.ts)
                await self.cr_service.handle_estimate(
                    parsed_est.cr_id,
                    parsed_est.estimate,
                    message_link=event.message_link,
                )
            except ParseError as exc:
                await self.switch.post(
                    room_ref, f"Could not parse estimate:\n{exc.expected_format}"
                )
            return

        # 3. Builder DONE message in acme-delivery or change room
        if re.search(r"\bDONE\s+W-\d+", text, flags=re.IGNORECASE):
            try:
                done_msg = parse_builder_done(text)
                await self.handle_builder_done(done_msg.work_id, done_msg.pr_url)
            except ParseError as exc:
                await self.switch.post(room_ref, exc.expected_format)
            return

        # 4. Internal human @clerk commands
        if re.match(r"^(?:@(?:acme-)?clerk|clerk)\b", text, flags=re.IGNORECASE):
            await self._handle_human_command(event, room_ref)

    async def _handle_intake_event(self, event: SwitchEvent, intake_room: RoomRef) -> None:
        try:
            messages = parse_intake_messages(event.text)
        except ParseError as exc:
            await self.switch.post(intake_room, exc.expected_format)
            return

        ask_msgs = [m for m in messages if isinstance(m, IntakeAskMessage)]
        other_msgs = [m for m in messages if not isinstance(m, IntakeAskMessage)]

        if ask_msgs:
            await self._handle_intake_ask_batch(ask_msgs, intake_room)

        for msg in other_msgs:
            if isinstance(msg, IntakeAnswerMessage):
                await self._handle_intake_answer(msg)
            elif isinstance(msg, IntakeDecisionMessage):
                await self._handle_intake_decision(msg)
            elif isinstance(msg, IntakeAcceptMessage):
                await self._handle_intake_accept(msg)
            elif isinstance(msg, IntakeDisputeMessage):
                await self._handle_intake_dispute(msg)
            elif isinstance(msg, IntakeDraftMessage):
                await self._handle_intake_draft(msg)

    async def _handle_intake_ask_batch(
        self, ask_msgs: list[IntakeAskMessage], intake_room: RoomRef
    ) -> None:
        now_dt = self.clock.now()
        now_iso = now_dt.isoformat()
        created_asks: list[Ask] = []

        for m in ask_msgs:
            ask = self.repo.create_ask(
                quote=m.quote,
                requester=m.requester,
                source_room="acme-client",
                source_link=m.link,
                created_at=now_iso,
            )
            created_asks.append(ask)

        ids_str = ", ".join(a.id for a in created_asks)
        await self.switch.post(intake_room, f"{ids_str} received")

        classified_asks: list[tuple[Ask, ClassificationResult]] = []
        plan = self.repo.get_plan()
        decisions = self.repo.list_decisions()

        for ask in created_asks:
            result, _notes = await self.classifier.classify(
                quote=ask.quote,
                plan=plan,
                decisions=decisions,
                current_date=now_dt.date(),
            )
            updated_ask = self.repo.update_ask(
                ask.id,
                status=AskStatus.CLASSIFIED,
                category=result.category,
                clause_ids=result.clause_ids,
                related_item=result.related_item,
                decision_id=result.decision_id,
                confidence=result.confidence,
                reason=result.reason,
                event_type="ask.classified",
                event_text=(
                    f"{ask.id} classified as {result.category.value} "
                    f"({', '.join(result.clause_ids) or 'no clause'})"
                ),
                ts=now_iso,
            )
            classified_asks.append((updated_ask, result))

        # Post the numbered verdicts list to Scout via READY
        only_asks = [pair[0] for pair in classified_asks]
        verdicts_text = render_verdicts(only_asks)
        scout_name = self.config.rooms.handles.scout.lstrip("@")
        await self.switch.send_targeted(
            intake_room,
            targets=[scout_name],
            text=render_ready(only_asks[0].id, verdicts_text),
        )

        # Trigger per-category downstream workflow actions
        for updated_ask, result in classified_asks:
            await self._dispatch_classified_ask(updated_ask, result)

    async def _dispatch_classified_ask(self, ask: Ask, result: ClassificationResult) -> None:
        now_iso = self.clock.now().isoformat()
        intake_room = self._room_ref("acme-intake", ChatApp.SLACK)
        scout_name = self.config.rooms.handles.scout.lstrip("@")

        if result.category in {Category.DEFECT, Category.IN_SCOPE}:
            await self._create_and_dispatch_work_order(ask)
        elif result.category == Category.UNCLEAR:
            q_text = (
                result.question or "Could you clarify how you would like us to handle this request?"
            )
            choices = result.choices or [
                "Use existing in-scope functionality",
                "Quote as a separate change request",
            ]
            question = self.repo.create_question(
                ask_id=ask.id,
                text=q_text,
                choices=choices,
                asked_at=now_iso,
            )
            self.repo.update_ask(
                ask.id,
                status=AskStatus.QUESTION_PENDING,
                question_id=question.id,
                event_type="ask.updated",
                event_text=f"{ask.id} waiting on {question.id}",
                ts=now_iso,
            )
            q_wire = render_question(question.id, ask.id, question.text, question.choices)
            await self.switch.send_targeted(
                intake_room,
                targets=[scout_name],
                text=q_wire,
            )
        elif result.category == Category.OUT_OF_SCOPE:
            await self.cr_service.open_change_request(ask)
        elif result.category == Category.DUPLICATE:
            self.repo.update_ask(
                ask.id,
                status=AskStatus.LINKED,
                decided_at=now_iso,
                event_type="ask.updated",
                event_text=f"{ask.id} linked to existing item {ask.related_item}",
                ts=now_iso,
            )
        elif result.category == Category.ALREADY_DECIDED:
            self.repo.update_ask(
                ask.id,
                status=AskStatus.REMINDED,
                decided_at=now_iso,
                event_type="ask.updated",
                event_text=f"{ask.id} reminded of decision {ask.decision_id}",
                ts=now_iso,
            )

    async def _create_and_dispatch_work_order(
        self, ask: Ask, cr_id: str | None = None, custom_title: str | None = None
    ) -> WorkItem:
        now_iso = self.clock.now().isoformat()
        feature = custom_title or _concise_feature_name(ask.quote)
        slug = _slugify(feature)
        branch = f"sk/{ask.id.lower()}-{slug}"
        await self.git_host.ensure_branch(branch)

        ticket = await self.git_host.create_ticket(
            ask_id=ask.id,
            title=feature,
            body=(
                f'Client ask ({ask.requester}): "{ask.quote}"\n'
                f"Clauses: {', '.join(ask.clause_ids)}"
            ),
        )
        work = self.repo.create_work_item(
            ask_id=ask.id,
            cr_id=cr_id,
            title=feature,
            ticket_url=ticket.url,
            branch=branch,
            ts=now_iso,
        )

        if ask.status == AskStatus.CLASSIFIED:
            self.repo.update_ask(
                ask.id,
                status=AskStatus.TICKETED,
                event_type="ask.updated",
                event_text=f"{ask.id} ticketed as {work.id}",
                ts=now_iso,
            )

        self.repo.update_ask(
            ask.id,
            status=AskStatus.BUILDING,
            event_type="ask.updated",
            event_text=f"{ask.id} building on {branch}",
            ts=now_iso,
        )
        work = self.repo.update_work_item(
            work.id,
            status=WorkItemStatus.BUILDING,
            event_type="work.updated",
            event_text=f"{work.id} building on {branch}",
            actor="clerk",
            ts=now_iso,
        )

        clause_note = (
            f"{feature}, clause {', '.join(ask.clause_ids)}" if ask.clause_ids else feature
        )
        wo_text = render_work_order(
            work=work,
            ask=ask,
            clause_note=clause_note,
            ticket_ref=ticket.url,
            pr_title=f"[{ask.id}] {feature[0].upper() + feature[1:]}",
            acceptance_criteria=f'Satisfies {ask.id} ("{ask.quote}") with passing tests.',
            builder_handle=self.config.rooms.handles.builder,
        )
        delivery_room = self._room_ref("acme-delivery", ChatApp.SLACK)
        builder_name = self.config.rooms.handles.builder.lstrip("@")
        await self.switch.send_targeted(
            delivery_room,
            targets=[builder_name],
            text=wo_text,
        )
        return work

    async def _handle_intake_answer(self, msg: IntakeAnswerMessage) -> None:
        now_dt = self.clock.now()
        now_iso = now_dt.isoformat()
        question = self.repo.answer_question(
            msg.question_id,
            answer_text=msg.quote,
            answer_link=msg.link,
            answered_at=now_iso,
        )
        ask = self.repo.get_ask(question.ask_id)
        if ask is None:
            return

        plan = self.repo.get_plan()
        decisions = self.repo.list_decisions()
        result, _ = await self.classifier.classify(
            quote=ask.quote,
            plan=plan,
            decisions=decisions,
            current_date=now_dt.date(),
            client_answer=msg.quote,
        )
        updated_ask = self.repo.update_ask(
            ask.id,
            status=AskStatus.CLASSIFIED,
            category=result.category,
            clause_ids=result.clause_ids,
            related_item=result.related_item,
            decision_id=result.decision_id,
            confidence=result.confidence,
            reason=result.reason,
            event_type="ask.classified",
            event_text=(
                f"{ask.id} reclassified after {question.id} answer as {result.category.value}"
            ),
            ts=now_iso,
            message_link=msg.link,
        )
        await self._dispatch_classified_ask(updated_ask, result)

    async def _handle_intake_decision(self, msg: IntakeDecisionMessage) -> None:
        cr, chosen_opt = await self.cr_service.record_client_decision(
            msg.cr_id,
            choice=msg.choice,
            message_link=msg.link,
        )
        if chosen_opt is None:
            return
        ask = self.repo.get_ask(cr.ask_id)
        if ask is None:
            return
        # Option A or C (or D swap-in) triggers a Builder work order
        if msg.choice in {
            chosen_opt.key for chosen_opt in cr.options if chosen_opt.key.value in {"A", "C", "D"}
        }:
            await self._create_and_dispatch_work_order(
                ask,
                cr_id=cr.id,
                custom_title=chosen_opt.swap_in or chosen_opt.label,
            )

    async def _handle_intake_accept(self, msg: IntakeAcceptMessage) -> None:
        now_iso = self.clock.now().isoformat()
        ask = self.repo.get_ask(msg.ask_id)
        if ask is None:
            return
        for wid in ask.work_item_ids:
            self.repo.update_work_item(
                wid,
                status=WorkItemStatus.ACCEPTED,
                event_type="work.updated",
                event_text=f"{wid} accepted by client",
                actor=ask.requester.lower(),
                ts=now_iso,
            )
        new_status = (
            AskStatus.INVOICED
            if ask.cr_id and ask.status == AskStatus.APPROVED
            else AskStatus.ACCEPTED
        )
        self.repo.update_ask(
            ask.id,
            status=new_status,
            decided_at=now_iso,
            event_type="ask.accepted",
            event_text=f"Client accepted {ask.id}",
            actor=ask.requester.lower(),
            ts=now_iso,
            message_link=msg.link,
        )

    async def _handle_intake_dispute(self, msg: IntakeDisputeMessage) -> None:
        delivery_room = self._room_ref("acme-delivery", ChatApp.SLACK)
        await self.switch.post(
            delivery_room,
            f'⚠️ Scope dispute on {msg.ask_id}: "{msg.quote}" ({msg.link}). '
            f"@account-manager please review.",
        )

    async def _handle_intake_draft(self, msg: IntakeDraftMessage) -> None:
        delivery_room = self._room_ref("acme-delivery", ChatApp.SLACK)
        await self.switch.post(
            delivery_room,
            f"📝 Copilot draft from Scout for {msg.ask_id}:\n{msg.text}",
        )

    async def handle_builder_done(self, work_id: str, pr_url: str) -> WorkItem:
        """Process Builder completion (or polled PR), deploy preview, and send READY to Scout."""
        now_iso = self.clock.now().isoformat()
        work = self.repo.get_work_item(work_id)
        if work is None:
            raise KeyError(f"WorkItem {work_id!r} not found")
        ask = self.repo.get_ask(work.ask_id)
        if ask is None:
            raise KeyError(f"Ask {work.ask_id!r} not found")

        self.repo.update_work_item(
            work.id,
            status=WorkItemStatus.PR_OPEN,
            pr_url=pr_url,
            event_type="work.pr_opened",
            event_text=f"PR opened for {work.id}: {pr_url}",
            actor="acme-builder",
            ts=now_iso,
        )

        preview_url = await self.preview.deploy_preview(work.id, work.branch)
        work = self.repo.update_work_item(
            work.id,
            status=WorkItemStatus.PREVIEW,
            pr_url=pr_url,
            preview_url=preview_url,
            event_type="work.preview_ready",
            event_text=f"Preview ready for {work.id}: {preview_url}",
            actor="clerk",
            ts=now_iso,
        )
        self.repo.update_ask(
            ask.id,
            status=AskStatus.PREVIEW,
            event_type="ask.updated",
            event_text=f"{ask.id} preview ready at {preview_url}",
            ts=now_iso,
        )

        client_msg = render_preview_ready(work.title, preview_url)
        intake_room = self._room_ref("acme-intake", ChatApp.SLACK)
        scout_name = self.config.rooms.handles.scout.lstrip("@")
        await self.switch.send_targeted(
            intake_room,
            targets=[scout_name],
            text=render_ready(ask.id, client_msg),
        )
        return work

    async def poll_open_work_items(self) -> list[WorkItem]:
        """Poll GitHostPort for open PRs on building WorkItems so missing DONE never blocks."""
        updated: list[WorkItem] = []
        for w in self.repo.list_work_items():
            if w.status in {WorkItemStatus.QUEUED, WorkItemStatus.BUILDING}:
                pr = await self.git_host.find_pull_request(w.branch)
                if pr is not None:
                    done_w = await self.handle_builder_done(w.id, pr.url)
                    updated.append(done_w)
        return updated

    async def _handle_human_command(self, event: SwitchEvent, room_ref: RoomRef) -> None:
        default_cr_id: str | None = None
        cr_in_room = self.repo.get_change_request_by_room(event.room_name)
        if cr_in_room is not None:
            default_cr_id = cr_in_room.id

        try:
            cmd = parse_clerk_command(
                event.text,
                default_cr_id=default_cr_id,
                default_year=self.clock.now().year,
            )
        except ParseError as exc:
            await self.switch.post(room_ref, exc.expected_format)
            return

        sender = event.sender_name.strip().lstrip("@")

        # 1. @delivery-lead commands: confirm / hours
        if isinstance(cmd, (ConfirmCommand, HoursCommand)):
            if not self.config.rooms.is_authorized(sender, "delivery-lead"):
                holder = self.config.rooms.role_holder_username("delivery-lead")
                await self.switch.post(
                    room_ref,
                    f"Sorry @{sender}, only `@delivery-lead` ({holder or 'unassigned'}) "
                    "can confirm or adjust hours.",
                )
                return
            target_cr = cmd.cr_id or default_cr_id
            if not target_cr:
                await self.switch.post(
                    room_ref, "Please specify a Change Request ID (e.g. `@clerk confirm CR-004`)."
                )
                return
            if isinstance(cmd, ConfirmCommand):
                await self.cr_service.confirm_hours(target_cr, hours=None, confirmed_by=sender)
            else:
                await self.cr_service.confirm_hours(
                    target_cr,
                    hours=cmd.hours,
                    confirmed_by=sender,
                    version=cmd.version,
                )
            return

        # 2. @account-manager commands: approve / price / goodwill / decline
        if isinstance(
            cmd,
            (ApproveCommand, PriceOverrideCommand, GoodwillCommand, DeclineCommand),
        ):
            if not self.config.rooms.is_authorized(sender, "account-manager"):
                holder = self.config.rooms.role_holder_username("account-manager")
                await self.switch.post(
                    room_ref,
                    f"Sorry @{sender}, only `@account-manager` ({holder or 'unassigned'}) "
                    "can approve, price, grant goodwill, or decline.",
                )
                return

            if isinstance(cmd, ApproveCommand):
                target_cr = cmd.cr_id or default_cr_id
                if not target_cr:
                    await self.switch.post(
                        room_ref,
                        "Please specify a Change Request ID (e.g. `@clerk approve CR-004`).",
                    )
                    return
                await self.cr_service.approve_change_request(
                    target_cr,
                    approved_by=sender,
                    approved_options=cmd.options,
                )
            elif isinstance(cmd, PriceOverrideCommand):
                target_cr = cmd.cr_id or default_cr_id
                if not target_cr:
                    await self.switch.post(room_ref, "Please specify a Change Request ID.")
                    return
                await self.cr_service.override_option_price(
                    target_cr, cmd.option, cmd.price_usd, actor=sender
                )
            elif isinstance(cmd, GoodwillCommand):
                await self._grant_goodwill(cmd, sender, room_ref, event.message_link)
            elif isinstance(cmd, DeclineCommand):
                target_cr = cmd.cr_id or default_cr_id
                if not target_cr:
                    await self.switch.post(room_ref, "Please specify a Change Request ID.")
                    return
                await self.cr_service.decline_change_request(
                    target_cr, declined_by=sender, reason=cmd.reason
                )
            return

        # 3. Read-only internal commands
        if isinstance(cmd, LedgerCommand):
            month = cmd.month or self.clock.now().isoformat()[:7]
            await self.switch.post(room_ref, self.invoice_service.render_ledger_for_month(month))
            return

        if isinstance(cmd, InvoiceCommand):
            csv_str = self.invoice_service.render_csv_for_month(cmd.month)
            await self.switch.post(room_ref, f"```csv\n{csv_str}```")
            return

        if isinstance(cmd, RenewalCommand):
            report = await self.renewal_service.generate_report()
            await self.switch.post(room_ref, report)
            return

        if isinstance(cmd, StatusCommand):
            await self._post_status(cmd.target_id, room_ref)
            return

        if isinstance(cmd, MemoryQueryCommand):
            ans = self.memory_service.query(cmd.topic)
            await self.switch.post(room_ref, ans)
            return

        # 4. Demo controls
        if isinstance(cmd, DemoControlCommand):
            if cmd.action == "flip_now":
                holder = await self.switch.role_holder(
                    self._room_ref("acme-client", ChatApp.DISCORD), "client-desk"
                )
                if holder is None:
                    await self.flip_service.flip_to_autopilot()
                else:
                    await self.flip_service.flip_to_copilot(post_brief=True)
            elif cmd.action == "morning_now":
                await self.flip_service.flip_to_copilot(post_brief=True)
            elif cmd.action == "clock" and cmd.offset:
                delta = parse_clock_offset(cmd.offset)
                new_dt = self.clock.advance(delta)
                self.repo.set_setting("clock_iso", new_dt.isoformat())
                await self.scheduler.tick()
                await self.switch.post(
                    room_ref, f"🕒 Simulated clock advanced to `{new_dt.isoformat()}`."
                )

    async def _grant_goodwill(
        self,
        cmd: GoodwillCommand,
        sender: str,
        room_ref: RoomRef,
        message_link: str,
    ) -> None:
        now_iso = self.clock.now().isoformat()
        month = now_iso[:7]
        ask = self.repo.get_ask(cmd.ask_id)
        if ask is None:
            await self.switch.post(room_ref, f"Ask {cmd.ask_id} not found.")
            return

        hours = 2.0
        if ask.cr_id:
            cr = self.repo.get_change_request(ask.cr_id)
            if cr and cr.confirmed_hours:
                hours = float(cr.confirmed_hours)
            elif cr and cr.estimate:
                hours = float(cr.estimate.full.p50_hours)

        used = self.repo.used_goodwill_hours(month)
        if not can_grant_goodwill(hours, used, self.config.scope_map.change_policy):
            await self.switch.post(
                room_ref,
                f"Cannot grant {hours:g}h goodwill for {ask.id}: monthly bucket exceeded.",
            )
            return

        reason = cmd.reason or f"Courtesy goodwill approved by {sender}"
        self.repo.create_goodwill(
            ask_id=ask.id,
            hours=hours,
            reason=reason,
            approved_by=sender,
            month=month,
            date_str=now_iso[:10],
            link=message_link,
            ts=now_iso,
        )
        self.repo.update_ask(
            ask.id,
            status=AskStatus.ACCEPTED,
            decided_at=now_iso,
            event_type="ask.accepted",
            event_text=f"{ask.id} granted as {hours:g}h goodwill by {sender}",
            actor=sender,
            ts=now_iso,
            message_link=message_link,
        )
        await self.switch.post(
            room_ref,
            f"Granted {hours:g}h goodwill for {ask.id} ({reason}).",
        )

    async def _post_status(self, target_id: str | None, room_ref: RoomRef) -> None:
        if target_id and target_id.startswith("CR-"):
            cr = self.repo.get_change_request(target_id)
            if cr is None:
                await self.switch.post(room_ref, f"{target_id} not found.")
                return
            await self.switch.post(
                room_ref,
                f"Status for {cr.id} ({cr.title}): `{cr.status.value}` | "
                f"confirmed_hours={cr.confirmed_hours} | choice={cr.client_choice}",
            )
            return
        if target_id and target_id.startswith("ASK-"):
            ask = self.repo.get_ask(target_id)
            if ask is None:
                await self.switch.post(room_ref, f"{target_id} not found.")
                return
            await self.switch.post(
                room_ref,
                f"Status for {ask.id}: `{ask.status.value}` "
                f"| category={ask.category} | cr={ask.cr_id}",
            )
            return
        asks = self.repo.list_asks()
        crs = self.repo.list_change_requests()
        await self.switch.post(
            room_ref,
            f"ScopeKeeper active: {len(asks)} asks, {len(crs)} change requests, "
            f"clock={self.clock.now().isoformat()}.",
        )
