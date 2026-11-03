"""Autonomous approval envelope evaluation."""

from __future__ import annotations

from decimal import Decimal

from clerk.domain.models import Confidence, EnvelopeConfig, EnvelopeResult

_CONFIDENCE_RANK: dict[Confidence, int] = {
    Confidence.LOW: 1,
    Confidence.MEDIUM: 2,
    Confidence.HIGH: 3,
}


def check_envelope(
    *,
    price_usd: int | Decimal,
    confidence: Confidence,
    milestone_impact_days: int,
    envelope: EnvelopeConfig,
    client_in_good_standing: bool | None = None,
    has_swap: bool = False,
) -> EnvelopeResult:
    """Evaluate whether a Change Request qualifies for autonomous approval under the envelope.

    Every rule must pass:
      1. `max_price_usd`: price_usd <= envelope.max_price_usd
      2. `min_confidence`: confidence >= envelope.min_confidence
      3. `milestone_impact_days`: milestone_impact_days <= envelope.milestone_impact_days
      4. `client_in_good_standing`: client_in_good_standing is True
      5. `swap_requires_approval`: swaps always require @account-manager approval
    """
    failed_rules: list[str] = []

    price_dec = Decimal(str(price_usd))
    if price_dec > envelope.max_price_usd:
        failed_rules.append("max_price_usd")

    if _CONFIDENCE_RANK[confidence] < _CONFIDENCE_RANK[envelope.min_confidence]:
        failed_rules.append("min_confidence")

    if milestone_impact_days > envelope.milestone_impact_days:
        failed_rules.append("milestone_impact_days")

    standing = (
        envelope.client_in_good_standing
        if client_in_good_standing is None
        else (envelope.client_in_good_standing and client_in_good_standing)
    )
    if not standing:
        failed_rules.append("client_in_good_standing")

    if has_swap:
        failed_rules.append("swap_requires_approval")

    return EnvelopeResult(passed=len(failed_rules) == 0, failed_rules=failed_rules)
