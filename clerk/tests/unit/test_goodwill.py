"""Unit tests for monthly goodwill bucket tracking and eligibility."""

from __future__ import annotations

from decimal import Decimal

from clerk.domain.goodwill import (
    can_grant_goodwill,
    remaining_goodwill_hours,
    should_suggest_goodwill,
)
from clerk.domain.models import ScopeMapConfig, SeedLedgerConfig


def test_remaining_goodwill_hours_from_seed_ledger(
    scope_map: ScopeMapConfig,
    seed_ledger: SeedLedgerConfig,
) -> None:
    """Seed ledger has 2h used in 2026-11 out of 8h monthly bucket -> 6h remaining."""
    used = sum(g.hours for g in seed_ledger.goodwill if g.month == "2026-11")
    assert used == 2
    rem = remaining_goodwill_hours(used, scope_map.change_policy)
    assert rem == Decimal("6")

    # Never negative if used exceeds bucket
    assert remaining_goodwill_hours(10, scope_map.change_policy) == Decimal("0")


def test_can_grant_and_should_suggest_goodwill(
    scope_map: ScopeMapConfig,
) -> None:
    """Verify goodwill grant validation and 2h suggestion threshold."""
    policy = scope_map.change_policy

    assert can_grant_goodwill(2, used_hours=2, policy=policy) is True
    assert can_grant_goodwill(6, used_hours=2, policy=policy) is True
    assert can_grant_goodwill(7, used_hours=2, policy=policy) is False
    assert can_grant_goodwill(0, used_hours=2, policy=policy) is False
    assert can_grant_goodwill(-1, used_hours=2, policy=policy) is False

    # Suggest goodwill when ask_hours <= goodwill_suggest_below_hours (2h) and bucket has room
    assert should_suggest_goodwill(1.5, used_hours=2, policy=policy) is True
    assert should_suggest_goodwill(2, used_hours=2, policy=policy) is True
    assert should_suggest_goodwill(3, used_hours=2, policy=policy) is False
    assert should_suggest_goodwill(0, used_hours=2, policy=policy) is False
    assert should_suggest_goodwill(2, used_hours=7, policy=policy) is False
