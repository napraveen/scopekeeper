"""Unit tests for autonomous pricing envelope checks."""

from __future__ import annotations

from decimal import Decimal

from clerk.domain.envelope import check_envelope
from clerk.domain.models import Confidence, EnvelopeConfig


def test_envelope_passes_for_small_high_confidence_cr(
    envelope_config: EnvelopeConfig,
) -> None:
    """CR-005 (3h high, $140, 0 shift days) passes the autonomous envelope."""
    result = check_envelope(
        price_usd=Decimal("140"),
        confidence=Confidence.HIGH,
        milestone_impact_days=0,
        envelope=envelope_config,
        has_swap=False,
    )
    assert result.passed is True
    assert result.failed_rules == []


def test_envelope_fails_for_cr_004_multiple_rules(
    envelope_config: EnvelopeConfig,
) -> None:
    """CR-004 (200h medium, $10,350, 12 shift days, with swap option) fails all relevant rules."""
    result = check_envelope(
        price_usd=Decimal("10350"),
        confidence=Confidence.MEDIUM,
        milestone_impact_days=12,
        envelope=envelope_config,
        has_swap=True,
    )
    assert result.passed is False
    assert set(result.failed_rules) == {
        "max_price_usd",
        "min_confidence",
        "milestone_impact_days",
        "swap_requires_approval",
    }


def test_envelope_fails_each_rule_individually(
    envelope_config: EnvelopeConfig,
) -> None:
    """Verify each individual rule failure is reported accurately."""
    # 1. Price > $500 ($510)
    r_price = check_envelope(
        price_usd=Decimal("510"),
        confidence=Confidence.HIGH,
        milestone_impact_days=0,
        envelope=envelope_config,
    )
    assert r_price.passed is False
    assert r_price.failed_rules == ["max_price_usd"]

    # 2. Confidence < high (medium)
    r_conf = check_envelope(
        price_usd=Decimal("140"),
        confidence=Confidence.MEDIUM,
        milestone_impact_days=0,
        envelope=envelope_config,
    )
    assert r_conf.passed is False
    assert r_conf.failed_rules == ["min_confidence"]

    # 3. Shift days > 0 (1 day)
    r_shift = check_envelope(
        price_usd=Decimal("140"),
        confidence=Confidence.HIGH,
        milestone_impact_days=1,
        envelope=envelope_config,
    )
    assert r_shift.passed is False
    assert r_shift.failed_rules == ["milestone_impact_days"]

    # 4. Client not in good standing
    r_standing = check_envelope(
        price_usd=Decimal("140"),
        confidence=Confidence.HIGH,
        milestone_impact_days=0,
        envelope=envelope_config,
        client_in_good_standing=False,
    )
    assert r_standing.passed is False
    assert r_standing.failed_rules == ["client_in_good_standing"]

    # 5. Swap option requires approval
    r_swap = check_envelope(
        price_usd=Decimal("140"),
        confidence=Confidence.HIGH,
        milestone_impact_days=0,
        envelope=envelope_config,
        has_swap=True,
    )
    assert r_swap.passed is False
    assert r_swap.failed_rules == ["swap_requires_approval"]
