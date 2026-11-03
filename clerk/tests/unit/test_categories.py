"""Unit tests for pre-checks, post-classification rules, and warranty validation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from clerk.domain.categories import (
    apply_post_rules,
    check_defect_warranty,
    find_contradicted_decisions,
    find_duplicate_candidates,
    normalize_tokens,
    run_pre_checks,
    token_overlap,
)
from clerk.domain.models import (
    Category,
    ClassificationResult,
    Plan,
    ScopeMapConfig,
    SeedLedgerConfig,
)
from clerk.settings import load_yaml_file


def test_normalize_tokens_and_overlap() -> None:
    """Verify stopword filtering, plural normalization, and token overlap scoring."""
    tokens = normalize_tokens("Please add CSV exports to the reports page v2")
    assert "csv" in tokens
    assert "export" in tokens
    assert "report" in tokens
    assert "v2" not in tokens
    assert "the" not in tokens

    score = token_overlap(
        "CSV export",
        "Please add CSV export to the reports page",
    )
    assert score == 1.0
    assert token_overlap("", "CSV export") == 0.0
    assert token_overlap("Single", "Unrelated words here") == 0.0
    assert token_overlap("Single", "Single word match here") > 0.0


def test_find_duplicate_candidates_and_pre_checks(
    plan: Plan,
    seed_ledger: SeedLedgerConfig,
) -> None:
    """Verify duplicate pre-check finds I8, I9, I10 (>= 0.6) and contradicted decisions."""
    c_i8 = find_duplicate_candidates("Please add CSV export to the reports page", plan)
    assert any(item.id == "I8" for item, _ in c_i8)

    c_i9 = find_duplicate_candidates("Add an admin analytics dashboard", plan)
    assert any(item.id == "I9" for item, _ in c_i9)

    c_i10 = find_duplicate_candidates("Add a filter by region on the reports page", plan)
    assert any(item.id == "I10" for item, _ in c_i10)

    hints = run_pre_checks(
        "Can you send SMS alerts and add CSV export?",
        plan=plan,
        decisions=seed_ledger.decisions,
    )
    assert any(item.id == "I8" for item, _ in hints.duplicate_candidates)
    assert any(dec.id == "DEC-002" for dec in hints.contradicted_decisions)


def test_find_contradicted_decisions(seed_ledger: SeedLedgerConfig) -> None:
    """Verify already-decided pre-check matches DEC-002 (no SMS) and DEC-001 (SSO is deferred)."""
    sms_matches = find_contradicted_decisions(
        "Can we have SMS for password resets?",
        decisions=seed_ledger.decisions,
    )
    assert any(c.id == "DEC-002" for c in sms_matches)

    sso_matches = find_contradicted_decisions(
        "Can we enable SSO login for staff?",
        decisions=seed_ledger.decisions,
    )
    assert any(c.id == "DEC-001" for c in sso_matches)


def test_post_rule_defect_warranty_passes_on_d3_despite_unstarted_i10(
    scope_map: ScopeMapConfig,
    plan: Plan,
) -> None:
    """Regression: D3 (clause 3.2) has done items I2/I8 plus unstarted I10.

    Warranty must pass on clause '3.2' (D3) because I2 and I8 were completed
    within 30 days of 2026-11-05.
    """
    raw = ClassificationResult(
        category=Category.DEFECT,
        clause_ids=["3.2"],
        related_item=None,
        confidence=0.92,
        reason="The CSV export has the wrong date column.",
    )
    refined, notes = apply_post_rules(
        raw,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 11, 5),
    )
    assert refined.category == Category.DEFECT
    assert refined.clause_ids == ["3.2"]
    assert notes == []


def test_post_rule_defect_warranty_downgrades_when_item_unstarted_or_expired(
    scope_map: ScopeMapConfig,
    plan: Plan,
) -> None:
    """Verify DEFECT is reclassified when item is unstarted or outside 30-day warranty."""
    # 1. Explicitly pointing to unstarted item I9 -> reclassifies to IN_SCOPE
    raw_unstarted = ClassificationResult(
        category=Category.DEFECT,
        clause_ids=["4.1"],
        related_item="I9",
        confidence=0.90,
        reason="Analytics chart bug.",
    )
    refined_unstarted, notes_1 = apply_post_rules(
        raw_unstarted,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 11, 5),
    )
    assert refined_unstarted.category == Category.IN_SCOPE
    assert len(notes_1) == 1

    # 2. Deliverable D4 (clause 4.1) has only I9 (unstarted) -> reclassifies to IN_SCOPE
    raw_d4 = ClassificationResult(
        category=Category.DEFECT,
        clause_ids=["4.1"],
        confidence=0.90,
        reason="Admin analytics dashboard issue.",
    )
    refined_d4, _ = apply_post_rules(
        raw_d4,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 11, 5),
    )
    assert refined_d4.category == Category.IN_SCOPE

    # 3. Deliverable D2 (clause 2.4) has no linked plan items -> reclassifies to IN_SCOPE
    passed_d2, _, fallback_d2 = check_defect_warranty(
        clause_ids=["2.4"],
        related_item_id=None,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 11, 5),
    )
    assert passed_d2 is False
    assert fallback_d2 == Category.IN_SCOPE

    # 4. Completed item I1 (done 2026-10-20) checked on 2026-12-01 (> 30d warranty)
    raw_expired = ClassificationResult(
        category=Category.DEFECT,
        clause_ids=["1.1"],
        related_item="I1",
        confidence=0.95,
        reason="Login button issue.",
    )
    refined_expired, _ = apply_post_rules(
        raw_expired,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 12, 1),
    )
    assert refined_expired.category == Category.OUT_OF_SCOPE

    # 5. Deliverable D1 (clause 1.1) checked without related_item after warranty expiry
    raw_deliv_expired = ClassificationResult(
        category=Category.DEFECT,
        clause_ids=["1.1"],
        confidence=0.95,
        reason="Responsive layout issue after warranty.",
    )
    refined_deliv_exp, _ = apply_post_rules(
        raw_deliv_expired,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 12, 1),
    )
    assert refined_deliv_exp.category == Category.OUT_OF_SCOPE

    # 6. No matching deliverable clause -> OUT_OF_SCOPE
    raw_no_clause = ClassificationResult(
        category=Category.DEFECT,
        clause_ids=[],
        confidence=0.90,
        reason="Unknown defect.",
    )
    refined_no_clause, _ = apply_post_rules(
        raw_no_clause,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 11, 5),
    )
    assert refined_no_clause.category == Category.OUT_OF_SCOPE


def test_post_rule_exclusion_beats_inclusion(
    scope_map: ScopeMapConfig,
    plan: Plan,
) -> None:
    """If an ask cites an exclusion clause (1.3 or 3.5), it cannot remain IN_SCOPE."""
    raw = ClassificationResult(
        category=Category.IN_SCOPE,
        clause_ids=["1.1", "1.3"],
        confidence=0.88,
        reason="Mobile app view.",
    )
    refined, notes = apply_post_rules(
        raw,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 11, 5),
    )
    assert refined.category == Category.OUT_OF_SCOPE
    assert refined.clause_ids[0] == "1.3"
    assert len(notes) == 1


def test_post_rule_low_confidence_becomes_unclear(
    scope_map: ScopeMapConfig,
    plan: Plan,
) -> None:
    """Confidence < 0.7 must become UNCLEAR with a clarifying question and choices."""
    raw = ClassificationResult(
        category=Category.IN_SCOPE,
        clause_ids=["3.2"],
        confidence=0.55,
        reason="Unclear analytics export format.",
    )
    refined, notes = apply_post_rules(
        raw,
        scope_map=scope_map,
        plan=plan,
        current_date=date(2026, 11, 5),
    )
    assert refined.category == Category.UNCLEAR
    assert refined.question is not None
    assert len(refined.choices) >= 2
    assert len(notes) == 1


def test_all_twenty_fixture_asks_pass_post_rules(
    repo_root: Path,
    scope_map: ScopeMapConfig,
    plan: Plan,
) -> None:
    """Every ask in tests/fixtures/asks.yaml preserves its expected category and clause."""
    fixtures_path = repo_root / "clerk" / "tests" / "fixtures" / "asks.yaml"
    data = load_yaml_file(fixtures_path)
    asks_list = data["asks"]
    assert len(asks_list) == 20

    for entry in asks_list:
        expected_cat = Category(entry["expected_category"])
        expected_clauses = entry.get("expected_clauses", [])
        expected_item = entry.get("expected_related_item")
        expected_dec = entry.get("expected_decision_id")

        raw = ClassificationResult(
            category=expected_cat,
            clause_ids=list(expected_clauses),
            related_item=expected_item,
            decision_id=expected_dec,
            confidence=0.92,
            reason=f"Classification for ask #{entry['id']}",
            question="Which option do you prefer?" if expected_cat == Category.UNCLEAR else None,
            choices=["Basic", "Full"] if expected_cat == Category.UNCLEAR else [],
        )
        refined, _ = apply_post_rules(
            raw,
            scope_map=scope_map,
            plan=plan,
            current_date=date(2026, 11, 5),
        )
        assert refined.category == expected_cat, f"Failed on ask #{entry['id']}"
        for cl in expected_clauses:
            assert cl in refined.clause_ids, f"Missing clause {cl} on ask #{entry['id']}"
