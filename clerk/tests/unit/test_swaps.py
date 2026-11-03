"""Unit tests for scope swap candidate finder."""

from __future__ import annotations

from decimal import Decimal

from clerk.domain.models import (
    Confidence,
    EstimateVersion,
    Milestone,
    Plan,
    PlanItem,
    ScopeMapConfig,
    SwapPolicyConfig,
)
from clerk.domain.swaps import (
    find_swap_for_estimate,
    find_swap_for_hours,
)


def test_swap_finder_200h_returns_none(plan: Plan, scope_map: ScopeMapConfig) -> None:
    """200h has no match among unstarted items I9 (58h) and I10 (24h)."""
    match = find_swap_for_hours(200, plan, scope_map.change_policy.swap)
    assert match is None


def test_swap_finder_56h_matches_i9(plan: Plan, scope_map: ScopeMapConfig) -> None:
    """56h matches I9 (58h, gap 3.57% <= 10%)."""
    match = find_swap_for_hours(56, plan, scope_map.change_policy.swap)
    assert match is not None
    assert match.item_ids == ["I9"]
    assert match.removed_hours == 58
    assert match.removed_titles == "Admin analytics dashboard"
    assert match.using_smaller is False
    assert match.gap_ratio == Decimal("2") / Decimal("56")


def test_swap_finder_for_estimate_falls_back_to_smaller(
    plan: Plan,
    scope_map: ScopeMapConfig,
) -> None:
    """When full scope (200h) has no swap, find_swap_for_estimate falls back to smaller (56h)."""
    smaller = EstimateVersion(
        title="Installable web app (PWA): home-screen install + offline shell",
        p50_hours=56,
        p90_hours=72,
        confidence=Confidence.HIGH,
    )
    match = find_swap_for_estimate(
        confirmed_hours=200,
        smaller=smaller,
        plan=plan,
        swap_policy=scope_map.change_policy.swap,
    )
    assert match is not None
    assert match.item_ids == ["I9"]
    assert match.using_smaller is True


def test_swap_finder_pair_match(plan: Plan, scope_map: ScopeMapConfig) -> None:
    """When no single item fits 80h, pair I9 (58h) + I10 (24h) = 82h fits within 10% (2.5% gap)."""
    match = find_swap_for_hours(80, plan, scope_map.change_policy.swap)
    assert match is not None
    assert match.item_ids == ["I9", "I10"]
    assert match.removed_hours == 82
    assert match.removed_titles == "Admin analytics dashboard and Report filters v2"


def test_single_item_preferred_over_closer_pair(scope_map: ScopeMapConfig) -> None:
    """A single unstarted item within tolerance is preferred over a 2-item pair with smaller gap."""
    custom_plan = Plan(
        capacity_hours_per_week=120,
        milestones=[
            Milestone(
                id="M2",
                name="Milestone 2",
                due="2026-12-12",
                items=[
                    PlanItem(
                        id="I1",
                        title="Single candidate",
                        deliverable="D3",
                        hours=108,  # 8% gap from 100h
                        status="unstarted",
                        priority=2,
                    ),
                    PlanItem(
                        id="I2",
                        title="Pair part A",
                        deliverable="D3",
                        hours=50,
                        status="unstarted",
                        priority=3,
                    ),
                    PlanItem(
                        id="I3",
                        title="Pair part B",
                        deliverable="D3",
                        hours=50,  # I2+I3 = 100h (0% gap)
                        status="unstarted",
                        priority=3,
                    ),
                ],
            )
        ],
    )
    match = find_swap_for_hours(100, custom_plan, scope_map.change_policy.swap)
    assert match is not None
    assert match.item_ids == ["I1"]


def test_swap_tie_breaking_by_priority_and_id(scope_map: ScopeMapConfig) -> None:
    """Tie-break equal gaps by lowest priority (highest priority int), then by item ID."""
    custom_plan = Plan(
        capacity_hours_per_week=120,
        milestones=[
            Milestone(
                id="M2",
                name="Milestone 2",
                due="2026-12-12",
                items=[
                    PlanItem(
                        id="I1",
                        title="Higher priority item (priority 1)",
                        deliverable="D3",
                        hours=50,
                        status="unstarted",
                        priority=1,
                    ),
                    PlanItem(
                        id="I9",
                        title="Lower priority item (priority 3)",
                        deliverable="D3",
                        hours=50,
                        status="unstarted",
                        priority=3,
                    ),
                    PlanItem(
                        id="I10",
                        title="Same priority 3, higher natural ID",
                        deliverable="D3",
                        hours=50,
                        status="unstarted",
                        priority=3,
                    ),
                ],
            )
        ],
    )
    match = find_swap_for_hours(50, custom_plan, scope_map.change_policy.swap)
    assert match is not None
    # I9 and I10 both have priority=3 (lowest priority), and I9 < I10 by natural ID order
    assert match.item_ids == ["I9"]


def test_swap_disabled_or_zero_hours(plan: Plan) -> None:
    """Disabled swap policy or non-positive hours returns None."""
    disabled_policy = SwapPolicyConfig(
        allowed=False, tolerance=Decimal("0.10"), only_unstarted=True
    )
    assert find_swap_for_hours(56, plan, disabled_policy) is None

    enabled_policy = SwapPolicyConfig(allowed=True, tolerance=Decimal("0.10"), only_unstarted=True)
    assert find_swap_for_hours(0, plan, enabled_policy) is None
