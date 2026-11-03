"""Deterministic Decimal pricing and Change Request option builder."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from clerk.domain.dates import compute_shift_days, shift_due_date
from clerk.domain.models import (
    Confidence,
    Estimate,
    EstimateVersion,
    Milestone,
    OptionKey,
    OptionQuote,
    Plan,
    RateCardConfig,
    SwapPolicyConfig,
)
from clerk.domain.swaps import find_swap_for_estimate


def compute_price_usd(
    hours: int | Decimal,
    confidence: Confidence,
    rate_card: RateCardConfig,
) -> Decimal:
    """Compute the deterministic price in USD using Decimal and ROUND_HALF_UP.

    Formula:
        price = round_to(hours * blended_rate * (1 + contingency[confidence]))

    Verified reference values (blended_rate=45, round_to=10):
      - 3 h, high (0.05)    -> 141.75   -> $140
      - 200 h, medium (0.15)-> 10350.00 -> $10,350
      - 56 h, high (0.05)   -> 2646.00  -> $2,650
      - 40 h, high (0.05)   -> 1890.00  -> $1,890
      - 20 h, high (0.05)   -> 945.00   -> $950
    """
    if hours <= 0:
        return Decimal("0")
    h = Decimal(str(hours))
    rate = rate_card.blended_rate
    contingency = rate_card.contingency.for_confidence(confidence)
    raw = h * rate * (Decimal("1") + contingency)
    step = Decimal(str(rate_card.round_to))
    units = (raw / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return units * step


def compute_price_cents(
    hours: int | Decimal,
    confidence: Confidence,
    rate_card: RateCardConfig,
) -> int:
    """Compute the deterministic price in integer USD cents."""
    usd = compute_price_usd(hours, confidence, rate_card)
    return int((usd * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def select_affected_milestone(plan: Plan) -> Milestone | None:
    """Select the active milestone (first milestone with unstarted/in-progress items, or last)."""
    for milestone in plan.milestones:
        if any(item.status != "done" for item in milestone.items):
            return milestone
    return plan.milestones[-1] if plan.milestones else None


def _short_smaller_name(smaller_title: str | None) -> str:
    """Extract concise prefix from a smaller estimate title (before ':')."""
    if not smaller_title:
        return "Smaller version"
    return smaller_title.split(":")[0].strip()


def _lower_article_title(title: str) -> str:
    """Format an item title with 'the ' in lowercase for natural sentence embedding."""
    lowered = title[0].lower() + title[1:] if title else title
    if lowered.lower().startswith("the "):
        return lowered
    return f"the {lowered}"


def build_options(
    *,
    ask_title: str,
    estimate: Estimate,
    confirmed_hours: int,
    plan: Plan,
    rate_card: RateCardConfig,
    swap_policy: SwapPolicyConfig,
    smaller_confirmed_hours: int | None = None,
    smaller_due_hint: str | None = None,
) -> list[OptionQuote]:
    """Build Change Request Options A, B, C, and D deterministically from code.

    - Option A: Build now, full price, shifts active milestone.
    - Option B: Next phase, full price, 0 shift now (when shift > 0 or smaller exists).
    - Option C: Smaller version at its own price and shift (skipped if no `estimate.smaller`).
    - Option D: Scope swap for $0 and 0 shift (skipped if no swap candidate matches).
    """
    milestone = select_affected_milestone(plan)
    milestone_id = milestone.id if milestone else None
    milestone_due = milestone.due if milestone else None

    full_confidence = estimate.full.confidence
    full_price_cents = compute_price_cents(confirmed_hours, full_confidence, rate_card)
    full_shift_days = compute_shift_days(confirmed_hours, plan.capacity_hours_per_week)
    full_new_due = (
        shift_due_date(milestone_due, full_shift_days)
        if milestone_due and full_shift_days > 0
        else milestone_due
    )

    options: list[OptionQuote] = []

    # Option A: Full scope now
    options.append(
        OptionQuote(
            key=OptionKey.A,
            label="Full app now" if "app" in ask_title.lower() else f"{ask_title} now",
            description=estimate.full.title or ask_title,
            hours=confirmed_hours,
            price_cents=full_price_cents,
            milestone_id=milestone_id,
            shift_days=full_shift_days,
            new_due=full_new_due,
        )
    )

    # For small single-option in-envelope changes (0 shift, no smaller version, no swap),
    # Option A alone suffices unless full_shift_days > 0 or estimate.smaller is present.
    has_multi_options = full_shift_days > 0 or estimate.smaller is not None
    if has_multi_options:
        options.append(
            OptionQuote(
                key=OptionKey.B,
                label=(
                    "Full app in the next phase"
                    if "app" in ask_title.lower()
                    else f"{ask_title} in the next phase"
                ),
                description=f"{estimate.full.title or ask_title} scheduled in the next phase",
                hours=confirmed_hours,
                price_cents=full_price_cents,
                milestone_id=milestone_id,
                shift_days=0,
                new_due=milestone_due,
            )
        )

    # Option C: Smaller version
    if estimate.smaller is not None:
        sm_hours = (
            smaller_confirmed_hours
            if smaller_confirmed_hours is not None
            else estimate.smaller.p50_hours
        )
        sm_price_cents = compute_price_cents(sm_hours, estimate.smaller.confidence, rate_card)
        sm_shift_days = compute_shift_days(sm_hours, plan.capacity_hours_per_week)
        sm_new_due = (
            shift_due_date(milestone_due, sm_shift_days)
            if milestone_due and sm_shift_days > 0
            else milestone_due
        )
        short_name = _short_smaller_name(estimate.smaller.title)
        c_label = f"{short_name} by {smaller_due_hint}" if smaller_due_hint else short_name
        options.append(
            OptionQuote(
                key=OptionKey.C,
                label=c_label,
                description=estimate.smaller.title or short_name,
                hours=sm_hours,
                price_cents=sm_price_cents,
                milestone_id=milestone_id,
                shift_days=sm_shift_days,
                new_due=sm_new_due,
            )
        )

    # Option D: Swap candidate
    effective_smaller = estimate.smaller
    if effective_smaller is not None and smaller_confirmed_hours is not None:
        effective_smaller = EstimateVersion(
            title=effective_smaller.title,
            p50_hours=smaller_confirmed_hours,
            p90_hours=effective_smaller.p90_hours,
            confidence=effective_smaller.confidence,
        )

    swap = find_swap_for_estimate(
        confirmed_hours=confirmed_hours,
        smaller=effective_smaller,
        plan=plan,
        swap_policy=swap_policy,
    )
    if swap is not None:
        swap_in_name = (
            _short_smaller_name(swap.smaller_title)
            if swap.using_smaller
            else (estimate.full.title or ask_title)
        )
        removed_desc = " and ".join(_lower_article_title(item.title) for item in swap.items)
        d_label = f"{swap_in_name} instead of {removed_desc}"
        options.append(
            OptionQuote(
                key=OptionKey.D,
                label=d_label,
                description=f"{d_label}: no extra cost, no date change",
                hours=swap.target_hours,
                price_cents=0,
                milestone_id=swap.milestone_id,
                shift_days=0,
                new_due=milestone_due,
                swap_out=swap.item_ids,
                swap_in=swap.smaller_title or swap_in_name,
            )
        )

    return options
