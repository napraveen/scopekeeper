"""Unit tests for deterministic pricing and option builder."""

from __future__ import annotations

from decimal import Decimal

import pytest

from clerk.domain.models import (
    Confidence,
    ContingencyConfig,
    Estimate,
    EstimateVersion,
    Milestone,
    OptionKey,
    Plan,
    PlanItem,
    RateCardConfig,
    ScopeMapConfig,
)
from clerk.domain.pricing import (
    build_options,
    compute_price_cents,
    compute_price_usd,
    select_affected_milestone,
)
from clerk.domain.templates import format_usd


@pytest.mark.parametrize(
    ("hours", "confidence", "expected_usd", "expected_cents"),
    [
        (3, Confidence.HIGH, Decimal("140"), 14000),
        (200, Confidence.MEDIUM, Decimal("10350"), 1035000),
        (56, Confidence.HIGH, Decimal("2650"), 265000),
        (40, Confidence.HIGH, Decimal("1890"), 189000),
        (20, Confidence.HIGH, Decimal("950"), 95000),
        (0, Confidence.HIGH, Decimal("0"), 0),
        (-5, Confidence.HIGH, Decimal("0"), 0),
        (10, Confidence.LOW, Decimal("560"), 56000),
    ],
)
def test_compute_price_canonical_cases(
    rate_card: RateCardConfig,
    hours: int,
    confidence: Confidence,
    expected_usd: Decimal,
    expected_cents: int,
) -> None:
    """Verify exact prices for canonical hackathon cases."""
    assert compute_price_usd(hours, confidence, rate_card) == expected_usd
    assert compute_price_cents(hours, confidence, rate_card) == expected_cents


def test_compute_price_round_half_up() -> None:
    """Verify ROUND_HALF_UP behavior when raw price lands at a $5 midpoint."""
    custom_card = RateCardConfig(
        currency="USD",
        blended_rate=Decimal("15"),
        contingency=ContingencyConfig(
            high=Decimal("0"),
            medium=Decimal("0"),
            low=Decimal("0"),
        ),
        round_to=10,
    )
    # 1h * $15 = $15 -> midpoint of $10 increment -> rounds half up to $20
    assert compute_price_usd(1, Confidence.HIGH, custom_card) == Decimal("20")
    assert compute_price_cents(1, Confidence.HIGH, custom_card) == 2000


def test_format_usd() -> None:
    """Verify human-readable USD formatting from integer cents."""
    assert format_usd(14000) == "$140"
    assert format_usd(1035000) == "$10,350"
    assert format_usd(265000) == "$2,650"
    assert format_usd(0) == "$0"
    assert format_usd(12345) == "$123.45"


def test_select_affected_milestone_and_fallback(plan: Plan) -> None:
    """Verify active milestone selection and fallback when all items are done."""
    active = select_affected_milestone(plan)
    assert active is not None
    assert active.id == "M2"

    all_done = Plan(
        capacity_hours_per_week=120,
        milestones=[
            Milestone(
                id="M1",
                name="Done",
                due="2026-10-25",
                items=[
                    PlanItem(
                        id="I1",
                        title="Done item",
                        deliverable="D1",
                        hours=10,
                        status="done",
                        done_on="2026-10-20",
                    )
                ],
            )
        ],
    )
    fallback = select_affected_milestone(all_done)
    assert fallback is not None
    assert fallback.id == "M1"


def test_build_options_cr_004_four_options(
    rate_card: RateCardConfig,
    plan: Plan,
    scope_map: ScopeMapConfig,
) -> None:
    """Verify CR-004 (Android app) builds Options A, B, C, and D accurately."""
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

    assert [opt.key for opt in options] == [
        OptionKey.A,
        OptionKey.B,
        OptionKey.C,
        OptionKey.D,
    ]

    opt_a, opt_b, opt_c, opt_d = options

    # Option A: Full app now (200h medium -> $10,350, +12 days -> 2026-12-24)
    assert opt_a.hours == 200
    assert opt_a.price_cents == 1035000
    assert opt_a.milestone_id == "M2"
    assert opt_a.shift_days == 12
    assert opt_a.new_due == "2026-12-24"
    assert opt_a.swap_out is None

    # Option B: Next phase (200h medium -> $10,350, 0 shift days)
    assert opt_b.hours == 200
    assert opt_b.price_cents == 1035000
    assert opt_b.shift_days == 0
    assert opt_b.new_due == "2026-12-12"

    # Option C: Smaller scope (56h high -> $2,650, +3 days -> 2026-12-15)
    assert opt_c.hours == 56
    assert opt_c.price_cents == 265000
    assert opt_c.milestone_id == "M2"
    assert opt_c.shift_days == 3
    assert opt_c.new_due == "2026-12-15"
    assert opt_c.label == "Installable web app (PWA) by Friday"

    # Option D: Scope swap (56h swaps out I9 58h -> $0, 0 shift days)
    assert opt_d.hours == 56
    assert opt_d.price_cents == 0
    assert opt_d.milestone_id == "M2"
    assert opt_d.shift_days == 0
    assert opt_d.new_due == "2026-12-12"
    assert opt_d.swap_out == ["I9"]
    assert "instead of the admin analytics dashboard" in opt_d.label


def test_build_options_cr_005_single_option(
    rate_card: RateCardConfig,
    plan: Plan,
    scope_map: ScopeMapConfig,
) -> None:
    """Verify CR-005 (3h high, no smaller, no swap) builds only Option A."""
    estimate = Estimate(
        full=EstimateVersion(
            title="Custom welcome banner on login screen",
            p50_hours=3,
            p90_hours=4,
            confidence=Confidence.HIGH,
        ),
        smaller=None,
    )

    options = build_options(
        ask_title="Custom welcome banner",
        estimate=estimate,
        confirmed_hours=3,
        plan=plan,
        rate_card=rate_card,
        swap_policy=scope_map.change_policy.swap,
    )

    assert len(options) == 1
    opt_a = options[0]
    assert opt_a.key == OptionKey.A
    assert opt_a.hours == 3
    assert opt_a.price_cents == 14000
    assert opt_a.shift_days == 0
    assert opt_a.new_due == "2026-12-12"
