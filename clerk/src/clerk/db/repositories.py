"""Database repository providing transactional state persistence and queries."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from statistics import median
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from clerk.db.tables import (
    AskRow,
    ChangeRequestRow,
    DecisionRow,
    EventRow,
    GoodwillRow,
    ProcessedEventRow,
    QuestionRow,
    RoleShiftRow,
    SettingRow,
    SwapRow,
    WorkItemRow,
)
from clerk.domain.models import (
    Ask,
    AskStatus,
    Category,
    ChangeOrdersOverview,
    ChangeRequest,
    ChangeRequestStatus,
    ChatApp,
    ChatLink,
    DecisionRecord,
    EnvelopeResult,
    Estimate,
    GoodwillOverview,
    LedgerEntry,
    OptionKey,
    OptionQuote,
    Overview,
    Plan,
    PlanItem,
    Question,
    StreamEvent,
    WorkItem,
    WorkItemStatus,
)


class OptimisticLockError(RuntimeError):
    """Raised when an entity's version column has changed concurrently."""


def _infer_chat_app(room_name: str, url: str) -> ChatApp:
    """Infer the bridged chat app from the URL or room name."""
    u = url.lower()
    if "discord" in u or room_name == "acme-client":
        return ChatApp.DISCORD
    if "mattermost" in u or ":8065" in u:
        return ChatApp.MATTERMOST
    if "teams" in u:
        return ChatApp.TEAMS
    return ChatApp.SLACK


def _next_formatted_id(existing_ids: list[str], prefix: str, width: int) -> str:
    """Compute the next sequential ID like 'ASK-0007', 'CR-004', 'Q-0001', 'W-0001'."""
    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", flags=re.IGNORECASE)
    for raw in existing_ids:
        m = pattern.match(raw.strip())
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"{prefix}{max_num + 1:0{width}d}"


class LedgerRepository:
    """Transactional data access layer for Clerk."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        default_plan: Plan,
        on_event: Callable[[StreamEvent], None] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._default_plan = default_plan
        self._on_event = on_event

    def session(self) -> Session:
        """Create a new SQLAlchemy session."""
        return self._session_factory()

    # ── Idempotency & Event Log ───────────────────────────────────────────────

    def is_event_processed(self, switch_event_id: str) -> bool:
        """Return True if `switch_event_id` has already been processed."""
        with self._session_factory() as s:
            return s.get(ProcessedEventRow, switch_event_id) is not None

    def mark_event_processed(self, switch_event_id: str, ts: str) -> None:
        """Record `switch_event_id` as processed."""
        with self._session_factory.begin() as s:
            if s.get(ProcessedEventRow, switch_event_id) is None:
                s.add(
                    ProcessedEventRow(
                        switch_event_id=switch_event_id,
                        processed_at=ts,
                    )
                )

    def _add_event_in_session(
        self,
        s: Session,
        *,
        ts: str,
        event_type: str,
        actor: str,
        text: str,
        ask_id: str | None = None,
        cr_id: str | None = None,
        room_id: str | None = None,
        message_link: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventRow:
        row = EventRow(
            ts=ts,
            type=event_type,
            actor=actor,
            text=text,
            ask_id=ask_id,
            cr_id=cr_id,
            room_id=room_id,
            payload=payload or {},
            message_link=message_link,
        )
        s.add(row)
        s.flush()
        return row

    def _to_stream_event(self, row: EventRow) -> StreamEvent:
        link: ChatLink | None = None
        if row.message_link:
            room_label = row.room_id or "acme-intake"
            link = ChatLink(
                app=_infer_chat_app(room_label, row.message_link),
                room=room_label,
                url=row.message_link,
            )
        return StreamEvent(
            id=f"EVT-{row.id:04d}",
            ts=row.ts,
            type=row.type,
            actor=row.actor,
            text=row.text,
            ask_id=row.ask_id,
            cr_id=row.cr_id,
            room_id=row.room_id,
            link=link,
            data=row.payload or None,
        )

    def record_event(
        self,
        *,
        ts: str,
        event_type: str,
        actor: str,
        text: str,
        ask_id: str | None = None,
        cr_id: str | None = None,
        room_id: str | None = None,
        message_link: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> StreamEvent:
        """Persist a standalone event row and broadcast it if a callback is registered."""
        with self._session_factory.begin() as s:
            row = self._add_event_in_session(
                s,
                ts=ts,
                event_type=event_type,
                actor=actor,
                text=text,
                ask_id=ask_id,
                cr_id=cr_id,
                room_id=room_id,
                message_link=message_link,
                payload=payload,
            )
            ev = self._to_stream_event(row)
        if self._on_event:
            self._on_event(ev)
        return ev

    def list_events(
        self,
        *,
        ask_id: str | None = None,
        cr_id: str | None = None,
        limit: int = 200,
    ) -> list[StreamEvent]:
        """List recorded stream events ordered chronologically."""
        with self._session_factory() as s:
            stmt = select(EventRow).order_by(EventRow.id.asc())
            if ask_id:
                stmt = stmt.where(EventRow.ask_id == ask_id)
            if cr_id:
                stmt = stmt.where(EventRow.cr_id == cr_id)
            stmt = stmt.limit(limit)
            rows = list(s.scalars(stmt).all())
            return [self._to_stream_event(r) for r in rows]

    # ── ID Generators ─────────────────────────────────────────────────────────

    def next_ask_id(self) -> str:
        """Return the next sequential Ask ID (e.g. ASK-0007)."""
        with self._session_factory() as s:
            ids = list(s.scalars(select(AskRow.id)).all())
            return _next_formatted_id(ids, "ASK-", 4)

    def next_question_id(self) -> str:
        """Return the next sequential Question ID (e.g. Q-0001)."""
        with self._session_factory() as s:
            ids = list(s.scalars(select(QuestionRow.id)).all())
            return _next_formatted_id(ids, "Q-", 4)

    def next_cr_id(self) -> str:
        """Return the next sequential ChangeRequest ID (e.g. CR-004)."""
        with self._session_factory() as s:
            ids = list(s.scalars(select(ChangeRequestRow.id)).all())
            return _next_formatted_id(ids, "CR-", 3)

    def next_work_id(self) -> str:
        """Return the next sequential WorkItem ID (e.g. W-0001)."""
        with self._session_factory() as s:
            ids = list(s.scalars(select(WorkItemRow.id)).all())
            return _next_formatted_id(ids, "W-", 4)

    def next_decision_id(self) -> str:
        """Return the next sequential Decision ID (e.g. DEC-003)."""
        with self._session_factory() as s:
            ids = list(s.scalars(select(DecisionRow.id)).all())
            return _next_formatted_id(ids, "DEC-", 3)

    def next_goodwill_id(self) -> str:
        """Return the next sequential Goodwill ID (e.g. GW-0002)."""
        with self._session_factory() as s:
            ids = list(s.scalars(select(GoodwillRow.id)).all())
            return _next_formatted_id(ids, "GW-", 4)

    def next_swap_id(self) -> str:
        """Return the next sequential Swap ID (e.g. SWAP-0001)."""
        with self._session_factory() as s:
            ids = list(s.scalars(select(SwapRow.id)).all())
            return _next_formatted_id(ids, "SWAP-", 4)

    # ── Ask Conversion & Operations ───────────────────────────────────────────

    def _row_to_ask(self, row: AskRow, work_item_ids: list[str]) -> Ask:
        return Ask(
            id=row.id,
            quote=row.quote,
            requester=row.requester,
            created_at=row.created_at,
            status=AskStatus(row.status),
            category=Category(row.category) if row.category else None,
            clause_ids=list(row.clause_ids or []),
            related_item=row.related_item,
            decision_id=row.decision_id,
            confidence=row.confidence,
            reason=row.reason,
            cr_id=row.cr_id,
            question_id=row.question_id,
            work_item_ids=work_item_ids,
            source=ChatLink(
                app=_infer_chat_app(row.source_room, row.source_link),
                room=row.source_room,
                url=row.source_link,
            ),
        )

    def create_ask(
        self,
        *,
        ask_id: str | None = None,
        quote: str,
        requester: str,
        source_room: str = "acme-client",
        source_message_id: str = "",
        source_link: str = "",
        created_at: str,
        actor: str = "scout",
    ) -> Ask:
        """Create a new Ask in `received` state and write an `ask.created` event."""
        new_id = ask_id or self.next_ask_id()
        with self._session_factory.begin() as s:
            row = AskRow(
                id=new_id,
                source_room=source_room,
                source_message_id=source_message_id,
                source_link=source_link,
                requester=requester,
                quote=quote,
                status=AskStatus.RECEIVED.value,
                clause_ids=[],
                created_at=created_at,
                version=1,
            )
            s.add(row)
            ev_row = self._add_event_in_session(
                s,
                ts=created_at,
                event_type="ask.created",
                actor=actor,
                text=f'{new_id} received from {requester}: "{quote}"',
                ask_id=new_id,
                room_id=source_room,
                message_link=source_link or None,
                payload={"quote": quote, "requester": requester},
            )
            ask = self._row_to_ask(row, [])
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return ask

    def get_ask(self, ask_id: str) -> Ask | None:
        """Fetch a single Ask by ID with its linked work_item_ids."""
        with self._session_factory() as s:
            row = s.get(AskRow, ask_id.upper())
            if row is None:
                return None
            w_ids = list(
                s.scalars(
                    select(WorkItemRow.id)
                    .where(WorkItemRow.ask_id == row.id)
                    .order_by(WorkItemRow.id.asc())
                ).all()
            )
            return self._row_to_ask(row, w_ids)

    def list_asks(
        self,
        *,
        category: Category | None = None,
        status: AskStatus | None = None,
    ) -> list[Ask]:
        """Return all asks matching optional filters, ordered by ID."""
        with self._session_factory() as s:
            stmt = select(AskRow).order_by(AskRow.id.asc())
            if category is not None:
                stmt = stmt.where(AskRow.category == category.value)
            if status is not None:
                stmt = stmt.where(AskRow.status == status.value)
            rows = list(s.scalars(stmt).all())
            all_work = list(s.scalars(select(WorkItemRow).order_by(WorkItemRow.id.asc())).all())
            work_by_ask: dict[str, list[str]] = {}
            for w in all_work:
                work_by_ask.setdefault(w.ask_id, []).append(w.id)
            return [self._row_to_ask(r, work_by_ask.get(r.id, [])) for r in rows]

    def update_ask(
        self,
        ask_id: str,
        *,
        status: AskStatus | None = None,
        category: Category | None = None,
        clause_ids: list[str] | None = None,
        related_item: str | None = None,
        decision_id: str | None = None,
        confidence: float | None = None,
        reason: str | None = None,
        cr_id: str | None = None,
        question_id: str | None = None,
        decided_at: str | None = None,
        event_type: str = "ask.updated",
        event_text: str | None = None,
        actor: str = "clerk",
        ts: str,
        message_link: str | None = None,
        expected_version: int | None = None,
    ) -> Ask:
        """Update an Ask atomically with optimistic locking and an audit event."""
        with self._session_factory.begin() as s:
            row = s.get(AskRow, ask_id.upper())
            if row is None:
                raise KeyError(f"Ask {ask_id!r} not found")
            if expected_version is not None and row.version != expected_version:
                raise OptimisticLockError(
                    f"Ask {row.id} version mismatch: expected {expected_version}, got {row.version}"
                )
            if status is not None:
                row.status = status.value
            if category is not None:
                row.category = category.value
            if clause_ids is not None:
                row.clause_ids = list(clause_ids)
            if related_item is not None:
                row.related_item = related_item
            if decision_id is not None:
                row.decision_id = decision_id
            if confidence is not None:
                row.confidence = confidence
            if reason is not None:
                row.reason = reason
            if cr_id is not None:
                row.cr_id = cr_id
            if question_id is not None:
                row.question_id = question_id
            if decided_at is not None:
                row.decided_at = decided_at
            row.version += 1

            w_ids = list(
                s.scalars(
                    select(WorkItemRow.id)
                    .where(WorkItemRow.ask_id == row.id)
                    .order_by(WorkItemRow.id.asc())
                ).all()
            )
            ev_row = self._add_event_in_session(
                s,
                ts=ts,
                event_type=event_type,
                actor=actor,
                text=event_text or f"{row.id} -> {row.status}",
                ask_id=row.id,
                cr_id=row.cr_id,
                room_id=row.source_room,
                message_link=message_link or row.source_link or None,
                payload={
                    "status": row.status,
                    "category": row.category,
                    "clause_ids": row.clause_ids,
                },
            )
            ask = self._row_to_ask(row, w_ids)
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return ask

    # ── Questions ─────────────────────────────────────────────────────────────

    def _row_to_question(self, row: QuestionRow) -> Question:
        return Question(
            id=row.id,
            ask_id=row.ask_id,
            text=row.text,
            choices=list(row.choices or []),
            answer=row.answer_text,
            asked_at=row.asked_at,
            answered_at=row.answered_at,
        )

    def create_question(
        self,
        *,
        question_id: str | None = None,
        ask_id: str,
        text: str,
        choices: list[str],
        asked_at: str,
    ) -> Question:
        """Create a clarifying question for an UNCLEAR ask."""
        q_id = question_id or self.next_question_id()
        with self._session_factory.begin() as s:
            row = QuestionRow(
                id=q_id,
                ask_id=ask_id.upper(),
                text=text,
                choices=list(choices),
                asked_at=asked_at,
            )
            s.add(row)
            ev_row = self._add_event_in_session(
                s,
                ts=asked_at,
                event_type="question.asked",
                actor="clerk",
                text=f"{q_id} asked for {ask_id}: {text}",
                ask_id=ask_id.upper(),
                payload={"question_id": q_id, "text": text, "choices": choices},
            )
            q = self._row_to_question(row)
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return q

    def get_question(self, question_id: str) -> Question | None:
        """Fetch a Question by ID."""
        with self._session_factory() as s:
            row = s.get(QuestionRow, question_id.upper())
            return self._row_to_question(row) if row else None

    def answer_question(
        self,
        question_id: str,
        *,
        answer_text: str,
        answer_link: str,
        answered_at: str,
        actor: str = "sam",
    ) -> Question:
        """Record the client's answer to a clarifying question."""
        with self._session_factory.begin() as s:
            row = s.get(QuestionRow, question_id.upper())
            if row is None:
                raise KeyError(f"Question {question_id!r} not found")
            row.answer_text = answer_text
            row.answer_link = answer_link
            row.answered_at = answered_at
            ev_row = self._add_event_in_session(
                s,
                ts=answered_at,
                event_type="question.answered",
                actor=actor,
                text=f'{row.id} answered for {row.ask_id}: "{answer_text}"',
                ask_id=row.ask_id,
                message_link=answer_link or None,
                payload={"question_id": row.id, "answer": answer_text},
            )
            q = self._row_to_question(row)
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return q

    # ── Change Requests ───────────────────────────────────────────────────────

    def _row_to_cr(self, row: ChangeRequestRow) -> ChangeRequest:
        est = Estimate.model_validate(row.estimate) if row.estimate else None
        opts = [OptionQuote.model_validate(o) for o in (row.options or [])]
        env = EnvelopeResult.model_validate(row.envelope_result) if row.envelope_result else None
        app_opts = (
            [OptionKey(k) for k in row.approved_options]
            if row.approved_options is not None
            else None
        )
        choice: OptionKey | Literal["DECLINE"] | None = None
        if row.client_choice == "DECLINE":
            choice = "DECLINE"
        elif row.client_choice in {"A", "B", "C", "D"}:
            choice = OptionKey(row.client_choice)

        return ChangeRequest(
            id=row.id,
            ask_id=row.ask_id,
            title=row.title,
            room=ChatLink(
                app=_infer_chat_app(row.room_id, row.room_url),
                room=row.room_id,
                url=row.room_url or f"https://slack.com/archives/{row.room_id}",
            ),
            created_at=row.created_at,
            status=ChangeRequestStatus(row.status),
            estimate=est,
            confirmed_hours=row.confirmed_hours,
            confirmed_by=row.confirmed_by,
            options=opts,
            envelope=env,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            approved_options=app_opts,
            client_choice=choice,
            decided_at=row.decided_at,
        )

    def create_change_request(
        self,
        *,
        cr_id: str | None = None,
        ask_id: str,
        title: str,
        room_id: str,
        room_url: str = "",
        created_at: str,
    ) -> ChangeRequest:
        """Create a new ChangeRequest in `estimating` status."""
        new_id = cr_id or self.next_cr_id()
        with self._session_factory.begin() as s:
            row = ChangeRequestRow(
                id=new_id,
                ask_id=ask_id.upper(),
                title=title,
                room_id=room_id,
                room_url=room_url or f"https://slack.com/archives/{room_id}",
                status=ChangeRequestStatus.ESTIMATING.value,
                options=[],
                created_at=created_at,
                version=1,
            )
            s.add(row)
            ev_row = self._add_event_in_session(
                s,
                ts=created_at,
                event_type="cr.created",
                actor="clerk",
                text=f"{new_id} opened in {room_id} for {ask_id}: {title}",
                ask_id=ask_id.upper(),
                cr_id=new_id,
                room_id=room_id,
                payload={"title": title, "room_id": room_id},
            )
            cr = self._row_to_cr(row)
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return cr

    def get_change_request(self, cr_id: str) -> ChangeRequest | None:
        """Fetch a ChangeRequest by ID."""
        with self._session_factory() as s:
            row = s.get(ChangeRequestRow, cr_id.upper())
            return self._row_to_cr(row) if row else None

    def get_change_request_by_room(self, room_id: str) -> ChangeRequest | None:
        """Find a ChangeRequest by its room_id or room name."""
        with self._session_factory() as s:
            row = s.scalar(select(ChangeRequestRow).where(ChangeRequestRow.room_id == room_id))
            return self._row_to_cr(row) if row else None

    def list_change_requests(
        self, *, status: ChangeRequestStatus | None = None
    ) -> list[ChangeRequest]:
        """List all ChangeRequests ordered by ID."""
        with self._session_factory() as s:
            stmt = select(ChangeRequestRow).order_by(ChangeRequestRow.id.asc())
            if status is not None:
                stmt = stmt.where(ChangeRequestRow.status == status.value)
            rows = list(s.scalars(stmt).all())
            return [self._row_to_cr(r) for r in rows]

    def update_change_request(
        self,
        cr_id: str,
        *,
        status: ChangeRequestStatus | None = None,
        estimate: Estimate | None = None,
        confirmed_hours: int | None = None,
        smaller_confirmed_hours: int | None = None,
        confirmed_by: str | None = None,
        options: list[OptionQuote] | None = None,
        envelope: EnvelopeResult | None = None,
        approved_by: str | None = None,
        approved_at: str | None = None,
        approved_options: list[OptionKey] | None = None,
        client_choice: OptionKey | Literal["DECLINE"] | None = None,
        decided_at: str | None = None,
        event_type: str = "cr.updated",
        event_text: str | None = None,
        actor: str = "clerk",
        ts: str,
        message_link: str | None = None,
        expected_version: int | None = None,
    ) -> ChangeRequest:
        """Update a ChangeRequest atomically with optimistic locking and an audit event."""
        with self._session_factory.begin() as s:
            row = s.get(ChangeRequestRow, cr_id.upper())
            if row is None:
                raise KeyError(f"ChangeRequest {cr_id!r} not found")
            if expected_version is not None and row.version != expected_version:
                raise OptimisticLockError(
                    f"ChangeRequest {row.id} version mismatch: "
                    f"expected {expected_version}, got {row.version}"
                )
            if status is not None:
                row.status = status.value
            if estimate is not None:
                row.estimate = estimate.model_dump(mode="json")
            if confirmed_hours is not None:
                row.confirmed_hours = confirmed_hours
            if smaller_confirmed_hours is not None:
                row.smaller_confirmed_hours = smaller_confirmed_hours
            if confirmed_by is not None:
                row.confirmed_by = confirmed_by
            if options is not None:
                row.options = [o.model_dump(mode="json") for o in options]
            if envelope is not None:
                row.envelope_result = envelope.model_dump(mode="json")
            if approved_by is not None:
                row.approved_by = approved_by
            if approved_at is not None:
                row.approved_at = approved_at
            if approved_options is not None:
                row.approved_options = [k.value for k in approved_options]
            if client_choice is not None:
                row.client_choice = (
                    client_choice.value if isinstance(client_choice, OptionKey) else client_choice
                )
            if decided_at is not None:
                row.decided_at = decided_at
            row.version += 1

            ev_row = self._add_event_in_session(
                s,
                ts=ts,
                event_type=event_type,
                actor=actor,
                text=event_text or f"{row.id} -> {row.status}",
                ask_id=row.ask_id,
                cr_id=row.id,
                room_id=row.room_id,
                message_link=message_link or row.room_url or None,
                payload={"status": row.status, "client_choice": row.client_choice},
            )
            cr = self._row_to_cr(row)
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return cr

    def get_smaller_confirmed_hours(self, cr_id: str) -> int | None:
        """Return smaller_confirmed_hours if explicitly set on the ChangeRequest."""
        with self._session_factory() as s:
            row = s.get(ChangeRequestRow, cr_id.upper())
            return row.smaller_confirmed_hours if row else None

    # ── Work Items ────────────────────────────────────────────────────────────

    def _row_to_work_item(self, row: WorkItemRow) -> WorkItem:
        return WorkItem(
            id=row.id,
            ask_id=row.ask_id,
            cr_id=row.cr_id,
            title=row.title,
            branch=row.branch,
            pr_url=row.pr_url,
            preview_url=row.preview_url,
            status=WorkItemStatus(row.status),
        )

    def create_work_item(
        self,
        *,
        work_id: str | None = None,
        ask_id: str,
        cr_id: str | None = None,
        title: str,
        ticket_url: str,
        branch: str,
        ts: str,
    ) -> WorkItem:
        """Create a queued WorkItem and emit a `work.created` event."""
        new_id = work_id or self.next_work_id()
        with self._session_factory.begin() as s:
            row = WorkItemRow(
                id=new_id,
                ask_id=ask_id.upper(),
                cr_id=cr_id.upper() if cr_id else None,
                title=title,
                ticket_url=ticket_url,
                branch=branch,
                status=WorkItemStatus.QUEUED.value,
            )
            s.add(row)
            ev_row = self._add_event_in_session(
                s,
                ts=ts,
                event_type="work.created",
                actor="clerk",
                text=f"Work order {new_id} created for {ask_id} on branch {branch}",
                ask_id=ask_id.upper(),
                cr_id=cr_id.upper() if cr_id else None,
                room_id="acme-delivery",
                payload={"work_id": new_id, "branch": branch, "ticket_url": ticket_url},
            )
            wi = self._row_to_work_item(row)
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return wi

    def get_work_item(self, work_id: str) -> WorkItem | None:
        """Fetch a WorkItem by ID."""
        with self._session_factory() as s:
            row = s.get(WorkItemRow, work_id.upper())
            return self._row_to_work_item(row) if row else None

    def list_work_items(self, *, ask_id: str | None = None) -> list[WorkItem]:
        """List all WorkItems, optionally filtered by `ask_id`."""
        with self._session_factory() as s:
            stmt = select(WorkItemRow).order_by(WorkItemRow.id.asc())
            if ask_id is not None:
                stmt = stmt.where(WorkItemRow.ask_id == ask_id.upper())
            rows = list(s.scalars(stmt).all())
            return [self._row_to_work_item(r) for r in rows]

    def update_work_item(
        self,
        work_id: str,
        *,
        status: WorkItemStatus | None = None,
        pr_url: str | None = None,
        preview_url: str | None = None,
        event_type: str = "work.updated",
        event_text: str | None = None,
        actor: str = "builder",
        ts: str,
    ) -> WorkItem:
        """Update a WorkItem's status, PR URL, or preview URL."""
        with self._session_factory.begin() as s:
            row = s.get(WorkItemRow, work_id.upper())
            if row is None:
                raise KeyError(f"WorkItem {work_id!r} not found")
            if status is not None:
                row.status = status.value
            if pr_url is not None:
                row.pr_url = pr_url
            if preview_url is not None:
                row.preview_url = preview_url
            ev_row = self._add_event_in_session(
                s,
                ts=ts,
                event_type=event_type,
                actor=actor,
                text=event_text or f"{row.id} -> {row.status}",
                ask_id=row.ask_id,
                cr_id=row.cr_id,
                room_id="acme-delivery",
                message_link=pr_url or preview_url,
                payload={
                    "work_id": row.id,
                    "status": row.status,
                    "pr_url": row.pr_url,
                    "preview_url": row.preview_url,
                },
            )
            wi = self._row_to_work_item(row)
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return wi

    # ── Decisions, Goodwill, Swaps, Role Shifts, Plan ─────────────────────────

    def list_decisions(self) -> list[DecisionRecord]:
        """List all recorded scope decisions."""
        with self._session_factory() as s:
            rows = list(s.scalars(select(DecisionRow).order_by(DecisionRow.id.asc())).all())
            return [
                DecisionRecord(
                    id=r.id,
                    date=r.date,
                    text=r.text,
                    link=r.link,
                    source=r.source,
                )
                for r in rows
            ]

    def create_decision(
        self,
        *,
        text: str,
        date_str: str,
        link: str,
        source: Literal["seed", "client", "agency"] = "agency",
    ) -> DecisionRecord:
        """Record a new scope decision."""
        dec_id = self.next_decision_id()
        with self._session_factory.begin() as s:
            row = DecisionRow(
                id=dec_id,
                date=date_str,
                text=text,
                link=link,
                source=source,
            )
            s.add(row)
            return DecisionRecord(
                id=row.id,
                date=row.date,
                text=row.text,
                link=row.link,
                source=source,
            )

    def used_goodwill_hours(self, month: str) -> float:
        """Sum goodwill hours granted in `month` (YYYY-MM)."""
        with self._session_factory() as s:
            rows = list(s.scalars(select(GoodwillRow).where(GoodwillRow.month == month)).all())
            return float(sum(r.hours for r in rows))

    def create_goodwill(
        self,
        *,
        ask_id: str,
        hours: float,
        reason: str,
        approved_by: str,
        month: str,
        date_str: str,
        link: str,
        ts: str,
    ) -> GoodwillRow:
        """Record a goodwill grant and emit a `ledger.updated` event."""
        gw_id = self.next_goodwill_id()
        with self._session_factory.begin() as s:
            row = GoodwillRow(
                id=gw_id,
                ask_id=ask_id.upper(),
                hours=hours,
                reason=reason,
                approved_by=approved_by,
                month=month,
                date=date_str,
                link=link,
            )
            s.add(row)
            ev_row = self._add_event_in_session(
                s,
                ts=ts,
                event_type="ledger.updated",
                actor=approved_by,
                text=f"Goodwill {gw_id} ({hours:g}h) granted for {ask_id} by {approved_by}",
                ask_id=ask_id.upper(),
                room_id="acme-delivery",
                message_link=link or None,
                payload={"goodwill_id": gw_id, "hours": hours, "month": month},
            )
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return row

    def create_swap(
        self,
        *,
        cr_id: str,
        added_title: str,
        removed_item_ids: list[str],
        hours_added: int,
        hours_removed: int,
        ts: str,
        message_link: str | None = None,
    ) -> SwapRow:
        """Record a scope swap in `swaps`, update the live delivery Plan, and emit events."""
        swap_id = self.next_swap_id()
        with self._session_factory.begin() as s:
            row = SwapRow(
                id=swap_id,
                cr_id=cr_id.upper(),
                added_title=added_title,
                removed_item_ids=list(removed_item_ids),
                hours_added=hours_added,
                hours_removed=hours_removed,
                created_at=ts,
            )
            s.add(row)

            # Update persisted plan_json: remove swapped-out items and add the new item
            plan_setting = s.get(SettingRow, "plan_json")
            current_plan = (
                Plan.model_validate_json(plan_setting.value)
                if plan_setting
                else self._default_plan.model_copy(deep=True)
            )
            removed_set = {rid.upper() for rid in removed_item_ids}
            all_item_ids: list[str] = []
            target_deliverable = "D3"
            for ms in current_plan.milestones:
                for it in ms.items:
                    all_item_ids.append(it.id)
                    if it.id.upper() in removed_set:
                        target_deliverable = it.deliverable

            new_item_id = _next_formatted_id(all_item_ids, "I", 1)
            for ms in current_plan.milestones:
                before_len = len(ms.items)
                ms.items = [it for it in ms.items if it.id.upper() not in removed_set]
                if len(ms.items) < before_len:
                    ms.items.append(
                        PlanItem(
                            id=new_item_id,
                            title=added_title,
                            deliverable=target_deliverable,
                            hours=hours_added,
                            status="unstarted",
                            priority=1,
                        )
                    )

            if plan_setting is None:
                s.add(SettingRow(key="plan_json", value=current_plan.model_dump_json()))
            else:
                plan_setting.value = current_plan.model_dump_json()

            ev_plan = self._add_event_in_session(
                s,
                ts=ts,
                event_type="plan.updated",
                actor="clerk",
                text=(
                    f"Plan updated via {cr_id} swap: removed {', '.join(removed_item_ids)} "
                    f"({hours_removed}h) and added {new_item_id}: {added_title} ({hours_added}h)"
                ),
                cr_id=cr_id.upper(),
                message_link=message_link,
                payload={
                    "swap_id": swap_id,
                    "removed_item_ids": removed_item_ids,
                    "added_item_id": new_item_id,
                    "added_title": added_title,
                },
            )
            ev_ledger = self._add_event_in_session(
                s,
                ts=ts,
                event_type="ledger.updated",
                actor="clerk",
                text=(
                    f"Swap {swap_id} recorded for {cr_id} "
                    f"($0, {hours_added}h for {hours_removed}h)"
                ),
                cr_id=cr_id.upper(),
                message_link=message_link,
                payload={"swap_id": swap_id, "cr_id": cr_id.upper()},
            )
            s_plan = self._to_stream_event(ev_plan)
            s_ledger = self._to_stream_event(ev_ledger)
        if self._on_event:
            self._on_event(s_plan)
            self._on_event(s_ledger)
        return row

    def list_swaps(self) -> list[SwapRow]:
        """List all recorded SwapRows."""
        with self._session_factory() as s:
            return list(s.scalars(select(SwapRow).order_by(SwapRow.id.asc())).all())

    def get_plan(self) -> Plan:
        """Return the current project Plan (including any applied scope swaps)."""
        with self._session_factory() as s:
            row = s.get(SettingRow, "plan_json")
            if row is None:
                return self._default_plan.model_copy(deep=True)
            return Plan.model_validate_json(row.value)

    def save_plan(self, plan: Plan) -> None:
        """Persist an updated project Plan."""
        with self._session_factory.begin() as s:
            row = s.get(SettingRow, "plan_json")
            if row is None:
                s.add(SettingRow(key="plan_json", value=plan.model_dump_json()))
            else:
                row.value = plan.model_dump_json()

    def record_role_shift(
        self,
        *,
        role: str,
        from_holder: str,
        to_holder: str,
        at: str,
        verified: bool,
    ) -> RoleShiftRow:
        """Record a @client-desk handover in `role_shifts` and emit `desk.handover`."""
        with self._session_factory.begin() as s:
            row = RoleShiftRow(
                role=role,
                from_holder=from_holder,
                to_holder=to_holder,
                at=at,
                verified=verified,
            )
            s.add(row)
            s.flush()
            ev_row = self._add_event_in_session(
                s,
                ts=at,
                event_type="desk.handover",
                actor="clerk",
                text=f"@{role} handed over from {from_holder} to {to_holder} (verified={verified})",
                room_id="acme-client",
                payload={
                    "role": role,
                    "from_holder": from_holder,
                    "to_holder": to_holder,
                    "verified": verified,
                },
            )
            stream_ev = self._to_stream_event(ev_row)
        if self._on_event:
            self._on_event(stream_ev)
        return row

    def list_role_shifts(self) -> list[RoleShiftRow]:
        """Return all RoleShiftRows in chronological order."""
        with self._session_factory() as s:
            return list(s.scalars(select(RoleShiftRow).order_by(RoleShiftRow.id.asc())).all())

    # ── Ledger & KPI Overview Queries ─────────────────────────────────────────

    def compute_ledger_entries(self, month: str | None = None) -> list[LedgerEntry]:
        """Build audit ledger rows for change orders, swaps, and goodwill."""
        entries: list[LedgerEntry] = []
        with self._session_factory() as s:
            crs = list(
                s.scalars(select(ChangeRequestRow).order_by(ChangeRequestRow.id.asc())).all()
            )
            swaps_by_cr = {
                sw.cr_id: sw for sw in s.scalars(select(SwapRow).order_by(SwapRow.id.asc())).all()
            }
            asks_by_id = {a.id: a for a in s.scalars(select(AskRow)).all()}
            for cr in crs:
                if cr.client_choice in {None, "DECLINE"}:
                    continue
                date_str = (cr.decided_at or cr.created_at)[:10]
                if month and not date_str.startswith(month):
                    continue
                chosen_opt: dict[str, Any] | None = None
                for opt in cr.options or []:
                    if opt.get("key") == cr.client_choice:
                        chosen_opt = opt
                        break
                ask_row = asks_by_id.get(cr.ask_id)
                link_url = ask_row.source_link if ask_row and ask_row.source_link else cr.room_url
                link = (
                    ChatLink(
                        app=_infer_chat_app("acme-client", link_url),
                        room="acme-client" if "discord" in link_url else cr.room_id,
                        url=link_url,
                    )
                    if link_url
                    else None
                )
                if cr.client_choice == "D" or cr.id in swaps_by_cr:
                    sw = swaps_by_cr.get(cr.id)
                    hrs = float(
                        sw.hours_added if sw else (chosen_opt.get("hours", 0) if chosen_opt else 0)
                    )
                    entries.append(
                        LedgerEntry(
                            date=date_str,
                            ref=cr.id,
                            title=sw.added_title if sw else cr.title,
                            hours=hrs,
                            amount_cents=0,
                            approved_by=cr.approved_by or "auto-envelope",
                            link=link,
                            kind="swap",
                        )
                    )
                elif chosen_opt is not None:
                    entries.append(
                        LedgerEntry(
                            date=date_str,
                            ref=cr.id,
                            title=cr.title,
                            hours=float(chosen_opt.get("hours", cr.confirmed_hours or 0)),
                            amount_cents=int(chosen_opt.get("price_cents", 0)),
                            approved_by=cr.approved_by or "auto-envelope",
                            link=link,
                            kind="change_order",
                        )
                    )

            gws = list(s.scalars(select(GoodwillRow).order_by(GoodwillRow.id.asc())).all())
            for gw in gws:
                if month and gw.month != month:
                    continue
                ask_row = asks_by_id.get(gw.ask_id)
                entries.append(
                    LedgerEntry(
                        date=gw.date or f"{gw.month}-03",
                        ref=gw.id,
                        title=ask_row.quote if ask_row else gw.reason,
                        hours=float(gw.hours),
                        amount_cents=0,
                        approved_by=gw.approved_by,
                        link=(
                            ChatLink(
                                app=_infer_chat_app("acme-delivery", gw.link),
                                room="acme-delivery",
                                url=gw.link,
                            )
                            if gw.link
                            else None
                        ),
                        kind="goodwill",
                    )
                )

        entries.sort(key=lambda e: (e.date, e.ref))
        return entries

    def compute_overview(self, month: str, bucket_hours: float = 8.0) -> Overview:
        """Compute the monthly dashboard KPI Overview matching Section 10."""
        entries = self.compute_ledger_entries(month=month)
        revenue_cents = sum(e.amount_cents for e in entries if e.kind == "change_order")
        swaps_count = sum(1 for e in entries if e.kind == "swap")
        goodwill_used = self.used_goodwill_hours(month)

        with self._session_factory() as s:
            all_crs = list(s.scalars(select(ChangeRequestRow)).all())
            month_crs = [c for c in all_crs if (c.decided_at or c.created_at).startswith(month)]
            sent_count = sum(1 for c in month_crs if c.status in {"sent", "decided", "closed"})
            approved_count = sum(1 for c in month_crs if c.client_choice in {"A", "B", "C"})
            pending_count = sum(
                1
                for c in month_crs
                if c.status in {"estimating", "awaiting_confirmation", "awaiting_approval", "sent"}
            )

            all_asks = list(s.scalars(select(AskRow)).all())
            asks_by_cat: dict[Category, int] = {cat: 0 for cat in Category}
            durations: list[float] = []
            for a in all_asks:
                if a.category:
                    try:
                        asks_by_cat[Category(a.category)] += 1
                    except ValueError:
                        pass
                if a.created_at and a.decided_at:
                    try:
                        t1 = datetime.fromisoformat(a.created_at.replace("Z", "+00:00"))
                        t2 = datetime.fromisoformat(a.decided_at.replace("Z", "+00:00"))
                        diff_min = max(0.0, (t2 - t1).total_seconds() / 60.0)
                        durations.append(diff_min)
                    except ValueError:
                        pass

        median_mins = round(median(durations), 1) if durations else 0.0
        return Overview(
            month=month,
            revenue_protected_cents=revenue_cents,
            change_orders=ChangeOrdersOverview(
                sent=sent_count,
                approved=approved_count,
                pending=pending_count,
                swaps=swaps_count,
            ),
            goodwill=GoodwillOverview(
                used_hours=goodwill_used,
                bucket_hours=bucket_hours,
            ),
            median_ask_to_decision_minutes=median_mins,
            asks_by_category=asks_by_cat,
        )

    def get_setting(self, key: str) -> str | None:
        """Read a key from the `settings` table."""
        with self._session_factory() as s:
            row = s.get(SettingRow, key)
            return row.value if row else None

    def set_setting(self, key: str, value: str) -> None:
        """Write a key-value pair to the `settings` table."""
        with self._session_factory.begin() as s:
            row = s.get(SettingRow, key)
            if row is None:
                s.add(SettingRow(key=key, value=value))
            else:
                row.value = value
