"""Monthly goodwill bucket calculation and suggestion rules."""

from __future__ import annotations

from decimal import Decimal

from clerk.domain.models import ChangePolicyConfig


def remaining_goodwill_hours(
    used_hours: int | float | Decimal,
    policy: ChangePolicyConfig,
) -> Decimal:
    """Return remaining goodwill hours in the current month's bucket (never negative)."""
    bucket = Decimal(str(policy.goodwill_hours_per_month))
    used = Decimal(str(used_hours))
    return max(Decimal("0"), bucket - used)


def can_grant_goodwill(
    ask_hours: int | float | Decimal,
    used_hours: int | float | Decimal,
    policy: ChangePolicyConfig,
) -> bool:
    """Return True if the monthly goodwill bucket has enough remaining hours for `ask_hours`."""
    hours = Decimal(str(ask_hours))
    if hours <= Decimal("0"):
        return False
    return hours <= remaining_goodwill_hours(used_hours, policy)


def should_suggest_goodwill(
    ask_hours: int | float | Decimal,
    used_hours: int | float | Decimal,
    policy: ChangePolicyConfig,
) -> bool:
    """Return True if Clerk should suggest goodwill to @account-manager.

    Clerk suggests goodwill for small asks (`ask_hours <= goodwill_suggest_below_hours`)
    while the monthly bucket still has capacity for the ask.
    """
    hours = Decimal(str(ask_hours))
    threshold = Decimal(str(policy.goodwill_suggest_below_hours))
    if hours <= Decimal("0") or hours > threshold:
        return False
    return can_grant_goodwill(hours, used_hours, policy)
