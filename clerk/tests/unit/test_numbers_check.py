"""Unit tests for the numbers integrity check (check_numbers)."""

from __future__ import annotations

from datetime import date

from clerk.domain.numbers_check import check_numbers


def test_check_numbers_passes_when_all_tokens_in_facts() -> None:
    """Verify check_numbers passes when prices, dates, hours, and clauses appear in facts."""
    facts = {
        "cr_id": "CR-004",
        "ask_id": "ASK-0008",
        "clauses": ["1.3", "3.2"],
        "items": ["I9"],
        "milestones": ["M2"],
        "price_cents": 1035000,
        "smaller_price_cents": 265000,
        "swap_price_cents": 0,
        "hours": [200, 56, 58, 3],
        "dates": ["2026-12-24", "2026-12-15", date(2026, 12, 12)],
    }
    text = (
        "An Android app is outside our current agreement (clause 1.3, native mobile apps). "
        "Your options:\n"
        "A) Full app now: $10,350; the December 12 milestone moves to December 24\n"
        "B) Full app in the next phase: $10,350; no change to current dates\n"
        "C) Installable web app (PWA): $2,650; the milestone moves about 3 days\n"
        "D) Installable web app (PWA) instead of the admin analytics dashboard: "
        "no extra cost, no date change"
    )
    result = check_numbers(text, facts)
    assert result.passed is True
    assert result.unexpected_tokens == []


def test_check_numbers_fails_on_hallucinated_price() -> None:
    """Verify check_numbers catches an invented dollar price."""
    facts = {
        "cr_id": "CR-004",
        "prices": ["$10,350", "$2,650"],
        "hours": [200, 56],
    }
    text = "Option A is $9,500 for 200 hours, or Option B is $2,650 for 56 hours."
    result = check_numbers(text, facts)
    assert result.passed is False
    assert "$9500" in result.unexpected_tokens


def test_check_numbers_fails_on_hallucinated_date_or_number() -> None:
    """Verify check_numbers catches invented dates, hours, and clause numbers."""
    facts = {
        "cr_id": "CR-004",
        "prices": ["$2,650"],
        "hours": [56],
        "dates": ["2026-12-15"],
        "clauses": ["1.3"],
    }
    text = (
        "Under CR-004 (clause 4.9), we can deliver in 40 hours for $2,650 by December 20."
    )
    result = check_numbers(text, facts)
    assert result.passed is False
    assert "40" in result.unexpected_tokens
    assert "4.9" in result.unexpected_tokens
    assert "12-20" in result.unexpected_tokens
