"""Integration tests for Phase 5: APScheduler handovers, brief, memory, and timeouts."""

from __future__ import annotations

from datetime import timedelta

import pytest

from clerk.adapters.clock import SimulatedClock
from clerk.adapters.llm_scripted import ScriptedLLM
from clerk.adapters.local_git import LocalGitHost
from clerk.adapters.preview_local import FakePreview
from clerk.adapters.switch_inmemory import InMemorySwitch
from clerk.db.repositories import LedgerRepository
from clerk.db.session import create_db_engine, create_session_factory, reset_and_seed_db
from clerk.domain.models import ChangeRequestStatus
from clerk.services.flip import FlipService
from clerk.services.scout_builtin import BuiltinScout
from clerk.services.workflow import WorkflowOrchestrator
from clerk.settings import ConfigBundle
from clerk.workers.timeouts import EstimatorTimeoutWorker


@pytest.mark.asyncio
async def test_apscheduler_registration_and_simulated_clock_1900_and_0930_handovers(
    config_bundle: ConfigBundle,
) -> None:
    """Verify APScheduler jobs at 19:00/09:30 IST and SimulatedClock crosses trigger handovers."""
    clock = SimulatedClock("2026-11-05T18:55:00+05:30")
    engine = create_db_engine("sqlite:///:memory:")
    reset_and_seed_db(engine, config_bundle.seed_ledger, config_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=config_bundle.plan)

    switch = InMemorySwitch(
        rooms_config=config_bundle.rooms,
        clock=clock,
        auto_scout_relay=True,
    )
    await switch.connect()

    orchestrator = WorkflowOrchestrator(
        config=config_bundle,
        repo=repo,
        switch=switch,
        llm=ScriptedLLM(),
        git_host=LocalGitHost(),
        preview=FakePreview(),
        clock=clock,
    )

    # 1. Start APScheduler and verify both CronTriggers (19:00 and 09:30 IST) are registered
    orchestrator.scheduler.start()
    assert orchestrator.scheduler.is_running is True
    assert orchestrator.scheduler.apscheduler is not None
    job_ids = {job.id for job in orchestrator.scheduler.apscheduler.get_jobs()}
    assert job_ids == {"flip_to_autopilot", "flip_to_copilot"}
    orchestrator.scheduler.stop()
    assert orchestrator.scheduler.is_running is False

    # 2. Advance clock from 18:55 IST -> 19:00 IST and tick scheduler
    clock.advance(timedelta(minutes=5))
    shifts = await orchestrator.scheduler.tick()
    assert len(shifts) == 1
    assert shifts[0].from_holder == "priya"
    assert shifts[0].to_holder == "scout"
    assert shifts[0].verified is True

    client_room = switch.get_room_ref("acme-client")
    assert await switch.role_holder(client_room, "client-desk") == "acme-scout"
    client_msgs = switch.messages_in("acme-client")
    assert any(
        "covering the desk until 11 PM your time" in m.text for m in client_msgs
    )

    # 3. Advance clock across 09:30 IST the next morning via @clerk clock +14h30m in acme-delivery
    switch.post_as("priya", "acme-delivery", "@clerk clock +14h30m")
    await orchestrator.process_pending_switch_events()

    assert await switch.role_holder(client_room, "client-desk") is None
    all_shifts = repo.list_role_shifts()
    assert len(all_shifts) == 2
    assert all_shifts[1].from_holder == "scout"
    assert all_shifts[1].to_holder == "priya"
    assert all_shifts[1].verified is True

    delivery_msgs = [m.text for m in switch.messages_in("acme-delivery")]
    assert any("morning brief" in text.lower() for text in delivery_msgs)
    delivery_docs = switch.documents_in("acme-delivery")
    assert "ledger-summary" in delivery_docs


@pytest.mark.asyncio
async def test_flip_retry_builtin_scout_fallback_and_unverified_warning(
    config_bundle: ConfigBundle,
) -> None:
    """Verify FlipService retries, triggers BuiltinScout fallback, or warns if unverified."""
    clock = SimulatedClock("2026-11-05T19:00:00+05:30")
    engine = create_db_engine("sqlite:///:memory:")
    reset_and_seed_db(engine, config_bundle.seed_ledger, config_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=config_bundle.plan)

    # Case A: Console Scout is offline (auto_scout_relay=False) and no builtin fallback -> warns
    switch_offline = InMemorySwitch(
        rooms_config=config_bundle.rooms,
        clock=clock,
        auto_scout_relay=False,
    )
    await switch_offline.connect()
    orchestrator_warn = WorkflowOrchestrator(
        config=config_bundle,
        repo=repo,
        switch=switch_offline,
        llm=ScriptedLLM(),
        git_host=LocalGitHost(),
        preview=FakePreview(),
        clock=clock,
    )
    shift_unverified = await orchestrator_warn.flip_service.flip_to_autopilot()
    assert shift_unverified.verified is False
    delivery_msgs = [m.text for m in switch_offline.messages_in("acme-delivery")]
    assert any("Warning" in t and "did not assume" in t for t in delivery_msgs)

    # Case B: BuiltinScout fallback wired -> assumes @client-desk on retry
    builtin_scout = BuiltinScout(llm=ScriptedLLM(), agent_name="acme-scout")

    async def fallback_cb(mode: str) -> None:
        if mode == "autopilot":
            action, greeting = await builtin_scout.handle_intake_command_from_clerk(
                "MODE autopilot until 09:30 IST (11:00 PM ET)"
            )
            if action == "assume_role":
                switch_offline.assume_role_as("acme-scout", "acme-client", "client-desk")
                if greeting:
                    switch_offline.post_as(
                        "acme-scout", "acme-client", greeting, is_agent=True
                    )
        else:
            action, _ = await builtin_scout.handle_intake_command_from_clerk("MODE copilot")
            if action == "release_role":
                switch_offline.release_role_as("acme-scout", "acme-client", "client-desk")

    flip_with_builtin = FlipService(
        repo=repo,
        switch=switch_offline,
        clock=clock,
        schedule=config_bundle.schedule,
        rooms_config=config_bundle.rooms,
        brief_service=orchestrator_warn.brief_service,
        builtin_scout_fallback=fallback_cb,
    )
    shift_ok = await flip_with_builtin.flip_to_autopilot()
    assert shift_ok.verified is True
    client_room = switch_offline.get_room_ref("acme-client")
    assert await switch_offline.role_holder(client_room, "client-desk") == "acme-scout"

    shift_morning = await flip_with_builtin.flip_to_copilot(post_brief=False)
    assert shift_morning.verified is True
    assert await switch_offline.role_holder(client_room, "client-desk") is None


@pytest.mark.asyncio
async def test_estimator_10m_reminder_and_30m_heuristic_fallback(
    config_bundle: ConfigBundle,
) -> None:
    """Verify EstimatorTimeoutWorker reminds at 10m and applies heuristic fallback at 30m."""
    clock = SimulatedClock("2026-11-05T19:05:00+05:30")
    engine = create_db_engine("sqlite:///:memory:")
    reset_and_seed_db(engine, config_bundle.seed_ledger, config_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=config_bundle.plan)
    switch = InMemorySwitch(rooms_config=config_bundle.rooms, clock=clock)
    await switch.connect()

    orchestrator = WorkflowOrchestrator(
        config=config_bundle,
        repo=repo,
        switch=switch,
        llm=ScriptedLLM(),
        git_host=LocalGitHost(),
        preview=FakePreview(),
        clock=clock,
    )
    timeout_worker = EstimatorTimeoutWorker(cr_service=orchestrator.cr_service)

    # Inject an out-of-scope ask in acme-intake to open CR-004 in ESTIMATING state
    switch.post_as(
        "acme-scout",
        "acme-intake",
        'ASK | "We need an Android app for the board meeting on the 20th" '
        "| requester=Sam | link=https://discord.com/channels/acme/1",
        is_agent=True,
    )
    await orchestrator.process_pending_switch_events()

    cr = repo.get_change_request("CR-004")
    assert cr is not None
    assert cr.status == ChangeRequestStatus.ESTIMATING

    # 1. At +11 minutes -> sends targeted reminder to @acme-estimator
    clock.advance(timedelta(minutes=11))
    actions_10m = await timeout_worker.run_once()
    assert actions_10m == ["reminded:CR-004"]
    cr_msgs = [m.text for m in switch.messages_in("acme-cr-004")]
    assert any("Reminder: please post" in t for t in cr_msgs)

    # 2. At +31 minutes total -> applies heuristic fallback estimate (low confidence, 40h/60h)
    clock.advance(timedelta(minutes=20))
    actions_30m = await timeout_worker.run_once()
    assert actions_30m == ["fallback:CR-004"]

    cr_after = repo.get_change_request("CR-004")
    assert cr_after is not None
    assert cr_after.status == ChangeRequestStatus.AWAITING_CONFIRMATION
    assert cr_after.estimate is not None
    assert cr_after.estimate.full.p50_hours == 40
    assert cr_after.estimate.full.confidence.value == "low"


@pytest.mark.asyncio
async def test_memory_queries_and_no_evidence_response(
    config_bundle: ConfigBundle,
) -> None:
    """Verify '@clerk what did we agree about <topic>?' cites links or states no record."""
    clock = SimulatedClock("2026-11-05T19:00:00+05:30")
    engine = create_db_engine("sqlite:///:memory:")
    reset_and_seed_db(engine, config_bundle.seed_ledger, config_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=config_bundle.plan)
    switch = InMemorySwitch(rooms_config=config_bundle.rooms, clock=clock)
    await switch.connect()

    orchestrator = WorkflowOrchestrator(
        config=config_bundle,
        repo=repo,
        switch=switch,
        llm=ScriptedLLM(),
        git_host=LocalGitHost(),
        preview=FakePreview(),
        clock=clock,
    )

    # 1. Query about SMS -> cites DEC-002 with link
    switch.post_as("priya", "acme-delivery", "@clerk what did we agree about SMS?")
    await orchestrator.process_pending_switch_events()
    reply_sms = switch.messages_in("acme-delivery")[-1].text
    assert "DEC-002" in reply_sms
    assert "https://discord.com/channels/acme/acme-client/msg-dec-002" in reply_sms

    # 2. Query about SSO -> cites DEC-001 with link
    switch.post_as("ravi", "acme-delivery", "@clerk what did we agree about SSO?")
    await orchestrator.process_pending_switch_events()
    reply_sso = switch.messages_in("acme-delivery")[-1].text
    assert "DEC-001" in reply_sso
    assert "https://discord.com/channels/acme/acme-client/msg-dec-001" in reply_sso

    # 3. Query about unrecorded topic -> states no evidence
    switch.post_as(
        "aisha", "acme-delivery", "@clerk what did we agree about cryptocurrency?"
    )
    await orchestrator.process_pending_switch_events()
    reply_none = switch.messages_in("acme-delivery")[-1].text
    assert "No recorded decision, ask, or change request found" in reply_none
