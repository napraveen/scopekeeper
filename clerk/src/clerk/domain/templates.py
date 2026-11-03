"""Deterministic client-facing and internal templates (Section 6)."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from clerk.domain.dates import format_month_day
from clerk.domain.models import (
    Ask,
    Category,
    ChangeRequest,
    LedgerEntry,
    OptionKey,
    OptionQuote,
    WorkItem,
)

_NUMBER_WORDS: dict[int, str] = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}


def format_usd(cents: int) -> str:
    """Format integer cents as USD string without trailing '.00' when whole dollars."""
    dollars = Decimal(cents) / Decimal("100")
    if dollars == dollars.to_integral_value():
        return f"${int(dollars):,}"
    return f"${dollars:,.2f}"


# ── Client-Facing Templates ───────────────────────────────────────────────────


def render_acknowledgement(client_name: str, count: int) -> str:
    """Render the immediate multi-ask acknowledgement for the client."""
    word = _NUMBER_WORDS.get(count, str(count))
    noun = "thing" if count == 1 else "things"
    pronoun = "it" if count == 1 else "each one"
    return f"Got it, {client_name}. I see {word} {noun} here; back in a minute with {pronoun}."


def render_verdicts(asks: Sequence[Ask]) -> str:
    """Render a numbered list of verdicts, one line per ask, with the clause in brackets."""
    lines: list[str] = []
    for idx, ask in enumerate(asks, 1):
        clause_str = f" [clause {', '.join(ask.clause_ids)}]" if ask.clause_ids else ""
        cat = ask.category
        if cat == Category.DEFECT:
            verdict = "Defect under warranty — we're fixing this free of charge"
        elif cat == Category.IN_SCOPE:
            verdict = "In scope — queued for the team now"
        elif cat == Category.UNCLEAR:
            verdict = "Needs one quick clarification from you"
        elif cat == Category.OUT_OF_SCOPE:
            verdict = "Outside current scope — preparing change options"
        elif cat == Category.DUPLICATE:
            item_note = f" ({ask.related_item})" if ask.related_item else ""
            verdict = f"Already in our delivery plan{item_note}"
        elif cat == Category.ALREADY_DECIDED:
            dec_note = f" ({ask.decision_id})" if ask.decision_id else ""
            verdict = f"Covered by an earlier decision{dec_note}"
        else:
            verdict = "Received and reviewing"
        lines.append(f'{idx}) "{ask.quote}" — {verdict}{clause_str}')
    return "\n".join(lines)


def render_preview_ready(feature_name: str, preview_url: str) -> str:
    """Render the client preview notification (at most 5 lines)."""
    clean_name = feature_name[0].upper() + feature_name[1:] if feature_name else "Preview"
    return f"{clean_name} is ready to try: {preview_url}. Reply 'accept' if it looks right."


def render_handover_greeting(
    client_name: str = "Sam",
    until_client_time: str = "11 PM",
    person_name: str = "Priya",
) -> str:
    """Render Scout's shift handover greeting in acme-client."""
    return (
        f"Hi {client_name}, I'm covering the desk until {until_client_time} your time. "
        f"{person_name} is back after that."
    )


def render_change_order(
    *,
    subject: str,
    clause_id: str,
    clause_summary: str,
    options: Sequence[OptionQuote],
    current_milestone_due: str | None = None,
) -> str:
    """Render a client-facing Change Order message matching Section 6."""
    header = f"{subject} is outside our current agreement (clause {clause_id}, {clause_summary})."
    if len(options) == 1 and options[0].shift_days == 0:
        opt = options[0]
        price_str = format_usd(opt.price_cents)
        return (
            f"{header} We can add it for {price_str} with no change to current dates.\n"
            f'Reply with A to approve, or "not now".'
        )

    lines: list[str] = [f"{header} Your options:"]
    keys_list: list[str] = []
    for opt in options:
        keys_list.append(opt.key.value)
        price_str = format_usd(opt.price_cents)
        if opt.key == OptionKey.D or opt.swap_out:
            lines.append(f"{opt.key.value}) {opt.label}: no extra cost, no date change")
        elif opt.key == OptionKey.B:
            lines.append(f"{opt.key.value}) {opt.label}: {price_str}; no change to current dates")
        elif opt.key == OptionKey.C:
            if opt.shift_days > 0:
                day_word = "day" if opt.shift_days == 1 else "days"
                shift_part = f"the milestone moves about {opt.shift_days} {day_word}"
            else:
                shift_part = "no change to current dates"
            lines.append(f"{opt.key.value}) {opt.label}: {price_str}; {shift_part}")
        else:
            # Option A
            if opt.shift_days > 0 and current_milestone_due and opt.new_due:
                old_md = format_month_day(current_milestone_due)
                new_md = format_month_day(opt.new_due)
                shift_part = f"the {old_md} milestone moves to {new_md}"
            elif opt.shift_days > 0:
                day_word = "day" if opt.shift_days == 1 else "days"
                shift_part = f"the milestone moves by {opt.shift_days} {day_word}"
            else:
                shift_part = "no change to current dates"
            lines.append(f"{opt.key.value}) {opt.label}: {price_str}; {shift_part}")

    keys_joined = ", ".join(keys_list)
    lines.append(f'Reply with {keys_joined}, or "not now".')
    return "\n".join(lines)


def render_ready(target_id: str, client_text: str) -> str:
    """Wrap client-facing text in a Clerk -> Scout READY message for acme-intake."""
    return f"READY {target_id}\n{client_text.strip()}"


def render_question(question_id: str, ask_id: str, text: str, choices: Sequence[str]) -> str:
    """Render a Clerk -> Scout QUESTION message for acme-intake."""
    formatted_choices = " ".join(f"{idx}) {choice}" for idx, choice in enumerate(choices, 1))
    return f"QUESTION {question_id} for {ask_id}\n{text.strip()}\nChoices: {formatted_choices}"


# ── Internal Agency Templates ─────────────────────────────────────────────────


def render_estimator_request(
    *,
    cr_id: str,
    ask_id: str,
    quote: str,
    context: str,
    repo_name: str = "acme-portal",
    estimator_handle: str = "@acme-estimator",
) -> str:
    """Render Clerk's targeted request to the Estimator in a change room (Section 6)."""
    handle = estimator_handle if estimator_handle.startswith("@") else f"@{estimator_handle}"
    return (
        f'{handle} estimate {cr_id} for {ask_id}: "{quote}". '
        f"Context: {context}. Repo: {repo_name}. "
        f"Reply to @clerk with exactly one fenced block whose info string is scopekeeper-estimate."
    )


def render_work_order(
    *,
    work: WorkItem,
    ask: Ask,
    clause_note: str,
    ticket_ref: str,
    pr_title: str,
    acceptance_criteria: str,
    builder_handle: str = "@acme-builder",
) -> str:
    """Render Clerk's targeted WORK order to the Builder in acme-delivery (Section 6)."""
    handle = builder_handle if builder_handle.startswith("@") else f"@{builder_handle}"
    return (
        f"{handle} WORK {work.id} for {ask.id} ({clause_note})\n"
        f"Ticket: {ticket_ref}\n"
        f"Branch: {work.branch}\n"
        f"PR title: {pr_title}\n"
        f"Done when: {acceptance_criteria}\n"
        f"Reply: @clerk DONE {work.id} pr=<url>"
    )


def render_change_room_opening(
    *,
    cr: ChangeRequest,
    ask: Ask,
    sow_context: str,
) -> str:
    """Render the opening summary message in a newly created acme-cr-NNN room."""
    clauses = ", ".join(ask.clause_ids) if ask.clause_ids else "none"
    return (
        f'Change Request {cr.id} opened for {ask.id}: "{ask.quote}"\n'
        f"Requester: {ask.requester} | Source: {ask.source.url}\n"
        f"Governing SOW Clause(s): {clauses} — {sow_context}\n"
        f"Step 1: Waiting on @acme-estimator to post `scopekeeper-estimate`."
    )


def render_morning_brief(
    *,
    came_in: Sequence[Ask],
    shipped: Sequence[WorkItem],
    needs_approval: Sequence[ChangeRequest],
    goodwill_remaining_hours: Decimal | float,
) -> str:
    """Render the 9:30 AM IST morning brief in acme-delivery."""
    lines: list[str] = ["Morning brief — overnight desk summary:"]

    # 1. Came in overnight
    if came_in:
        ask_summaries = ", ".join(
            f"{a.id} ({a.category.value if a.category else 'pending'})" for a in came_in
        )
        lines.append(f"- Came in ({len(came_in)}): {ask_summaries}")
    else:
        lines.append("- Came in: none")

    # 2. Shipped / previews ready
    if shipped:
        ship_items = []
        for w in shipped:
            links = [x for x in [w.pr_url, w.preview_url] if x]
            link_str = f" ({' | '.join(links)})" if links else ""
            ship_items.append(f"{w.id} for {w.ask_id} [{w.status.value}]{link_str}")
        lines.append(f"- Shipped ({len(shipped)}): " + "; ".join(ship_items))
    else:
        lines.append("- Shipped: none")

    # 3. Needs a yes (with exact approve command per CR)
    if needs_approval:
        lines.append("- Needs a yes:")
        for cr in needs_approval:
            opt_keys = ",".join(o.key.value for o in cr.options) or "A"
            lines.append(
                f"  • {cr.id} ({cr.title}): confirm/approve in {cr.room.room} "
                f"with `@clerk approve {opt_keys}` (or `@clerk approve`)"
            )
    else:
        lines.append("- Needs a yes: none")

    lines.append(f"- Goodwill remaining this month: {goodwill_remaining_hours} h")
    return "\n".join(lines)


def render_ledger_message(
    *,
    month: str,
    entries: Sequence[LedgerEntry],
    revenue_protected_cents: int,
    swaps_count: int,
    goodwill_used: float,
    goodwill_bucket: float,
) -> str:
    """Render the human-readable ledger summary for acme-delivery."""
    rev_str = format_usd(revenue_protected_cents)
    lines: list[str] = [
        f"ScopeKeeper Ledger ({month}) — Revenue protected: {rev_str} "
        f"| Swaps: {swaps_count} | Goodwill: {goodwill_used:g}/{goodwill_bucket:g} h"
    ]
    for e in entries:
        amt_str = format_usd(e.amount_cents)
        link_part = f" ({e.link.url})" if e.link else ""
        lines.append(
            f"- {e.date} | {e.ref} | {e.kind} | {e.title} | {e.hours:g} h | {amt_str}{link_part}"
        )
    return "\n".join(lines)


def render_invoice_csv(entries: Sequence[LedgerEntry]) -> str:
    """Render the monthly invoice CSV (`date,change,option,hours,price_usd,approved_by,link`)."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["date", "change", "option", "hours", "price_usd", "approved_by", "link"])
    for entry in entries:
        if entry.kind not in {"change_order", "swap"}:
            continue
        option_val = "D" if entry.kind == "swap" else "A"
        price_usd = Decimal(entry.amount_cents) / Decimal("100")
        price_str = (
            str(int(price_usd))
            if price_usd == price_usd.to_integral_value()
            else f"{price_usd:.2f}"
        )
        hours_str = str(int(entry.hours)) if float(entry.hours).is_integer() else f"{entry.hours:g}"
        writer.writerow(
            [
                entry.date,
                entry.ref,
                option_val,
                hours_str,
                price_str,
                entry.approved_by or "",
                entry.link.url if entry.link else "",
            ]
        )
    return buf.getvalue()


def render_renewal_report(themes: Sequence[dict[str, Any]]) -> str:
    """Render the phase renewal add-on proposal from grouped out-of-scope asks."""
    if not themes:
        return "Renewal Report: No out-of-scope asks recorded for next-phase add-ons."
    lines: list[str] = ["Renewal Report — Proposed Next-Phase Add-Ons:"]
    total_hours = 0
    for idx, theme in enumerate(themes, 1):
        name = str(theme.get("name", f"Theme {idx}"))
        member_ids = ", ".join(str(m) for m in theme.get("member_ids", []))
        hours = int(theme.get("total_hours", 0))
        total_hours += hours
        lines.append(f"{idx}) {name} ({member_ids}) — {hours} h")
    lines.append(f"Total proposed renewal scope: {total_hours} h")
    return "\n".join(lines)
