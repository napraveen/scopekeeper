"""FlipService managing the 7:00 PM IST and 9:30 AM IST @client-desk shift handovers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from clerk.db.repositories import LedgerRepository
from clerk.db.tables import RoleShiftRow
from clerk.domain.dates import format_handover_window
from clerk.domain.models import ChatApp, RoomsConfig, ScheduleConfig
from clerk.ports.protocols import ClockPort, RoomRef, SwitchPort
from clerk.services.brief import BriefService


class FlipService:
    """Service orchestrating the evening and morning @client-desk handovers."""

    def __init__(
        self,
        repo: LedgerRepository,
        switch: SwitchPort,
        clock: ClockPort,
        schedule: ScheduleConfig,
        rooms_config: RoomsConfig,
        brief_service: BriefService,
        builtin_scout_fallback: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._repo = repo
        self._switch = switch
        self._clock = clock
        self._schedule = schedule
        self._rooms_config = rooms_config
        self._brief_service = brief_service
        self._builtin_scout_fallback = builtin_scout_fallback

    def _room_ref(self, name: str, app: ChatApp = ChatApp.SLACK) -> RoomRef:
        get_ref = getattr(self._switch, "get_room_ref", None)
        if callable(get_ref):
            ref: RoomRef = get_ref(name)
            return ref
        return RoomRef(id=f"room-{name}", name=name, app=app)

    async def flip_to_autopilot(self) -> RoleShiftRow:
        """Execute the 7:00 PM IST handover from Priya (human copilot) to Scout (autopilot)."""
        now_dt = self._clock.now()
        now_iso = now_dt.isoformat()
        window_str = format_handover_window(now_dt, self._schedule)
        intake_room = self._room_ref("acme-intake", ChatApp.SLACK)
        client_room = self._room_ref("acme-client", ChatApp.DISCORD)
        delivery_room = self._room_ref("acme-delivery", ChatApp.SLACK)
        scout_name = self._rooms_config.handles.scout.lstrip("@")

        cmd_text = f"MODE autopilot until {window_str}"
        await self._switch.send_targeted(
            intake_room,
            targets=[scout_name],
            text=cmd_text,
        )

        holder = await self._switch.role_holder(client_room, "client-desk")
        if holder not in {scout_name, "scout", "acme-scout"}:
            # Retry once per Section 7
            await self._switch.send_targeted(
                intake_room,
                targets=[scout_name],
                text=cmd_text,
            )
            if self._builtin_scout_fallback is not None:
                await self._builtin_scout_fallback("autopilot")
            holder = await self._switch.role_holder(client_room, "client-desk")
            if holder not in {scout_name, "scout", "acme-scout"}:
                await self._switch.post(
                    delivery_room,
                    (
                        "⚠️ Warning: `@acme-scout` did not assume "
                        "`@client-desk` in `acme-client` after retry."
                    ),
                )

        verified = holder in {scout_name, "scout", "acme-scout"}
        return self._repo.record_role_shift(
            role="client-desk",
            from_holder=self._schedule.flip.person,
            to_holder=self._schedule.flip.agent,
            at=now_iso,
            verified=verified,
        )

    async def flip_to_copilot(self, post_brief: bool = True) -> RoleShiftRow:
        """Execute the 9:30 AM IST handover from Scout (autopilot) back to Priya (copilot)."""
        now_dt = self._clock.now()
        now_iso = now_dt.isoformat()
        intake_room = self._room_ref("acme-intake", ChatApp.SLACK)
        client_room = self._room_ref("acme-client", ChatApp.DISCORD)
        delivery_room = self._room_ref("acme-delivery", ChatApp.SLACK)
        scout_name = self._rooms_config.handles.scout.lstrip("@")

        if post_brief:
            await self._brief_service.post_morning_brief()

        await self._switch.send_targeted(
            intake_room,
            targets=[scout_name],
            text="MODE copilot",
        )

        holder = await self._switch.role_holder(client_room, "client-desk")
        if holder is not None:
            if self._builtin_scout_fallback is not None:
                await self._builtin_scout_fallback("copilot")
            holder = await self._switch.role_holder(client_room, "client-desk")
            if holder is not None:
                await self._switch.post(
                    delivery_room,
                    f"⚠️ Warning: `@client-desk` is still held by `{holder}` after `MODE copilot`.",
                )

        verified = holder is None
        return self._repo.record_role_shift(
            role="client-desk",
            from_holder=self._schedule.flip.agent,
            to_holder=self._schedule.flip.person,
            at=now_iso,
            verified=verified,
        )
