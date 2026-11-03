"""Golden-path integration test for the ScopeKeeper Overnight Story (Section 2 & 13)."""

from __future__ import annotations

import inspect
from datetime import timedelta
from pathlib import Path

import pytest

from clerk.adapters import (
    FakePreview,
    InMemorySwitch,
    LocalGitHost,
    ScriptedLLM,
    SimulatedClock,
)
from clerk.db.repositories import LedgerRepository
from clerk.db.session import (
    create_db_engine,
    create_session_factory,
    reset_and_seed_db,
)
from clerk.domain.models import (
    AskStatus,
    Category,
    ChangeRequestStatus,
    OptionKey,
    WorkItemStatus,
)
from clerk.services import (
    BuiltinScout,
    WorkflowOrchestrator,
)
from clerk.services import scout_builtin as scout_builtin_module
from clerk.settings import ConfigBundle, load_all_configs


@pytest.fixture
def config_bundle() -> ConfigBundle:
    """Load the repository configuration bundle."""
    repo_root = Path(__file__).resolve().parents[3]
    return load_all_configs(repo_root / "config")


def _build_test_harness(
    config_bundle: ConfigBundle,
    *,
    allow_room_creation: bool = True,
) -> tuple[
    WorkflowOrchestrator,
    LedgerRepository,
    InMemorySwitch,
    SimulatedClock,
    LocalGitHost,
    FakePreview,
]:
    """Create a complete offline test harness backed by SQLite in-memory and fake adapters."""
    clock = SimulatedClock("2026-11-05T19:00:00+05:30")
    engine = create_db_engine("sqlite:///:memory:")
    reset_and_seed_db(engine, config_bundle.seed_ledger, config_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=config_bundle.plan)

    switch = InMemorySwitch(
        rooms_config=config_bundle.rooms,
        clock=clock,
        auto_scout_relay=True,
        allow_room_creation=allow_room_creation,
    )
    llm = ScriptedLLM()
    git_host = LocalGitHost()
    preview = FakePreview()

    orchestrator = WorkflowOrchestrator(
        config=config_bundle,
        repo=repo,
        switch=switch,
        llm=llm,
        git_host=git_host,
        preview=preview,
        clock=clock,
    )
    return orchestrator, repo, switch, clock, git_host, preview


@pytest.mark.asyncio
async def test_overnight_story_golden_path(config_bundle: ConfigBundle) -> None:
    """Verify the entire Section 2 overnight story end-to-end (all 7 requirements in Section 13)."""
    orchestrator, repo, switch, clock, git_host, preview = _build_test_harness(
        config_bundle,
        allow_room_creation=True,
    )
    await switch.connect()

    # =========================================================================
    # 1. 7:00 PM IST handover (MODE autopilot, Scout assumes @client-desk)
    #    and its role_shifts row
    # =========================================================================
    shift = await orchestrator.flip_service.flip_to_autopilot()
    assert shift.role == "client-desk"
    assert shift.from_holder == "priya"
    assert shift.to_holder == "scout"
    assert shift.verified is True

    # Verify MODE autopilot was sent in acme-intake and Scout assumed @client-desk
    intake_msgs = switch.messages_in("acme-intake")
    assert any(
        "MODE autopilot until 09:30 IST (11:00 PM ET)" in m.text and m.sender == "clerk"
        for m in intake_msgs
    )
    holder = await switch.role_holder(
        switch.get_room_ref("acme-client"),
        "client-desk",
    )
    assert holder == "acme-scout"

    shifts = repo.list_role_shifts()
    assert len(shifts) == 1
    assert shifts[0].role == "client-desk"
    assert shifts[0].to_holder == "scout"
    assert shifts[0].verified is True

    # =========================================================================
    # 2. Four asks classified DEFECT (1.1), IN_SCOPE (2.4), UNCLEAR (3.2) and
    #    OUT_OF_SCOPE (1.3)
    # =========================================================================
    clock.advance(timedelta(hours=1, minutes=30))  # 20:30 IST (10:00 AM ET)

    intake_batch = (
        'ASK | "The login button on Safari 17 does nothing when clicked - '
        'console shows a CORS error on `/api/session`." | requester=Sam '
        "| link=https://discord.com/channels/acme/client/1001\n"
        'ASK | "Can we get a dark mode toggle on the settings page? '
        'Pretty sure that was part of the theming work." | requester=Sam '
        "| link=https://discord.com/channels/acme/client/1001\n"
        'ASK | "We also need the monthly usage report exported to Excel." '
        "| requester=Sam | link=https://discord.com/channels/acme/client/1001\n"
        'ASK | "And our CEO asked if we can ship a companion Android app '
        'before the Series B board meeting on Dec 10." | requester=Sam '
        "| link=https://discord.com/channels/acme/client/1001"
    )
    switch.post_as("acme-scout", "acme-intake", intake_batch, is_agent=True)
    await orchestrator.process_pending_switch_events()

    ask_7 = repo.get_ask("ASK-0007")
    ask_8 = repo.get_ask("ASK-0008")
    ask_9 = repo.get_ask("ASK-0009")
    ask_10 = repo.get_ask("ASK-0010")

    assert ask_7 is not None
    assert ask_7.category == Category.DEFECT
    assert ask_7.clause_ids == ["1.1"]
    assert ask_7.status == AskStatus.BUILDING

    assert ask_8 is not None
    assert ask_8.category == Category.IN_SCOPE
    assert ask_8.clause_ids == ["2.4"]
    assert ask_8.status == AskStatus.BUILDING

    assert ask_9 is not None
    assert ask_9.category == Category.UNCLEAR
    assert ask_9.clause_ids == ["3.2"]
    assert ask_9.status == AskStatus.QUESTION_PENDING

    assert ask_10 is not None
    assert ask_10.category == Category.OUT_OF_SCOPE
    assert ask_10.clause_ids == ["1.3"]
    assert ask_10.status == AskStatus.CHANGE_OPEN
    assert ask_10.cr_id == "CR-004"

    # Verify Q-0001 was created and sent to Scout
    q1 = repo.get_question("Q-0001")
    assert q1 is not None
    assert q1.ask_id == "ASK-0009"
    assert any("QUESTION Q-0001 for ASK-0009" in m.text for m in switch.messages_in("acme-intake"))

    # Verify W-0001 and W-0002 were dispatched to @acme-builder in acme-delivery
    w1 = repo.get_work_item("W-0001")
    w2 = repo.get_work_item("W-0002")
    assert w1 is not None and w1.ask_id == "ASK-0007"
    assert w2 is not None and w2.ask_id == "ASK-0008"
    delivery_msgs = switch.messages_in("acme-delivery")
    assert any("W-0001" in m.text and "ASK-0007" in m.text for m in delivery_msgs)
    assert any("W-0002" in m.text and "ASK-0008" in m.text for m in delivery_msgs)

    # Verify CR-004 room acme-cr-004 was created and Estimator was requested
    cr4 = repo.get_change_request("CR-004")
    assert cr4 is not None
    assert cr4.ask_id == "ASK-0010"
    assert cr4.room.room == "acme-cr-004"
    assert any(
        "CR-004" in m.text and "ASK-0010" in m.text for m in switch.messages_in("acme-cr-004")
    )

    # =========================================================================
    # 3. Q-0001 asked; after the answer ("a native .xlsx file"), CR-005 priced at
    #    $140, auto-sent under the envelope, approved, and a work item created
    # =========================================================================
    clock.advance(timedelta(minutes=2))  # 20:32 IST
    switch.post_as(
        "acme-scout",
        "acme-intake",
        'ANSWER Q-0001 | "a native .xlsx file" | link=https://discord.com/channels/acme/client/1002',
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    ask_9_updated = repo.get_ask("ASK-0009")
    assert ask_9_updated is not None
    assert ask_9_updated.category == Category.OUT_OF_SCOPE
    assert ask_9_updated.status == AskStatus.CHANGE_OPEN
    assert ask_9_updated.cr_id == "CR-005"

    cr5 = repo.get_change_request("CR-005")
    assert cr5 is not None
    assert cr5.room.room == "acme-cr-005"

    # Estimator posts 3 h, high confidence estimate in acme-cr-005
    clock.advance(timedelta(minutes=2))  # 20:34 IST
    estimator_cr5_msg = (
        "```scopekeeper-estimate\n"
        "{\n"
        '  "cr_id": "CR-005",\n'
        '  "full": { "p50_hours": 3, "p90_hours": 4, "confidence": "high" },\n'
        '  "smaller": null,\n'
        '  "touches": ["src/reports/monthly.ts"],\n'
        '  "similar": [{ "ref": "c91a20e", "hours": 3 }],\n'
        '  "risks": ["SheetJS bundle size"],\n'
        '  "assumptions": ["Uses existing monthly report query"]\n'
        "}\n"
        "```"
    )
    switch.post_as("acme-estimator", "acme-cr-005", estimator_cr5_msg, is_agent=True)
    await orchestrator.process_pending_switch_events()

    cr5_priced = repo.get_change_request("CR-005")
    assert cr5_priced is not None
    assert cr5_priced.confirmed_hours == 3
    assert cr5_priced.confirmed_by == "auto-envelope"
    assert cr5_priced.approved_by == "auto-envelope"
    assert cr5_priced.status == ChangeRequestStatus.SENT
    assert cr5_priced.envelope is not None and cr5_priced.envelope.passed is True
    assert len(cr5_priced.options) >= 1
    assert cr5_priced.options[0].key == OptionKey.A
    assert cr5_priced.options[0].price_cents == 14000  # $140

    assert any(
        "READY CR-005" in m.text and "$140" in m.text for m in switch.messages_in("acme-intake")
    )

    # Sam approves CR-005 (DECISION CR-005 A)
    clock.advance(timedelta(minutes=4))  # 20:38 IST
    switch.post_as(
        "acme-scout",
        "acme-intake",
        "DECISION CR-005 A | link=https://discord.com/channels/acme/client/1003",
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    cr5_decided = repo.get_change_request("CR-005")
    assert cr5_decided is not None
    assert cr5_decided.status == ChangeRequestStatus.CLOSED
    assert cr5_decided.client_choice == OptionKey.A
    assert switch.is_archived("acme-cr-005") is True

    # Work item W-0003 created for ASK-0009 / CR-005
    w3 = repo.get_work_item("W-0003")
    assert w3 is not None
    assert w3.ask_id == "ASK-0009"
    assert w3.cr_id == "CR-005"

    # Builder finishes W-0001, W-0002, and W-0003
    clock.advance(timedelta(minutes=16))  # 20:54 IST
    for work_id, pr_num in [("W-0001", 48), ("W-0002", 49), ("W-0003", 50)]:
        switch.post_as(
            "acme-builder",
            "acme-delivery",
            f"@clerk DONE {work_id} pr=https://github.com/acme/portal/pull/{pr_num}",
            is_agent=True,
        )
    await orchestrator.process_pending_switch_events()

    assert len(preview.deployed) == 3
    assert any(
        "READY ASK-0008" in m.text and "http://localhost:4300/" in m.text
        for m in switch.messages_in("acme-intake")
    )

    # Sam accepts the dark mode preview (ASK-0008)
    clock.advance(timedelta(minutes=18))  # 21:12 IST
    switch.post_as(
        "acme-scout",
        "acme-intake",
        "ACCEPT ASK-0008 | link=https://discord.com/channels/acme/client/1004",
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    w2_accepted = repo.get_work_item("W-0002")
    assert w2_accepted is not None
    assert w2_accepted.status == WorkItemStatus.ACCEPTED
    ask_8_accepted = repo.get_ask("ASK-0008")
    assert ask_8_accepted is not None
    assert ask_8_accepted.status == AskStatus.ACCEPTED

    # =========================================================================
    # 4. CR-004 estimated, confirmed at 200 h, with options A $10,350, B $10,350,
    #    C $2,650 and D $0 naming I9
    # =========================================================================
    estimator_cr4_msg = (
        "```scopekeeper-estimate\n"
        "{\n"
        '  "cr_id": "CR-004",\n'
        '  "full": { "p50_hours": 190, "p90_hours": 240, "confidence": "medium" },\n'
        '  "smaller": {\n'
        '    "title": "Board-meeting version: installable mobile web app (PWA), '
        'view-only dashboards",\n'
        '    "p50_hours": 56,\n'
        '    "p90_hours": 68,\n'
        '    "confidence": "high"\n'
        "  },\n"
        '  "touches": ["src/auth/session.ts", "src/dashboard/"],\n'
        '  "similar": [{ "ref": "a44f10b", "hours": 52 }],\n'
        '  "risks": ["No mobile code in repo; Play Store review takes 7-14 days"],\n'
        '  "assumptions": ["Read-only mobile KPIs satisfy the Dec 10 board deck"]\n'
        "}\n"
        "```"
    )
    switch.post_as("acme-estimator", "acme-cr-004", estimator_cr4_msg, is_agent=True)
    await orchestrator.process_pending_switch_events()

    cr4_est = repo.get_change_request("CR-004")
    assert cr4_est is not None
    assert cr4_est.status == ChangeRequestStatus.AWAITING_CONFIRMATION
    assert cr4_est.estimate is not None
    assert cr4_est.estimate.full.p50_hours == 190
    assert cr4_est.estimate.full.p90_hours == 240
    assert cr4_est.estimate.smaller is not None
    assert cr4_est.estimate.smaller.p50_hours == 56

    # =========================================================================
    # 5. Morning brief at 9:30 AM IST and desk handover (MODE copilot, Scout
    #    releases @client-desk); approval required and given by Priya; the client
    #    picks D; the swap recorded; I9 removed from M2 and the new item added
    # =========================================================================
    clock.advance(timedelta(hours=12, minutes=18))  # 2026-11-06T09:30:00+05:30
    assert clock.now().isoformat().startswith("2026-11-06T09:30:00")

    morning_shift = await orchestrator.flip_service.flip_to_copilot(post_brief=True)
    assert morning_shift.from_holder == "scout"
    assert morning_shift.to_holder == "priya"
    assert morning_shift.verified is True

    holder_morning = await switch.role_holder(
        switch.get_room_ref("acme-client"),
        "client-desk",
    )
    assert holder_morning is None

    # Verify morning brief was posted in acme-delivery
    delivery_msgs_morning = switch.messages_in("acme-delivery")
    assert any(
        "Morning brief" in m.text and "CR-004" in m.text and "W-0003" in m.text
        for m in delivery_msgs_morning
    )

    # Ravi confirms 200 h in acme-cr-004
    clock.advance(timedelta(minutes=3))  # 09:33 IST
    switch.post_as("ravi", "acme-cr-004", "@clerk hours 200", is_agent=False)
    await orchestrator.process_pending_switch_events()

    cr4_priced = repo.get_change_request("CR-004")
    assert cr4_priced is not None
    assert cr4_priced.confirmed_hours == 200
    assert cr4_priced.confirmed_by == "ravi"
    assert cr4_priced.status == ChangeRequestStatus.AWAITING_APPROVAL
    assert cr4_priced.envelope is not None and cr4_priced.envelope.passed is False

    opts_by_key = {o.key: o for o in cr4_priced.options}
    assert set(opts_by_key.keys()) == {OptionKey.A, OptionKey.B, OptionKey.C, OptionKey.D}
    assert opts_by_key[OptionKey.A].price_cents == 1035000  # $10,350
    assert opts_by_key[OptionKey.A].shift_days == 12
    assert opts_by_key[OptionKey.A].new_due == "2026-12-24"
    assert opts_by_key[OptionKey.B].price_cents == 1035000  # $10,350
    assert opts_by_key[OptionKey.C].price_cents == 265000  # $2,650
    assert opts_by_key[OptionKey.C].shift_days == 3
    assert opts_by_key[OptionKey.D].price_cents == 0  # $0
    assert opts_by_key[OptionKey.D].swap_out == ["I9"]

    # Priya approves sending CR-004 options to client
    clock.advance(timedelta(minutes=2))  # 09:35 IST
    switch.post_as("priya", "acme-cr-004", "@clerk approve", is_agent=False)
    await orchestrator.process_pending_switch_events()

    cr4_sent = repo.get_change_request("CR-004")
    assert cr4_sent is not None
    assert cr4_sent.status == ChangeRequestStatus.SENT
    assert cr4_sent.approved_by == "priya"
    assert any(
        "READY CR-004" in m.text
        and "$10,350" in m.text
        and "$2,650" in m.text
        and "no extra cost" in m.text
        for m in switch.messages_in("acme-intake")
    )

    # Sam picks Option D (DECISION CR-004 D)
    clock.advance(timedelta(minutes=11))  # 09:46 IST
    switch.post_as(
        "acme-scout",
        "acme-intake",
        "DECISION CR-004 D | link=https://discord.com/channels/acme/client/1005",
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    cr4_swapped = repo.get_change_request("CR-004")
    assert cr4_swapped is not None
    assert cr4_swapped.status == ChangeRequestStatus.CLOSED
    assert cr4_swapped.client_choice == OptionKey.D
    assert switch.is_archived("acme-cr-004") is True

    ask_10_swapped = repo.get_ask("ASK-0010")
    assert ask_10_swapped is not None
    # Note: after swap D, a work order W-0004 is dispatched for the swapped-in PWA item,
    # advancing ASK-0010 from SWAPPED -> BUILDING.
    assert ask_10_swapped.status in {AskStatus.SWAPPED, AskStatus.BUILDING}

    # Verify swap recorded and I9 removed from M2 in plan, with new item added
    swaps = repo.list_swaps()
    assert len(swaps) == 1
    assert swaps[0].cr_id == "CR-004"
    assert swaps[0].removed_item_ids == ["I9"]
    assert swaps[0].hours_removed == 58
    assert swaps[0].hours_added == 56

    updated_plan = repo.get_plan()
    m2 = next(m for m in updated_plan.milestones if m.id == "M2")
    m2_item_ids = [item.id for item in m2.items]
    assert "I9" not in m2_item_ids
    assert "I11" in m2_item_ids

    # =========================================================================
    # 6. The ledger shows $2,030 approved this month and one swap.
    # =========================================================================
    overview = repo.compute_overview("2026-11")
    assert overview.revenue_protected_cents == 203000  # $2,030 ($1,890 CR-003 + $140 CR-005)
    assert overview.change_orders.swaps == 1
    assert overview.goodwill.used_hours == 2.0

    ledger_text = orchestrator.invoice_service.render_ledger_for_month("2026-11")
    assert "$2,030" in ledger_text
    assert "CR-003" in ledger_text
    assert "CR-005" in ledger_text
    assert "CR-004" in ledger_text

    # =========================================================================
    # 7. Clerk never posted in acme-client.
    # =========================================================================
    client_messages = switch.messages_in("acme-client")
    assert len(client_messages) > 0
    assert all(m.sender != "clerk" for m in client_messages)


@pytest.mark.asyncio
async def test_clerk_never_posts_or_binds_in_acme_client(config_bundle: ConfigBundle) -> None:
    """Verify architectural guardrail: Clerk is forbidden from posting or binding in acme-client."""
    _orchestrator, _repo, switch, _clock, _git_host, _preview = _build_test_harness(config_bundle)
    client_room = switch.get_room_ref("acme-client")

    with pytest.raises(PermissionError, match="acme-client"):
        await switch.post(client_room, "Hello client!")

    with pytest.raises(PermissionError, match="acme-client"):
        await switch.send_targeted(client_room, targets=["acme-scout"], text="Hello client!")

    with pytest.raises(PermissionError, match="acme-client"):
        await switch.read_context(client_room)


@pytest.mark.asyncio
async def test_role_check_rejects_unauthorized_human_commands(
    config_bundle: ConfigBundle,
) -> None:
    """Verify @clerk commands enforce human role checks from config/rooms.yaml."""
    orchestrator, repo, switch, _clock, _git_host, _preview = _build_test_harness(config_bundle)

    # Trigger CR-004 creation
    switch.post_as(
        "acme-scout",
        "acme-intake",
        (
            'ASK | "And our CEO asked if we can ship a companion Android app '
            'before the Series B board meeting on Dec 10." '
            "| requester=Sam | link=https://discord.com/1"
        ),
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    # Estimator replies
    switch.post_as(
        "acme-estimator",
        "acme-cr-004",
        (
            "```scopekeeper-estimate\n"
            '{"cr_id": "CR-004", "full": {"p50_hours": 190, '
            '"p90_hours": 240, "confidence": "medium"}, "touches": ["mobile/"]}\n'
            "```"
        ),
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    # Priya (account-manager) tries to run `@clerk hours 200` (requires delivery-lead `ravi`)
    switch.post_as("priya", "acme-cr-004", "@clerk hours 200", is_agent=False)
    await orchestrator.process_pending_switch_events()

    assert any("only `@delivery-lead`" in m.text for m in switch.messages_in("acme-cr-004"))
    cr4 = repo.get_change_request("CR-004")
    assert cr4 is not None and cr4.confirmed_hours is None

    # Ravi confirms 200h (allowed)
    switch.post_as("ravi", "acme-cr-004", "@clerk hours 200", is_agent=False)
    await orchestrator.process_pending_switch_events()
    cr4_after_ravi = repo.get_change_request("CR-004")
    assert cr4_after_ravi is not None and cr4_after_ravi.confirmed_hours == 200

    # Ravi tries to run `@clerk approve` (requires account-manager `priya`)
    switch.post_as("ravi", "acme-cr-004", "@clerk approve", is_agent=False)
    await orchestrator.process_pending_switch_events()
    assert any("only `@account-manager`" in m.text for m in switch.messages_in("acme-cr-004"))
    cr4_still_waiting = repo.get_change_request("CR-004")
    assert cr4_still_waiting is not None
    assert cr4_still_waiting.status == ChangeRequestStatus.AWAITING_APPROVAL


@pytest.mark.asyncio
async def test_dynamic_room_creation_fallback_to_precreated_pool(
    config_bundle: ConfigBundle,
) -> None:
    """Verify fallback to pre-created acme-cr-* pool when dynamic room creation is disabled."""
    orchestrator, repo, switch, _clock, _git_host, _preview = _build_test_harness(
        config_bundle,
        allow_room_creation=False,
    )

    switch.post_as(
        "acme-scout",
        "acme-intake",
        (
            'ASK | "And our CEO asked if we can ship a companion Android app '
            'before the Series B board meeting on Dec 10." '
            "| requester=Sam | link=https://discord.com/1"
        ),
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    cr4 = repo.get_change_request("CR-004")
    assert cr4 is not None
    assert cr4.room.room == "acme-cr-004"
    docs = switch.documents_in("acme-cr-004")
    assert "cr-004-brief" in docs


@pytest.mark.asyncio
async def test_commands_ledger_invoice_memory_renewal_goodwill_decline(
    config_bundle: ConfigBundle,
) -> None:
    """Verify @clerk ledger, invoice, memory query, renewal, status, and goodwill."""
    orchestrator, repo, switch, _clock, _git_host, _preview = _build_test_harness(config_bundle)

    # 1. @clerk status
    switch.post_as("priya", "acme-delivery", "@clerk status", is_agent=False)
    # 2. @clerk ledger
    switch.post_as("priya", "acme-delivery", "@clerk ledger", is_agent=False)
    # 3. @clerk invoice november
    switch.post_as("priya", "acme-delivery", "@clerk invoice november", is_agent=False)
    # 4. @clerk what did we agree about SMS?
    switch.post_as(
        "priya",
        "acme-delivery",
        "@clerk what did we agree about SMS?",
        is_agent=False,
    )
    # 5. @clerk renewal
    switch.post_as("priya", "acme-delivery", "@clerk renewal", is_agent=False)
    await orchestrator.process_pending_switch_events()

    delivery_texts = [m.text for m in switch.messages_in("acme-delivery")]
    assert any("ScopeKeeper active:" in t for t in delivery_texts)
    assert any("ScopeKeeper Ledger" in t for t in delivery_texts)
    assert any("```csv" in t and "CR-003" in t for t in delivery_texts)
    assert any("DEC-002" in t for t in delivery_texts)
    assert any("Renewal" in t or "Phase" in t for t in delivery_texts)

    # 6. Create a small ask and grant @clerk goodwill
    switch.post_as(
        "acme-scout",
        "acme-intake",
        (
            'ASK | "We need the monthly usage report exported as a native .xlsx file." '
            "| requester=Sam | link=https://discord.com/2"
        ),
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    switch.post_as(
        "priya",
        "acme-delivery",
        '@clerk goodwill ASK-0007 "Thank-you gesture for early renewal discussions"',
        is_agent=False,
    )
    await orchestrator.process_pending_switch_events()
    assert repo.used_goodwill_hours("2026-11") == 4.0  # 2h seed + 2h default goodwill


@pytest.mark.asyncio
async def test_builtin_scout_isolation_and_split() -> None:
    """Verify BuiltinScout never imports clerk.db or clerk.domain.pricing and splits asks."""
    source = inspect.getsource(scout_builtin_module)
    assert "from clerk.db" not in source and "import clerk.db" not in source
    assert "from clerk.domain.pricing" not in source and "import clerk.domain.pricing" not in source

    scout = BuiltinScout(llm=ScriptedLLM())
    action, greeting = await scout.handle_intake_command_from_clerk(
        "MODE autopilot until 09:30 IST (11:00 PM ET)"
    )
    assert action == "assume_role"
    assert greeting is not None and "Priya" in greeting
    assert scout.mode == "autopilot"

    ack, intake_lines = await scout.handle_client_message(
        sender="Sam",
        text=(
            "1. The login button on Safari 17 does nothing.\n"
            "2. Can we get a dark mode toggle on the settings page?\n"
            "3. We also need the monthly usage report exported to Excel.\n"
            "4. And our CEO asked if we can ship a companion Android app."
        ),
        message_link="https://discord.com/channels/acme/client/1001",
    )
    assert ack is not None and "four things" in ack
    assert len(intake_lines) == 4
    assert all(line.startswith("ASK | ") for line in intake_lines)
