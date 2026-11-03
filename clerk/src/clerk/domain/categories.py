"""Ask classification pre-checks, token overlap, and post-rules (warranty, exclusions)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from clerk.domain.models import (
    Category,
    ClassificationResult,
    DecisionRecord,
    Plan,
    PlanItem,
    ScopeMapConfig,
)

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "to",
        "on",
        "in",
        "for",
        "of",
        "and",
        "or",
        "please",
        "can",
        "could",
        "would",
        "we",
        "you",
        "our",
        "add",
        "make",
        "get",
        "have",
        "want",
        "need",
        "with",
        "by",
        "is",
        "are",
        "it",
        "too",
        "from",
        "into",
        "that",
        "this",
    }
)


def _stem_token(token: str) -> str:
    """Apply lightweight plural normalization for scope/plan matching."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def normalize_tokens(text: str) -> set[str]:
    """Extract normalized content tokens from a title or ask quote."""
    raw_words = re.findall(r"[a-z0-9]+", text.lower())
    tokens: set[str] = set()
    for word in raw_words:
        if word in _STOPWORDS:
            continue
        # Ignore standalone version markers such as 'v1', 'v2'
        if re.match(r"^v\d+$", word):
            continue
        tokens.add(_stem_token(word))
    return tokens


def token_overlap(item_title: str, ask_quote: str) -> float:
    """Compute normalized token overlap between a plan item title and an ask quote.

    Uses the maximum of Jaccard similarity and title-containment ratio (when the
    item title has at least 2 content tokens), so concise item titles like
    'CSV export' or 'Report filters v2' match longer natural-language asks like
    'Please add CSV export to the reports page' with overlap >= 0.6.
    """
    title_tokens = normalize_tokens(item_title)
    quote_tokens = normalize_tokens(ask_quote)
    if not title_tokens or not quote_tokens:
        return 0.0

    intersection = len(title_tokens & quote_tokens)
    if intersection == 0:
        return 0.0

    union = len(title_tokens | quote_tokens)
    jaccard = intersection / union
    if len(title_tokens) >= 2:
        containment = intersection / len(title_tokens)
        return max(jaccard, containment)
    return jaccard


@dataclass(frozen=True)
class PreCheckHints:
    """Candidate matches from deterministic pre-checks passed into LLM classification."""

    duplicate_candidates: list[tuple[PlanItem, float]]
    contradicted_decisions: list[DecisionRecord]


def find_duplicate_candidates(
    quote: str,
    plan: Plan,
    threshold: float = 0.6,
) -> list[tuple[PlanItem, float]]:
    """Find open, planned, or done plan items with normalized token overlap >= threshold."""
    matches: list[tuple[PlanItem, float]] = []
    for milestone in plan.milestones:
        for item in milestone.items:
            score = token_overlap(item.title, quote)
            if score >= threshold:
                matches.append((item, score))
    matches.sort(key=lambda pair: (-pair[1], pair[0].id))
    return matches


def find_contradicted_decisions(
    quote: str,
    decisions: Sequence[DecisionRecord],
) -> list[DecisionRecord]:
    """Identify recorded decisions that the ask quote potentially contradicts.

    Detects negated terms in decisions (e.g. 'no SMS', 'SSO is deferred') that appear
    in the ask quote.
    """
    quote_lower = quote.lower()
    quote_tokens = set(re.findall(r"[a-z0-9]+", quote_lower))
    contradicted: list[DecisionRecord] = []

    for dec in decisions:
        dec_lower = dec.text.lower()
        # Look for explicit negative clauses like "no <term>" or "<term> is deferred"
        negated_terms = set(re.findall(r"\bno\s+([a-z0-9_-]+)", dec_lower))
        negated_terms.update(
            re.findall(r"\b([a-z0-9_-]+)\s+is\s+deferred", dec_lower)
        )
        negated_terms.update(
            re.findall(r"\bwithout\s+([a-z0-9_-]+)", dec_lower)
        )
        stemmed_negated = {_stem_token(t) for t in negated_terms} | negated_terms
        stemmed_quote = {_stem_token(t) for t in quote_tokens} | quote_tokens

        if stemmed_negated & stemmed_quote:
            contradicted.append(dec)

    return contradicted


def run_pre_checks(
    quote: str,
    plan: Plan,
    decisions: Sequence[DecisionRecord],
    duplicate_threshold: float = 0.6,
) -> PreCheckHints:
    """Run deterministic pre-checks before LLM classification."""
    return PreCheckHints(
        duplicate_candidates=find_duplicate_candidates(
            quote, plan, threshold=duplicate_threshold
        ),
        contradicted_decisions=find_contradicted_decisions(quote, decisions),
    )


def check_defect_warranty(
    *,
    clause_ids: Sequence[str],
    related_item_id: str | None,
    scope_map: ScopeMapConfig,
    plan: Plan,
    current_date: date,
) -> tuple[bool, str, Category]:
    """Verify whether a DEFECT classification satisfies the SOW warranty rules.

    Rule (Section 7):
    `DEFECT` needs a related deliverable where at least one linked plan item
    (or the specific `related_item`) has `status == "done"` and
    `(current_date - done_on).days <= warranty_days`.

    Returns:
        (passed, reason, fallback_category_if_failed)
    """
    items_by_id: dict[str, PlanItem] = {}
    items_by_deliverable: dict[str, list[PlanItem]] = {}
    for milestone in plan.milestones:
        for item in milestone.items:
            items_by_id[item.id] = item
            items_by_deliverable.setdefault(item.deliverable, []).append(item)

    # 1. If a specific PlanItem ID was named in related_item
    if related_item_id and related_item_id in items_by_id:
        target_item = items_by_id[related_item_id]
        if target_item.status != "done" or not target_item.done_on:
            return (
                False,
                f"Related item {target_item.id} has status '{target_item.status}' (not done)",
                Category.IN_SCOPE,
            )
        done_date = date.fromisoformat(target_item.done_on)
        age_days = (current_date - done_date).days
        if 0 <= age_days <= scope_map.warranty_days:
            return (
                True,
                (
                    f"Item {target_item.id} completed {age_days} days ago "
                    f"(within {scope_map.warranty_days}d warranty)"
                ),
                Category.DEFECT,
            )
        return (
            False,
            (
                f"Warranty expired for item {target_item.id}: completed {age_days} days ago "
                f"(> {scope_map.warranty_days}d)"
            ),
            Category.OUT_OF_SCOPE,
        )

    # 2. Resolve deliverables from clause_ids (or related_item if it's a deliverable ID like 'D3')
    matched_deliverables: list[str] = []
    if related_item_id and related_item_id in items_by_deliverable:
        matched_deliverables.append(related_item_id)
    for deliv in scope_map.deliverables:
        if deliv.clause in clause_ids and deliv.id not in matched_deliverables:
            matched_deliverables.append(deliv.id)

    if not matched_deliverables:
        return (
            False,
            "No related SOW deliverable found for DEFECT classification",
            Category.OUT_OF_SCOPE,
        )

    linked_items: list[PlanItem] = []
    for deliv_id in matched_deliverables:
        linked_items.extend(items_by_deliverable.get(deliv_id, []))

    if not linked_items:
        return (
            False,
            f"Deliverable(s) {', '.join(matched_deliverables)} have no linked plan items",
            Category.IN_SCOPE,
        )

    done_items = [it for it in linked_items if it.status == "done" and it.done_on]
    if not done_items:
        return (
            False,
            f"Deliverable(s) {', '.join(matched_deliverables)} have no completed plan items yet",
            Category.IN_SCOPE,
        )

    for item in done_items:
        assert item.done_on is not None
        done_date = date.fromisoformat(item.done_on)
        age_days = (current_date - done_date).days
        if 0 <= age_days <= scope_map.warranty_days:
            return (
                True,
                (
                    f"Deliverable {item.deliverable} item {item.id} completed {age_days}d ago "
                    f"(within {scope_map.warranty_days}d warranty)"
                ),
                Category.DEFECT,
            )

    return (
        False,
        (
            f"All completed items for deliverable(s) {', '.join(matched_deliverables)} "
            f"are past the {scope_map.warranty_days}-day warranty"
        ),
        Category.OUT_OF_SCOPE,
    )


def apply_post_rules(
    result: ClassificationResult,
    scope_map: ScopeMapConfig,
    plan: Plan,
    current_date: date,
) -> tuple[ClassificationResult, list[str]]:
    """Apply deterministic post-rules after LLM classification.

    Post-rules (Section 7):
      1. An exclusion always beats an inclusion.
      2. `DEFECT` needs a related deliverable where at least one linked plan item
         (or the specific `related_item`) has `status == "done"` and
         `(current_date - done_on).days <= warranty_days`; otherwise reclassify and log why.
      3. Confidence below 0.7 becomes `UNCLEAR`.
    """
    notes: list[str] = []
    updated = result.model_copy(deep=True)

    exclusion_clauses = {excl.clause for excl in scope_map.exclusions}
    cited_exclusions = [c for c in updated.clause_ids if c in exclusion_clauses]

    # Rule 1: An exclusion always beats an inclusion
    if cited_exclusions and updated.category != Category.OUT_OF_SCOPE:
        old_cat: Category = updated.category
        updated.category = Category.OUT_OF_SCOPE
        # Put exclusion clauses first
        other_clauses = [c for c in updated.clause_ids if c not in exclusion_clauses]
        updated.clause_ids = cited_exclusions + other_clauses
        note = (
            f"Reclassified {old_cat} -> OUT_OF_SCOPE because exclusion clause(s) "
            f"{', '.join(cited_exclusions)} beat inclusions."
        )
        notes.append(note)
        updated.reason = f"{updated.reason} ({note})"[:200]

    # Rule 2: DEFECT warranty verification
    if updated.category == Category.DEFECT:
        passed, reason, fallback_cat = check_defect_warranty(
            clause_ids=updated.clause_ids,
            related_item_id=updated.related_item,
            scope_map=scope_map,
            plan=plan,
            current_date=current_date,
        )
        if not passed:
            old_cat = updated.category
            updated.category = fallback_cat
            note = f"Reclassified {old_cat} -> {fallback_cat}: {reason}"
            notes.append(note)
            updated.reason = reason

    # Rule 3: Confidence below 0.7 becomes UNCLEAR
    if updated.confidence < 0.7 and updated.category != Category.UNCLEAR:
        old_cat = updated.category
        updated.category = Category.UNCLEAR
        note = (
            f"Reclassified {old_cat} -> UNCLEAR because confidence "
            f"{updated.confidence:.2f} < 0.70"
        )
        notes.append(note)
        if not updated.question:
            updated.question = (
                "Could you clarify how you would like us to handle this request?"
            )
        if not updated.choices:
            updated.choices = [
                "Use the existing in-scope capability",
                "Quote as a separate change request",
            ]

    return updated, notes
