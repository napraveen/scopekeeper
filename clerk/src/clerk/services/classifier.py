"""ClassifierService running deterministic pre-checks, LLM classification, and post-rules."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from clerk.domain.categories import apply_post_rules, run_pre_checks
from clerk.domain.models import (
    Category,
    ClassificationResult,
    DecisionRecord,
    Plan,
    ScopeMapConfig,
)
from clerk.ports.protocols import LLMPort

CLASSIFIER_SYSTEM_PROMPT = (
    "You classify one client request against a signed scope of work for a software agency. "
    "Return JSON only, matching the schema.\n"
    "Categories:\n"
    "- DEFECT: something the contract promised does not work as specified.\n"
    "- IN_SCOPE: matches a deliverable or inclusion in the scope map.\n"
    "- DUPLICATE: already delivered, planned or in progress; give the item id.\n"
    "- UNCLEAR: a clause partly matches and the request could be read either way.\n"
    "- OUT_OF_SCOPE: matches an exclusion, or no deliverable covers it.\n"
    "- ALREADY_DECIDED: contradicts a recorded decision; give the decision id.\n"
    "Rules: an exclusion beats an inclusion. Cite clause ids exactly as given. "
    "Never invent clauses, items or decisions. If unsure, choose UNCLEAR and write "
    "one question with 2 or 3 short choices."
)


class ClassifierService:
    """Service that classifies client asks against the SOW, plan, and decision log."""

    def __init__(self, llm: LLMPort, scope_map: ScopeMapConfig) -> None:
        self._llm = llm
        self._scope_map = scope_map

    def _build_user_prompt(
        self,
        *,
        quote: str,
        plan: Plan,
        decisions: Sequence[DecisionRecord],
        dup_ids: list[str],
        contradicted_ids: list[str],
        client_answer: str | None = None,
    ) -> str:
        deliv_lines = [
            f"- {d.id} (Clause {d.clause}): {d.title} | includes: {', '.join(d.includes)}"
            for d in self._scope_map.deliverables
        ]
        excl_lines = [f"- Clause {e.clause}: {e.text}" for e in self._scope_map.exclusions]
        item_lines = [
            (
                f"- {it.id}: {it.title} "
                f"(deliverable={it.deliverable}, status={it.status}, done_on={it.done_on})"
            )
            for ms in plan.milestones
            for it in ms.items
        ]
        dec_lines = [f"- {d.id} ({d.date}): {d.text}" for d in decisions]

        parts = [
            "Deliverables:",
            *deliv_lines,
            "Exclusions:",
            *excl_lines,
            "Plan Items:",
            *item_lines,
            "Decisions:",
            *dec_lines,
            f"Pre-check duplicate candidates: {dup_ids}",
            f"Pre-check contradicted decisions: {contradicted_ids}",
            f'Quoted Ask: "{quote}"',
        ]
        if client_answer:
            parts.append(f'Client Answer: "{client_answer}"')
        return "\n".join(parts)

    async def classify(
        self,
        *,
        quote: str,
        plan: Plan,
        decisions: Sequence[DecisionRecord],
        current_date: date,
        client_answer: str | None = None,
    ) -> tuple[ClassificationResult, list[str]]:
        """Run pre-checks -> LLM classification (with retry + fallback) -> post-rules."""
        hints = run_pre_checks(quote, plan, decisions)
        dup_ids = [item.id for item, _ in hints.duplicate_candidates]
        contradicted_ids = [d.id for d in hints.contradicted_decisions]

        user_prompt = self._build_user_prompt(
            quote=quote,
            plan=plan,
            decisions=decisions,
            dup_ids=dup_ids,
            contradicted_ids=contradicted_ids,
            client_answer=client_answer,
        )

        raw_result: ClassificationResult | None = None
        for attempt in range(2):
            try:
                sys_prompt = (
                    CLASSIFIER_SYSTEM_PROMPT
                    if attempt == 0
                    else CLASSIFIER_SYSTEM_PROMPT
                    + "\nRepair retry: ensure valid JSON matching ClassificationResult."
                )
                raw_result = await self._llm.json(sys_prompt, user_prompt, ClassificationResult)
                break
            except Exception:
                continue

        if raw_result is None:
            raw_result = ClassificationResult(
                category=Category.UNCLEAR,
                clause_ids=[],
                confidence=0.5,
                reason="Automatic fallback due to classification error.",
                question="Could you clarify how you would like us to handle this request?",
                choices=[
                    "Use existing in-scope functionality",
                    "Price as a separate change request",
                ],
            )

        # Enrich missing IDs from pre-check candidates when the category matches
        if (
            raw_result.category == Category.DUPLICATE
            and not raw_result.related_item
            and hints.duplicate_candidates
        ):
            raw_result.related_item = hints.duplicate_candidates[0][0].id
        if (
            raw_result.category == Category.ALREADY_DECIDED
            and not raw_result.decision_id
            and hints.contradicted_decisions
        ):
            raw_result.decision_id = hints.contradicted_decisions[0].id

        return apply_post_rules(
            raw_result,
            scope_map=self._scope_map,
            plan=plan,
            current_date=current_date,
        )
