"""Deterministic scope swap finder for unstarted plan items."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from clerk.domain.models import EstimateVersion, Plan, PlanItem, SwapPolicyConfig


@dataclass(frozen=True)
class SwapCandidate:
    """Best matching unstarted plan item (or pair of items) for a scope swap."""

    items: tuple[PlanItem, ...]
    milestone_id: str
    target_hours: int
    removed_hours: int
    gap_ratio: Decimal
    using_smaller: bool = False
    smaller_title: str | None = None

    @property
    def item_ids(self) -> list[str]:
        """Return the IDs of the plan items to swap out."""
        return [item.id for item in self.items]

    @property
    def removed_titles(self) -> str:
        """Human-readable title(s) of the swapped-out item(s)."""
        return " and ".join(item.title for item in self.items)


def _natural_id_key(item_id: str) -> tuple[str, int]:
    """Extract prefix and integer suffix for natural ID tie-breaking (e.g. 'I9' < 'I10')."""
    match = re.match(r"^([A-Za-z_-]+)(\d+)$", item_id.strip())
    if match:
        return (match.group(1), int(match.group(2)))
    return (item_id, 0)


def find_swap_for_hours(
    target_hours: int,
    plan: Plan,
    swap_policy: SwapPolicyConfig,
    *,
    using_smaller: bool = False,
    smaller_title: str | None = None,
) -> SwapCandidate | None:
    """Find the best single unstarted item (or pair if no single matches) within tolerance.

    Tie-breaking order:
      1. Prefer a single item over a pair.
      2. Smallest relative size gap: |candidate_hours - target_hours| / target_hours <= tolerance.
      3. Lowest priority (i.e. highest priority number, e.g. priority 3 before priority 2).
      4. Lowest item ID (natural order, e.g. I9 before I10).
    """
    if not swap_policy.allowed or target_hours <= 0:
        return None

    target = Decimal(str(target_hours))
    tolerance = swap_policy.tolerance

    # Collect eligible items along with their milestone_id
    eligible: list[tuple[PlanItem, str]] = []
    for milestone in plan.milestones:
        for item in milestone.items:
            if swap_policy.only_unstarted and item.status != "unstarted":
                continue
            if not swap_policy.only_unstarted and item.status == "done":
                continue
            eligible.append((item, milestone.id))

    if not eligible:
        return None

    # 1. Check single items
    single_matches: list[tuple[Decimal, int, tuple[str, int], SwapCandidate]] = []
    for item, milestone_id in eligible:
        gap = abs(Decimal(str(item.hours)) - target) / target
        if gap <= tolerance:
            priority_num = item.priority if item.priority is not None else 0
            cand = SwapCandidate(
                items=(item,),
                milestone_id=milestone_id,
                target_hours=target_hours,
                removed_hours=item.hours,
                gap_ratio=gap,
                using_smaller=using_smaller,
                smaller_title=smaller_title,
            )
            single_matches.append((gap, -priority_num, _natural_id_key(item.id), cand))

    if single_matches:
        single_matches.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
        return single_matches[0][3]

    # 2. Check pairs of distinct items
    pair_matches: list[
        tuple[Decimal, int, int, tuple[str, int], tuple[str, int], SwapCandidate]
    ] = []
    n = len(eligible)
    for i in range(n):
        for j in range(i + 1, n):
            item1, ms1 = eligible[i]
            item2, _ms2 = eligible[j]
            combined_hours = item1.hours + item2.hours
            gap = abs(Decimal(str(combined_hours)) - target) / target
            if gap <= tolerance:
                p1 = item1.priority if item1.priority is not None else 0
                p2 = item2.priority if item2.priority is not None else 0
                cand = SwapCandidate(
                    items=(item1, item2),
                    milestone_id=ms1,
                    target_hours=target_hours,
                    removed_hours=combined_hours,
                    gap_ratio=gap,
                    using_smaller=using_smaller,
                    smaller_title=smaller_title,
                )
                pair_matches.append(
                    (
                        gap,
                        -min(p1, p2),
                        -(p1 + p2),
                        _natural_id_key(item1.id),
                        _natural_id_key(item2.id),
                        cand,
                    )
                )

    if pair_matches:
        pair_matches.sort(
            key=lambda entry: (entry[0], entry[1], entry[2], entry[3], entry[4])
        )
        return pair_matches[0][5]

    return None


def find_swap_for_estimate(
    confirmed_hours: int,
    smaller: EstimateVersion | None,
    plan: Plan,
    swap_policy: SwapPolicyConfig,
) -> SwapCandidate | None:
    """Find a swap candidate against confirmed_hours first, falling back to smaller.p50_hours."""
    primary = find_swap_for_hours(
        confirmed_hours,
        plan,
        swap_policy,
        using_smaller=False,
        smaller_title=None,
    )
    if primary is not None:
        return primary

    if smaller is not None:
        return find_swap_for_hours(
            smaller.p50_hours,
            plan,
            swap_policy,
            using_smaller=True,
            smaller_title=smaller.title,
        )

    return None
