"""BriefService for generating and posting the 9:30 AM IST morning brief."""

from __future__ import annotations

from clerk.db.repositories import LedgerRepository
from clerk.domain.goodwill import remaining_goodwill_hours
from clerk.domain.models import (
    ChangeRequestStatus,
    ChatApp,
    ScopeMapConfig,
    WorkItemStatus,
)
from clerk.domain.templates import render_ledger_message, render_morning_brief
from clerk.ports.protocols import ClockPort, RoomDocumentSpec, RoomRef, SwitchPort


class BriefService:
    """Service that composes and posts the morning brief and updates ledger-summary."""

    def __init__(
        self,
        repo: LedgerRepository,
        switch: SwitchPort,
        clock: ClockPort,
        scope_map: ScopeMapConfig,
    ) -> None:
        self._repo = repo
        self._switch = switch
        self._clock = clock
        self._scope_map = scope_map

    async def post_morning_brief(self, since_iso: str | None = None) -> str:
        """Post the morning brief to acme-delivery and update the ledger-summary document."""
        now_dt = self._clock.now()
        now_iso = now_dt.isoformat()
        month = now_iso[:7]

        all_asks = self._repo.list_asks()
        # Asks created after ASK-0006 (or >= since_iso) count as overnight activity
        came_in = [
            a
            for a in all_asks
            if (since_iso and a.created_at >= since_iso)
            or (not since_iso and int(a.id.split("-")[1]) >= 7)
        ]

        all_work = self._repo.list_work_items()
        shipped = [
            w
            for w in all_work
            if w.status
            in {
                WorkItemStatus.PR_OPEN,
                WorkItemStatus.PREVIEW,
                WorkItemStatus.MERGED,
                WorkItemStatus.ACCEPTED,
            }
        ]

        all_crs = self._repo.list_change_requests()
        needs_approval = [
            cr
            for cr in all_crs
            if cr.status
            in {
                ChangeRequestStatus.AWAITING_CONFIRMATION,
                ChangeRequestStatus.AWAITING_APPROVAL,
            }
        ]

        used_gw = self._repo.used_goodwill_hours(month)
        rem_gw = remaining_goodwill_hours(used_gw, self._scope_map.change_policy)

        brief_text = render_morning_brief(
            came_in=came_in,
            shipped=shipped,
            needs_approval=needs_approval,
            goodwill_remaining_hours=rem_gw,
        )

        delivery_room = self._resolve_delivery_room()
        msg_ref = await self._switch.post(delivery_room, brief_text)

        # Update ledger-summary room document in acme-delivery
        entries = self._repo.compute_ledger_entries(month=month)
        overview = self._repo.compute_overview(
            month=month,
            bucket_hours=float(self._scope_map.change_policy.goodwill_hours_per_month),
        )
        ledger_doc_text = render_ledger_message(
            month=month,
            entries=entries,
            revenue_protected_cents=overview.revenue_protected_cents,
            swaps_count=overview.change_orders.swaps,
            goodwill_used=overview.goodwill.used_hours,
            goodwill_bucket=overview.goodwill.bucket_hours,
        )
        await self._switch.upsert_document(
            delivery_room,
            RoomDocumentSpec(
                name="ledger-summary",
                description=f"Live ScopeKeeper ledger summary for {month}",
                instructions="Read-only audit ledger updated by Clerk.",
                content=ledger_doc_text,
            ),
        )

        self._repo.record_event(
            ts=now_iso,
            event_type="brief.posted",
            actor="clerk",
            text=f"Morning brief posted in acme-delivery ({len(came_in)} overnight asks)",
            room_id=delivery_room.name,
            message_link=msg_ref.url,
            payload={
                "came_in_count": len(came_in),
                "shipped_count": len(shipped),
                "needs_approval_count": len(needs_approval),
            },
        )
        return brief_text

    def _resolve_delivery_room(self) -> RoomRef:
        get_ref = getattr(self._switch, "get_room_ref", None)
        if callable(get_ref):
            ref: RoomRef = get_ref("acme-delivery")
            return ref
        return RoomRef(id="room-acme-delivery", name="acme-delivery", app=ChatApp.SLACK)
