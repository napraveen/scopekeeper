"""Unit tests for deterministic templates and camelCase Frontend Data Contract serialization."""

from __future__ import annotations

from clerk.domain.models import (
    Ask,
    AskStatus,
    Category,
    ChangeOrdersOverview,
    ChangeRequest,
    ChangeRequestStatus,
    ChatApp,
    ChatLink,
    Confidence,
    Estimate,
    EstimateVersion,
    GoodwillOverview,
    LedgerEntry,
    Overview,
    Plan,
    RateCardConfig,
    ScopeMapConfig,
    SimilarMerge,
    WorkItem,
    WorkItemStatus,
)
from clerk.domain.numbers_check import check_numbers
from clerk.domain.pricing import build_options
from clerk.domain.templates import (
    render_acknowledgement,
    render_change_order,
    render_change_room_opening,
    render_estimator_request,
    render_handover_greeting,
    render_invoice_csv,
    render_ledger_message,
    render_morning_brief,
    render_preview_ready,
    render_question,
    render_ready,
    render_renewal_report,
    render_verdicts,
    render_work_order,
)


def test_client_facing_templates_match_section_6(
    rate_card: RateCardConfig,
    plan: Plan,
    scope_map: ScopeMapConfig,
) -> None:
    """Verify acknowledgement, verdicts, preview, handover greeting, and change order templates."""
    ack_3 = render_acknowledgement("Sam", 3)
    assert ack_3 == "Got it, Sam. I see three things here; back in a minute with each one."
    ack_1 = render_acknowledgement("Sam", 1)
    assert ack_1 == "Got it, Sam. I see one thing here; back in a minute with it."

    asks = [
        Ask(
            id="ASK-0007",
            quote="The login button doesn't work on Safari",
            requester="Sam",
            created_at="2026-11-05T19:01:00Z",
            status=AskStatus.TICKETED,
            category=Category.DEFECT,
            clause_ids=["1.1"],
            source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/1"),
        ),
        Ask(
            id="ASK-0008",
            quote="Can we get a dark theme?",
            requester="Sam",
            created_at="2026-11-05T19:01:00Z",
            status=AskStatus.TICKETED,
            category=Category.IN_SCOPE,
            clause_ids=["2.4"],
            source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/2"),
        ),
        Ask(
            id="ASK-0009",
            quote="Export the reports to Excel please",
            requester="Sam",
            created_at="2026-11-05T19:01:00Z",
            status=AskStatus.QUESTION_PENDING,
            category=Category.UNCLEAR,
            clause_ids=["3.2"],
            source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/3"),
        ),
        Ask(
            id="ASK-0010",
            quote="We need an Android app for the board",
            requester="Sam",
            created_at="2026-11-05T19:01:00Z",
            status=AskStatus.CHANGE_OPEN,
            category=Category.OUT_OF_SCOPE,
            clause_ids=["1.3"],
            source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/4"),
        ),
        Ask(
            id="ASK-0011",
            quote="Add a filter by region on the reports page",
            requester="Sam",
            created_at="2026-11-05T19:01:00Z",
            status=AskStatus.LINKED,
            category=Category.DUPLICATE,
            clause_ids=["3.2"],
            related_item="I10",
            source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/5"),
        ),
        Ask(
            id="ASK-0012",
            quote="Can you send SMS alerts?",
            requester="Sam",
            created_at="2026-11-05T19:01:00Z",
            status=AskStatus.REMINDED,
            category=Category.ALREADY_DECIDED,
            decision_id="DEC-002",
            source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/6"),
        ),
    ]
    verdicts = render_verdicts(asks)
    assert '1) "The login button doesn\'t work on Safari" — Defect under warranty' in verdicts
    assert "[clause 1.1]" in verdicts
    assert "(I10)" in verdicts
    assert "(DEC-002)" in verdicts

    preview = render_preview_ready("dark theme", "http://localhost:8090/previews/W-0001")
    assert preview == (
        "Dark theme is ready to try: http://localhost:8090/previews/W-0001. "
        "Reply 'accept' if it looks right."
    )

    greeting = render_handover_greeting("Sam", "11 PM", "Priya")
    assert greeting == (
        "Hi Sam, I'm covering the desk until 11 PM your time. Priya is back after that."
    )

    # Multi-option Change Order (CR-004) matching Section 6 verbatim
    estimate = Estimate(
        full=EstimateVersion(
            title="Full native Android app",
            p50_hours=200,
            p90_hours=260,
            confidence=Confidence.MEDIUM,
        ),
        smaller=EstimateVersion(
            title="Installable web app (PWA): home-screen install + offline shell",
            p50_hours=56,
            p90_hours=72,
            confidence=Confidence.HIGH,
        ),
        touches=["web/manifest.json"],
        similar=[SimilarMerge(ref="PR#42", hours=48)],
    )
    options = build_options(
        ask_title="An Android app",
        estimate=estimate,
        confirmed_hours=200,
        plan=plan,
        rate_card=rate_card,
        swap_policy=scope_map.change_policy.swap,
        smaller_due_hint="Friday",
    )
    co_text = render_change_order(
        subject="An Android app",
        clause_id="1.3",
        clause_summary="native mobile apps",
        options=options,
        current_milestone_due="2026-12-12",
    )
    expected_co = (
        "An Android app is outside our current agreement "
        "(clause 1.3, native mobile apps). Your options:\n"
        "A) Full app now: $10,350; the December 12 milestone moves to December 24\n"
        "B) Full app in the next phase: $10,350; no change to current dates\n"
        "C) Installable web app (PWA) by Friday: $2,650; the milestone moves about 3 days\n"
        "D) Installable web app (PWA) instead of the admin analytics dashboard: "
        "no extra cost, no date change\n"
        'Reply with A, B, C, D, or "not now".'
    )
    assert co_text == expected_co

    # Verify change order passes numbers integrity check
    check = check_numbers(
        co_text,
        {
            "clause_id": "1.3",
            "options": [o.model_dump() for o in options],
            "current_milestone_due": "2026-12-12",
        },
    )
    assert check.passed is True

    # Single-option in-envelope Change Order (CR-005)
    est_single = Estimate(
        full=EstimateVersion(p50_hours=3, p90_hours=4, confidence=Confidence.HIGH),
    )
    opts_single = build_options(
        ask_title="Custom welcome banner",
        estimate=est_single,
        confirmed_hours=3,
        plan=plan,
        rate_card=rate_card,
        swap_policy=scope_map.change_policy.swap,
    )
    co_single = render_change_order(
        subject="Custom welcome banner",
        clause_id="1.1",
        clause_summary="login screen enhancement",
        options=opts_single,
    )
    assert "We can add it for $140 with no change to current dates." in co_single
    assert 'Reply with A to approve, or "not now".' in co_single


def test_internal_prompts_and_export_templates(
    rate_card: RateCardConfig,
    plan: Plan,
    scope_map: ScopeMapConfig,
) -> None:
    """Verify internal room prompts, morning brief, ledger, invoice CSV, and renewal report."""
    r_msg = render_ready("ASK-0007", "Got it, Sam.")
    assert r_msg == "READY ASK-0007\nGot it, Sam."

    q_msg = render_question("Q-0001", "ASK-0009", "Which format?", ["CSV", "Excel"])
    assert q_msg == "QUESTION Q-0001 for ASK-0009\nWhich format?\nChoices: 1) CSV 2) Excel"

    est_req = render_estimator_request(
        cr_id="CR-004",
        ask_id="ASK-0010",
        quote="We need an Android app for the board",
        context="Clause 1.3 excludes native apps",
    )
    assert "@acme-estimator estimate CR-004 for ASK-0010" in est_req
    assert "scopekeeper-estimate" in est_req

    ask = Ask(
        id="ASK-0007",
        quote="The login button doesn't work on Safari",
        requester="Sam",
        created_at="2026-11-05T19:01:00Z",
        status=AskStatus.TICKETED,
        category=Category.DEFECT,
        clause_ids=["1.1"],
        source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/1"),
    )
    work = WorkItem(
        id="W-0001",
        ask_id="ASK-0007",
        title="Fix Safari login button click handler",
        branch="fix/w-0001-safari-login",
        status=WorkItemStatus.QUEUED,
        pr_url="https://github.com/acme/portal/pull/12",
        preview_url="http://localhost:8090/previews/W-0001",
    )
    wo_text = render_work_order(
        work=work,
        ask=ask,
        clause_note="DEFECT under 1.1",
        ticket_ref="I1",
        pr_title="fix: Safari login button",
        acceptance_criteria="Login works on Safari 17+",
    )
    assert "@acme-builder WORK W-0001 for ASK-0007" in wo_text
    assert "Reply: @clerk DONE W-0001 pr=<url>" in wo_text

    estimate = Estimate(
        full=EstimateVersion(p50_hours=200, p90_hours=260, confidence=Confidence.MEDIUM),
        smaller=EstimateVersion(
            title="Installable web app (PWA)",
            p50_hours=56,
            p90_hours=72,
            confidence=Confidence.HIGH,
        ),
    )
    options = build_options(
        ask_title="An Android app",
        estimate=estimate,
        confirmed_hours=200,
        plan=plan,
        rate_card=rate_card,
        swap_policy=scope_map.change_policy.swap,
    )
    cr = ChangeRequest(
        id="CR-004",
        ask_id="ASK-0010",
        title="Android app",
        room=ChatLink(app=ChatApp.MATTERMOST, room="acme-cr-004", url="http://localhost:8065"),
        created_at="2026-11-05T19:02:00Z",
        status=ChangeRequestStatus.AWAITING_APPROVAL,
        estimate=estimate,
        options=options,
    )
    cr_open = render_change_room_opening(
        cr=cr,
        ask=ask,
        sow_context="Excluded under 1.3",
    )
    assert "Change Request CR-004 opened" in cr_open

    brief = render_morning_brief(
        came_in=[ask],
        shipped=[work],
        needs_approval=[cr],
        goodwill_remaining_hours=6,
    )
    assert "Morning brief" in brief
    assert "ASK-0007" in brief
    assert "W-0001" in brief
    assert "CR-004" in brief
    assert "@clerk approve A,B,C,D" in brief

    entries = [
        LedgerEntry(
            date="2026-10-30",
            ref="CR-002",
            title="Role-based audit log export",
            hours=40,
            amount_cents=189000,
            approved_by="priya",
            link=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/cr2"),
            kind="change_order",
        ),
        LedgerEntry(
            date="2026-11-02",
            ref="CR-003",
            title="Weekly email scheduling",
            hours=20,
            amount_cents=0,
            approved_by="priya",
            kind="swap",
        ),
    ]
    ledger_msg = render_ledger_message(
        month="2026-11",
        entries=entries,
        revenue_protected_cents=189000,
        swaps_count=1,
        goodwill_used=2.0,
        goodwill_bucket=8.0,
    )
    assert "$1,890" in ledger_msg
    assert "CR-002" in ledger_msg

    csv_text = render_invoice_csv(entries)
    assert "date,change,option,hours,price_usd,approved_by,link" in csv_text
    assert "2026-10-30,CR-002,A,40,1890,priya,https://discord.com/cr2" in csv_text
    assert "2026-11-02,CR-003,D,20,0,priya," in csv_text

    renewal = render_renewal_report(
        [
            {"name": "Mobile & Offline", "member_ids": ["ASK-0010", "CR-004"], "total_hours": 200},
        ]
    )
    assert "Mobile & Offline" in renewal
    assert "200 h" in renewal
    assert "No out-of-scope asks" in render_renewal_report([])


def test_frontend_data_contract_camel_case_serialization() -> None:
    """Verify Frontend Data Contract models serialize to camelCase JSON keys."""
    ask = Ask(
        id="ASK-0007",
        quote="The login button doesn't work on Safari",
        requester="Sam",
        created_at="2026-11-05T19:01:00Z",
        status=AskStatus.TICKETED,
        category=Category.DEFECT,
        clause_ids=["1.1"],
        related_item="I1",
        work_item_ids=["W-0001"],
        source=ChatLink(app=ChatApp.DISCORD, room="acme-client", url="https://discord.com/1"),
    )
    ask_json = ask.model_dump(by_alias=True)
    assert "createdAt" in ask_json
    assert "clauseIds" in ask_json
    assert "relatedItem" in ask_json
    assert "workItemIds" in ask_json

    overview = Overview(
        month="2026-11",
        revenue_protected_cents=284000,
        change_orders=ChangeOrdersOverview(sent=3, approved=2, pending=1, swaps=1),
        goodwill=GoodwillOverview(used_hours=2.0, bucket_hours=8.0),
        median_ask_to_decision_minutes=14.5,
        asks_by_category={Category.DEFECT: 1, Category.OUT_OF_SCOPE: 2},
    )
    ov_json = overview.model_dump(by_alias=True)
    assert ov_json["revenueProtectedCents"] == 284000
    assert ov_json["changeOrders"]["approved"] == 2
    assert ov_json["goodwill"]["usedHours"] == 2.0
    assert ov_json["medianAskToDecisionMinutes"] == 14.5
    assert "asksByCategory" in ov_json
