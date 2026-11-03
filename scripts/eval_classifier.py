"""Evaluate ClassifierService on the 20 fixture asks in clerk/tests/fixtures/asks.yaml.

Prints individual ask verdicts, overall accuracy, and an ASCII confusion matrix.
Usage:
    python scripts/eval_classifier.py [--provider scripted|gemini|anthropic|openai]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
CLERK_SRC = REPO_ROOT / "clerk" / "src"
if str(CLERK_SRC) not in sys.path:
    sys.path.insert(0, str(CLERK_SRC))

from clerk.adapters.llm_providers import create_llm_adapter  # noqa: E402
from clerk.adapters.llm_scripted import ScriptedLLM  # noqa: E402
from clerk.domain.models import Category  # noqa: E402
from clerk.ports.protocols import LLMPort  # noqa: E402
from clerk.services.classifier import ClassifierService  # noqa: E402
from clerk.settings import load_all_configs  # noqa: E402

CATEGORIES: list[str] = [c.value for c in Category]


def print_confusion_matrix(matrix: dict[str, dict[str, int]]) -> None:
    """Print an ASCII confusion matrix of expected vs actual categories."""
    col_width = 15
    header = "Expected \\ Pred".ljust(18) + "".join(c[:12].rjust(col_width) for c in CATEGORIES)
    print("\n" + "=" * len(header))
    print("CONFUSION MATRIX")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for exp in CATEGORIES:
        row = exp[:16].ljust(18)
        for pred in CATEGORIES:
            cnt = matrix[exp][pred]
            cell = str(cnt) if cnt > 0 else "."
            row += cell.rjust(col_width)
        print(row)
    print("=" * len(header) + "\n")


async def run_evaluation(provider_name: str = "scripted") -> int:
    """Run classification across all 20 asks and return process exit code (0 if >= 17/20)."""
    configs = load_all_configs(REPO_ROOT / "config")
    fixtures_path = REPO_ROOT / "clerk" / "tests" / "fixtures" / "asks.yaml"

    yaml_parser = YAML(typ="safe")
    fixture_data = yaml_parser.load(fixtures_path.read_text(encoding="utf-8"))
    asks = fixture_data.get("asks", [])

    llm: LLMPort
    if provider_name == "scripted":
        llm = ScriptedLLM()
    else:
        llm = create_llm_adapter(provider=provider_name)

    classifier = ClassifierService(llm=llm, scope_map=configs.scope_map)
    today = date(2026, 11, 5)

    print(f"\nEvaluating ClassifierService with provider: {provider_name.upper()}")
    print(f"Loaded {len(asks)} asks from {fixtures_path.name}\n")
    print(f"{'#':<4} {'Status':<8} {'Expected':<18} {'Actual':<18} {'Quote'}")
    print("-" * 80)

    correct_count = 0
    confusion_matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for ask in asks:
        ask_id = ask["id"]
        quote = ask["quote"]
        expected_cat = ask["expected_category"]

        result, _ = await classifier.classify(
            quote=quote,
            plan=configs.plan,
            decisions=configs.seed_ledger.decisions,
            current_date=today,
        )

        actual_cat = result.category.value
        confusion_matrix[expected_cat][actual_cat] += 1

        is_match = actual_cat == expected_cat
        if is_match:
            correct_count += 1
            status_badge = "PASS"
        else:
            status_badge = "FAIL"

        print(f"{ask_id:<4} {status_badge:<8} {expected_cat:<18} {actual_cat:<18} {quote[:45]}")

    total = len(asks)
    accuracy = (correct_count / total) * 100 if total > 0 else 0.0

    print_confusion_matrix(confusion_matrix)
    print(f"Total Asks: {total}")
    print(f"Correct:    {correct_count} / {total} ({accuracy:.1f}%)")
    target_met = correct_count >= 17

    if target_met:
        print(f"RESULT: SUCCESS (Target >= 17 of 20 met: {correct_count}/{total})\n")
        return 0
    else:
        print(f"RESULT: FAILED (Target >= 17 of 20 not met: {correct_count}/{total})\n")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ScopeKeeper classifier accuracy")
    parser.add_argument(
        "--provider",
        choices=["scripted", "gemini", "anthropic", "openai"],
        default=os.environ.get("LLM_PROVIDER", "scripted"),
        help="LLM provider to test (default: scripted)",
    )
    args = parser.parse_args()
    code = asyncio.run(run_evaluation(provider_name=args.provider))
    sys.exit(code)


if __name__ == "__main__":
    main()
