"""Guard verifying that every number, money amount, and date in LLM text appears in facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

_MONTH_TO_INT: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_MONTH_PATTERN = "|".join(
    sorted(_MONTH_TO_INT.keys(), key=len, reverse=True)
)


@dataclass(frozen=True)
class NumbersCheckResult:
    """Result of checking generated text against structured facts."""

    passed: bool
    unexpected_tokens: list[str]


def _normalize_decimal_str(raw: str) -> str:
    """Normalize a numeric string (e.g., '10,350.00' -> '10350', '1.1' -> '1.1')."""
    cleaned = raw.replace(",", "").strip()
    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        return cleaned
    if dec == dec.to_integral_value():
        return str(int(dec))
    return str(dec.normalize())


def _extract_from_string(
    text: str,
) -> tuple[set[str], set[tuple[int, int]], set[str]]:
    """Extract (money_amounts, month_day_dates, bare_numbers) from a string."""
    # Remove URLs first so port numbers or paths in URLs aren't misread as facts
    scrubbed = re.sub(r"https?://\S+", " ", text)
    # Remove canonical entity IDs like ASK-0007, CR-004, Q-0001, W-0001, DEC-002, I9, M2, D1
    scrubbed = re.sub(
        r"\b(?:ASK|CR|Q|W|DEC|GW)-\d+\b", " ", scrubbed, flags=re.IGNORECASE
    )
    scrubbed = re.sub(r"\b[IMD]\d+\b", " ", scrubbed)

    money_set: set[str] = set()
    date_set: set[tuple[int, int]] = set()
    number_set: set[str] = set()

    # 1. Extract money amounts ($10,350 or $140.50)
    def _consume_money(match: re.Match[str]) -> str:
        amt = _normalize_decimal_str(match.group(1))
        money_set.add(amt)
        return " "

    scrubbed = re.sub(
        r"\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.([0-9]{1,2}))?",
        lambda m: _consume_money(m),
        scrubbed,
    )

    # 2. Extract ISO dates (YYYY-MM-DD)
    def _consume_iso_date(match: re.Match[str]) -> str:
        try:
            d = date.fromisoformat(match.group(0))
            date_set.add((d.month, d.day))
        except ValueError:
            pass
        return " "

    scrubbed = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", _consume_iso_date, scrubbed)

    # 3. Extract Month-Name Day dates (e.g. 'December 12', 'Nov 20th')
    def _consume_named_date(match: re.Match[str]) -> str:
        m_name = match.group(1).lower()
        day_num = int(match.group(2))
        month_num = _MONTH_TO_INT.get(m_name)
        if month_num and 1 <= day_num <= 31:
            date_set.add((month_num, day_num))
        return " "

    scrubbed = re.sub(
        rf"\b({_MONTH_PATTERN})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
        _consume_named_date,
        scrubbed,
        flags=re.IGNORECASE,
    )

    # Strip numbered list / choice markers like '1)', '2)', '1.' at start of line
    scrubbed = re.sub(r"(?:^|\s)\d+\)", " ", scrubbed)
    scrubbed = re.sub(r"(?m)^\s*\d+\.\s+", " ", scrubbed)

    # 4. Extract remaining numbers & clause identifiers (e.g. '1.1', '3', '200', '10,350')
    for match in re.finditer(
        r"\b([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)(?:st|nd|rd|th)?\b",
        scrubbed,
    ):
        raw_num = match.group(1)
        # Keep exact dotted clause IDs like '1.1' or '3.2' as well as normalized form
        cleaned = raw_num.replace(",", "")
        number_set.add(cleaned)
        number_set.add(_normalize_decimal_str(cleaned))

    return money_set, date_set, number_set


def _collect_allowed_from_facts(
    facts: Any,
    money_allowed: set[str],
    date_allowed: set[tuple[int, int]],
    number_allowed: set[str],
    *,
    parent_key: str = "",
) -> None:
    """Recursively populate allowed money amounts, dates, and numbers from `facts`."""
    if facts is None or isinstance(facts, bool):
        return

    if isinstance(facts, (int, float, Decimal)):
        norm = _normalize_decimal_str(str(facts))
        number_allowed.add(norm)
        number_allowed.add(str(facts))
        if parent_key.lower().endswith("cents"):
            dollars = _normalize_decimal_str(str(Decimal(str(facts)) / Decimal("100")))
            money_allowed.add(dollars)
            number_allowed.add(dollars)
        else:
            money_allowed.add(norm)
        return

    if isinstance(facts, date):
        date_allowed.add((facts.month, facts.day))
        number_allowed.add(str(facts.day))
        return

    if isinstance(facts, str):
        m_set, d_set, n_set = _extract_from_string(facts)
        money_allowed.update(m_set)
        date_allowed.update(d_set)
        number_allowed.update(n_set)
        # Any bare number in facts can also be formatted as money if it represents a price
        money_allowed.update(n_set)
        # Any date day in facts can also be written as a bare day ordinal (e.g. 'the 20th')
        for _m, day in d_set:
            number_allowed.add(str(day))
        return

    if isinstance(facts, dict):
        for k, v in facts.items():
            _collect_allowed_from_facts(
                v,
                money_allowed,
                date_allowed,
                number_allowed,
                parent_key=str(k),
            )
        return

    if isinstance(facts, (list, tuple, set)):
        seq = list(facts)
        number_allowed.add(str(len(seq)))
        for item in seq:
            _collect_allowed_from_facts(
                item,
                money_allowed,
                date_allowed,
                number_allowed,
                parent_key=parent_key,
            )


def check_numbers(text: str, facts: dict[str, Any] | list[Any]) -> NumbersCheckResult:
    """Verify that every money amount, date, and number in `text` appears in `facts`.

    Returns `NumbersCheckResult(passed=True, unexpected_tokens=[])` if valid, or
    lists every unverified token so the caller can retry once and then fall back
    to a deterministic template.
    """
    money_allowed: set[str] = set()
    date_allowed: set[tuple[int, int]] = set()
    number_allowed: set[str] = set()

    _collect_allowed_from_facts(facts, money_allowed, date_allowed, number_allowed)

    text_money, text_dates, text_numbers = _extract_from_string(text)
    unexpected: list[str] = []

    for amt in sorted(text_money):
        if amt not in money_allowed and amt not in number_allowed:
            unexpected.append(f"${amt}")

    for m_num, d_num in sorted(text_dates):
        if (m_num, d_num) not in date_allowed:
            unexpected.append(f"{m_num:02d}-{d_num:02d}")

    for num in sorted(text_numbers):
        if num not in number_allowed and num not in money_allowed:
            unexpected.append(num)

    return NumbersCheckResult(passed=len(unexpected) == 0, unexpected_tokens=unexpected)
