"""Unit tests for all inter-agent, client, and human message parsers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from clerk.domain.models import Confidence, OptionKey
from clerk.domain.parsing import (
    ApproveCommand,
    BuilderDoneMessage,
    ClerkModeMessage,
    ClerkQuestionMessage,
    ClerkReadyMessage,
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
    parse_clerk_to_scout_message,
    parse_estimator_reply,
    parse_intake_message,
    parse_intake_messages,
)


def test_parse_intake_messages_clean_and_messy() -> None:
    """Verify ASK, ANSWER, DECISION, ACCEPT, DISPUTE, and DRAFT in acme-intake."""
    ask = parse_intake_message(
        '@clerk ASK | "The login button doesn\'t work on Safari" | requester=Sam | link=https://discord.com/1'
    )
    assert isinstance(ask, IntakeAskMessage)
    assert ask.quote == "The login button doesn't work on Safari"
    assert ask.requester == "Sam"
    assert ask.link == "https://discord.com/1"

    ans = parse_intake_message('`ANSWER Q-0001 | "Option 2 please" | link=https://discord.com/2`')
    assert isinstance(ans, IntakeAnswerMessage)
    assert ans.question_id == "Q-0001"
    assert ans.quote == "Option 2 please"
    assert ans.link == "https://discord.com/2"

    # Pipe-separated ANSWER variant
    ans2 = parse_intake_message('ANSWER | Q-0002 | "Excel" | link=https://discord.com/2b')
    assert isinstance(ans2, IntakeAnswerMessage)
    assert ans2.question_id == "Q-0002"

    dec = parse_intake_message("DECISION CR-004 D | link=<https://discord.com/3>")
    assert isinstance(dec, IntakeDecisionMessage)
    assert dec.cr_id == "CR-004"
    assert dec.choice == OptionKey.D
    assert dec.link == "https://discord.com/3"

    dec_decline = parse_intake_message(
        'DECISION | CR-004 | "not now" | link=https://discord.com/3b'
    )
    assert isinstance(dec_decline, IntakeDecisionMessage)
    assert dec_decline.choice == "DECLINE"

    acc = parse_intake_message("ACCEPT ASK-0008 | link=https://discord.com/4")
    assert isinstance(acc, IntakeAcceptMessage)
    assert acc.ask_id == "ASK-0008"
    assert acc.link == "https://discord.com/4"

    disp = parse_intake_message(
        'DISPUTE ASK-0009 | "We agreed this was in clause 1.1" | link=https://discord.com/5'
    )
    assert isinstance(disp, IntakeDisputeMessage)
    assert disp.ask_id == "ASK-0009"
    assert disp.quote == "We agreed this was in clause 1.1"

    draft = parse_intake_message("DRAFT ASK-0007: Got it, Sam. Checking now.")
    assert isinstance(draft, IntakeDraftMessage)
    assert draft.ask_id == "ASK-0007"
    assert draft.text == "Got it, Sam. Checking now."

    # Multi-line intake message batch
    batch = parse_intake_messages(
        'ASK | "First ask" | requester=Sam | link=https://discord.com/10\n'
        'ASK | "Second ask" | requester=Sam | link=https://discord.com/11'
    )
    assert len(batch) == 2


def test_parse_intake_errors() -> None:
    """Verify ParseError and expected_format hints on malformed intake messages."""
    for bad in [
        "",
        "UNKNOWN_VERB | foo",
        "ASK | missing_fields",
        "ANSWER Q-0001 | missing_link",
        "DECISION CR-004 Z | link=https://discord.com/1",
        "ACCEPT ASK-0008",
        "DISPUTE ASK-0009 | only_quote",
    ]:
        with pytest.raises(ParseError) as exc_info:
            parse_intake_message(bad)
        assert "ASK |" in exc_info.value.expected_format


def test_parse_clerk_to_scout_messages() -> None:
    """Verify READY, QUESTION, and MODE messages from Clerk to Scout."""
    m_auto = parse_clerk_to_scout_message(
        "@acme-scout MODE autopilot until 09:30 IST (11:00 PM ET)"
    )
    assert isinstance(m_auto, ClerkModeMessage)
    assert m_auto.mode == "autopilot"
    assert m_auto.until_note == "09:30 IST (11:00 PM ET)"

    m_cop = parse_clerk_to_scout_message("MODE copilot")
    assert isinstance(m_cop, ClerkModeMessage)
    assert m_cop.mode == "copilot"

    r_msg = parse_clerk_to_scout_message("READY ASK-0007\nGot it, Sam. Back in a minute.")
    assert isinstance(r_msg, ClerkReadyMessage)
    assert r_msg.target_id == "ASK-0007"
    assert "Got it, Sam." in r_msg.text

    q_msg = parse_clerk_to_scout_message(
        "QUESTION Q-0001 for ASK-0009\nWhich format do you need?\nChoices: 1) CSV 2) Excel"
    )
    assert isinstance(q_msg, ClerkQuestionMessage)
    assert q_msg.question_id == "Q-0001"
    assert q_msg.ask_id == "ASK-0009"
    assert q_msg.choices == ["CSV", "Excel"]

    with pytest.raises(ParseError):
        parse_clerk_to_scout_message("INVALID scout message")


def test_parse_estimator_reply_fenced_and_json() -> None:
    """Verify Estimator JSON block parsing from scopekeeper-estimate and json code blocks."""
    msg = """Here is the sizing for CR-004:
```scopekeeper-estimate
{
  "cr_id": "CR-004",
  "full": { "p50_hours": 200, "p90_hours": 260, "confidence": "medium" },
  "smaller": {
    "title": "Installable web app (PWA): home-screen install + offline shell",
    "p50_hours": 56,
    "p90_hours": 72,
    "confidence": "high"
  },
  "touches": ["web/manifest.json", "web/service-worker.ts"],
  "similar": [{ "ref": "PR#42", "hours": 48 }],
  "risks": ["iOS Safari push notification quirks"],
  "assumptions": ["Reuses existing REST API"]
}
```
"""
    parsed = parse_estimator_reply(msg, posted_at="2026-11-05T19:05:00Z")
    assert parsed.cr_id == "CR-004"
    assert parsed.estimate.full.p50_hours == 200
    assert parsed.estimate.full.confidence == Confidence.MEDIUM
    assert parsed.estimate.smaller is not None
    assert parsed.estimate.smaller.p50_hours == 56
    assert parsed.estimate.smaller.confidence == Confidence.HIGH
    assert parsed.estimate.similar[0].ref == "PR#42"

    # Fallback ```json fence
    json_fence = (
        '```json\n{"cr_id": "CR-005", '
        '"full": {"p50_hours": 3, "p90_hours": 4, "confidence": "high"}}\n```'
    )
    parsed_2 = parse_estimator_reply(json_fence)
    assert parsed_2.cr_id == "CR-005"
    assert parsed_2.estimate.full.p50_hours == 3

    with pytest.raises(ParseError):
        parse_estimator_reply("No estimate block here")

    with pytest.raises(ParseError):
        parse_estimator_reply("```scopekeeper-estimate\n{bad json}\n```")


def test_parse_builder_done() -> None:
    """Verify Builder DONE command parsing."""
    done = parse_builder_done("@clerk DONE W-0003 pr=https://github.com/acme/portal/pull/48")
    assert isinstance(done, BuilderDoneMessage)
    assert done.work_id == "W-0003"
    assert done.pr_url == "https://github.com/acme/portal/pull/48"

    with pytest.raises(ParseError) as exc_info:
        parse_builder_done("@clerk DONE W-0003 missing_pr")
    assert "DONE W-" in exc_info.value.expected_format


def test_parse_all_clerk_commands() -> None:
    """Verify every @clerk human governance and demo command."""
    c_confirm = parse_clerk_command("@clerk confirm", default_cr_id="CR-004")
    assert isinstance(c_confirm, ConfirmCommand)
    assert c_confirm.cr_id == "CR-004"

    c_hours_full = parse_clerk_command("@clerk hours 180", default_cr_id="CR-004")
    assert isinstance(c_hours_full, HoursCommand)
    assert c_hours_full.hours == 180
    assert c_hours_full.version == "full"

    c_hours_sm = parse_clerk_command("@clerk hours CR-004 smaller 50h")
    assert isinstance(c_hours_sm, HoursCommand)
    assert c_hours_sm.hours == 50
    assert c_hours_sm.version == "smaller"

    c_approve_all = parse_clerk_command("@clerk approve", default_cr_id="CR-004")
    assert isinstance(c_approve_all, ApproveCommand)
    assert c_approve_all.options is None
    assert c_approve_all.cr_id == "CR-004"

    c_approve_sub = parse_clerk_command("@clerk approve CR-004 A, C, D")
    assert isinstance(c_approve_sub, ApproveCommand)
    assert c_approve_sub.options == [OptionKey.A, OptionKey.C, OptionKey.D]

    c_price = parse_clerk_command("@clerk price A $9,500", default_cr_id="CR-004")
    assert isinstance(c_price, PriceOverrideCommand)
    assert c_price.option == OptionKey.A
    assert c_price.price_usd == Decimal("9500")

    c_gw = parse_clerk_command("@clerk goodwill ASK-0006 Quick Q4 courtesy")
    assert isinstance(c_gw, GoodwillCommand)
    assert c_gw.ask_id == "ASK-0006"
    assert c_gw.reason == "Quick Q4 courtesy"

    c_dec = parse_clerk_command("@clerk decline CR-001 Out of architecture scope")
    assert isinstance(c_dec, DeclineCommand)
    assert c_dec.cr_id == "CR-001"
    assert c_dec.reason == "Out of architecture scope"

    c_ledger = parse_clerk_command("@clerk ledger november")
    assert isinstance(c_ledger, LedgerCommand)
    assert c_ledger.month == "2026-11"

    c_inv = parse_clerk_command("@clerk invoice 2026-11")
    assert isinstance(c_inv, InvoiceCommand)
    assert c_inv.month == "2026-11"

    c_ren = parse_clerk_command("@clerk renewal")
    assert isinstance(c_ren, RenewalCommand)

    c_stat = parse_clerk_command("@clerk status CR-004")
    assert isinstance(c_stat, StatusCommand)
    assert c_stat.target_id == "CR-004"

    c_mem = parse_clerk_command("@clerk what did we agree about SMS?")
    assert isinstance(c_mem, MemoryQueryCommand)
    assert c_mem.topic == "SMS"

    c_flip = parse_clerk_command("@clerk flip now")
    assert isinstance(c_flip, DemoControlCommand)
    assert c_flip.action == "flip_now"

    c_morn = parse_clerk_command("@clerk morning now")
    assert isinstance(c_morn, DemoControlCommand)
    assert c_morn.action == "morning_now"

    c_clock = parse_clerk_command("@clerk clock +10h")
    assert isinstance(c_clock, DemoControlCommand)
    assert c_clock.action == "clock"
    assert c_clock.offset == "+10h"

    with pytest.raises(ParseError):
        parse_clerk_command("@clerk unknown_command 123")
