"""RenewalService grouping out-of-scope asks by theme with hours summed in code."""

from __future__ import annotations

from typing import Any

from clerk.adapters.llm_scripted import RenewalGroupingOutput
from clerk.db.repositories import LedgerRepository
from clerk.domain.models import Category
from clerk.domain.templates import render_renewal_report
from clerk.ports.protocols import LLMPort


class RenewalService:
    """Service that builds the next-phase renewal proposal from out-of-scope asks."""

    def __init__(self, repo: LedgerRepository, llm: LLMPort) -> None:
        self._repo = repo
        self._llm = llm

    async def generate_report(self) -> str:
        """Group out-of-scope asks into themes and sum their estimated hours in code."""
        oos_asks = self._repo.list_asks(category=Category.OUT_OF_SCOPE)
        if not oos_asks:
            return render_renewal_report([])

        crs_by_ask = {cr.ask_id: cr for cr in self._repo.list_change_requests()}
        hours_by_ask: dict[str, int] = {}
        ask_lines: list[str] = []
        for ask in oos_asks:
            cr = crs_by_ask.get(ask.id)
            hrs = 0
            if cr is not None:
                if cr.confirmed_hours is not None:
                    hrs = cr.confirmed_hours
                elif cr.estimate is not None:
                    hrs = cr.estimate.full.p50_hours
            hours_by_ask[ask.id] = hrs
            ask_lines.append(f"- {ask.id}: {ask.quote} ({hrs}h)")

        # Also include any swapped-out plan items so they can be proposed for Phase 2
        swaps = self._repo.list_swaps()
        for sw in swaps:
            for item_id in sw.removed_item_ids:
                hours_by_ask[item_id] = sw.hours_removed
                ask_lines.append(
                    f"- {item_id}: Swapped-out plan item from {sw.cr_id} ({sw.hours_removed}h)"
                )

        user_prompt = "Group these out-of-scope items into at most 5 themes:\n" + "\n".join(
            ask_lines
        )
        try:
            grouping = await self._llm.json(
                "Group out-of-scope asks into at most 5 renewal themes.",
                user_prompt,
                RenewalGroupingOutput,
            )
            raw_themes = grouping.themes
        except Exception:
            raw_themes = []

        if not raw_themes:
            all_ids = list(hours_by_ask.keys())
            themes_payload: list[dict[str, Any]] = [
                {
                    "name": "Phase 2 Scope Additions & Deferred Items",
                    "member_ids": all_ids,
                    "total_hours": sum(hours_by_ask.values()),
                }
            ]
            return render_renewal_report(themes_payload)

        themes_out: list[dict[str, Any]] = []
        covered: set[str] = set()
        for t in raw_themes[:5]:
            valid_ids = [mid for mid in t.member_ids if mid in hours_by_ask]
            if not valid_ids:
                continue
            covered.update(valid_ids)
            themes_out.append(
                {
                    "name": t.name,
                    "member_ids": valid_ids,
                    "total_hours": sum(hours_by_ask[mid] for mid in valid_ids),
                }
            )

        remaining = [k for k in hours_by_ask if k not in covered]
        if remaining:
            themes_out.append(
                {
                    "name": "Additional Deferred Scope",
                    "member_ids": remaining,
                    "total_hours": sum(hours_by_ask[mid] for mid in remaining),
                }
            )

        return render_renewal_report(themes_out)
