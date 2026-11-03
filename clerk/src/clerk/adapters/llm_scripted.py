"""Deterministic offline ScriptedLLM adapter implementing LLMPort."""

from __future__ import annotations

import hashlib
import re
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from clerk.domain.models import Category, ClassificationResult

TModel = TypeVar("TModel", bound=BaseModel)


class RenewalThemeSpec(BaseModel):
    """Single theme grouping out-of-scope asks for renewal reporting."""

    name: str
    member_ids: list[str] = Field(default_factory=list)


class RenewalGroupingOutput(BaseModel):
    """Structured LLM output for grouping out-of-scope asks into renewal themes."""

    themes: list[RenewalThemeSpec] = Field(default_factory=list)


class ScoutSplitOutput(BaseModel):
    """Structured LLM output for splitting a multi-ask client message."""

    asks: list[str] = Field(default_factory=list)


def _extract_quoted_ask(user_prompt: str) -> str:
    """Extract the primary ask quote from a ClassifierService user prompt."""
    match = re.search(r"Quoted Ask:\s*\"?(.*?)\"?(?:\n|$)", user_prompt, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('"')
    return user_prompt.strip()


class ScriptedLLM:
    """Offline deterministic LLMPort implementation for tests and offline demos."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._custom_json: dict[str, BaseModel] = {}
        self._custom_text: dict[str, str] = {}

    def register_json(self, substring_key: str, response: BaseModel) -> None:
        """Register a custom Pydantic model response when `substring_key` appears in `user`."""
        self._custom_json[substring_key.lower()] = response

    def register_text(self, substring_key: str, response: str) -> None:
        """Register a custom text response when `substring_key` appears in `user`."""
        self._custom_text[substring_key.lower()] = response

    async def json(self, system: str, user: str, schema: type[TModel]) -> TModel:
        """Return a deterministic Pydantic model instance matching `schema`."""
        cache_key = hashlib.sha256(f"{schema.__name__}::{system}::{user}".encode()).hexdigest()
        if cache_key in self._cache:
            cached: TModel = self._cache[cache_key]
            return cached.model_copy(deep=True)

        user_lower = user.lower()
        for key, custom_val in self._custom_json.items():
            if key in user_lower and isinstance(custom_val, schema):
                self._cache[cache_key] = custom_val
                return custom_val.model_copy(deep=True)

        if schema is ClassificationResult:
            res = self._classify_ask(user)
            typed_res: TModel = schema.model_validate(res.model_dump())
            self._cache[cache_key] = typed_res
            return typed_res.model_copy(deep=True)

        if schema is RenewalGroupingOutput:
            ask_ids = re.findall(r"\bASK-\d+\b", user)
            themes = [
                RenewalThemeSpec(
                    name="Mobile, Reporting & Integrations",
                    member_ids=sorted(set(ask_ids)),
                )
            ]
            grouped = RenewalGroupingOutput(themes=themes)
            typed_group: TModel = schema.model_validate(grouped.model_dump())
            self._cache[cache_key] = typed_group
            return typed_group.model_copy(deep=True)

        if schema is ScoutSplitOutput:
            split_res = self._split_client_message(user)
            typed_split: TModel = schema.model_validate(split_res.model_dump())
            self._cache[cache_key] = typed_split
            return typed_split.model_copy(deep=True)

        # Generic fallback via empty/default validation
        fallback: TModel = schema.model_validate({})
        self._cache[cache_key] = fallback
        return fallback

    async def text(self, system: str, user: str, max_words: int = 120) -> str:
        """Return deterministic concise text matching the facts in `user`."""
        user_lower = user.lower()
        for key, custom_str in self._custom_text.items():
            if key in user_lower:
                return custom_str
        words = user.strip().split()
        return " ".join(words[:max_words])

    def _split_client_message(self, user: str) -> ScoutSplitOutput:
        """Deterministically split the canonical overnight Sam message or single asks."""
        lower = user.lower()
        if "dark mode" in lower and "excel" in lower and "android" in lower and "safari" in lower:
            return ScoutSplitOutput(
                asks=[
                    "The login button is broken on Safari",
                    "Can you add dark mode",
                    "Export reports to Excel",
                    "We need an Android app for the board meeting on the 20th",
                ]
            )
        return ScoutSplitOutput(asks=[user.strip()])

    def _classify_ask(self, user_prompt: str) -> ClassificationResult:
        """Deterministic rule-table covering the overnight story and all 20 evaluation asks."""
        quote = _extract_quoted_ask(user_prompt)
        q_lower = quote.lower()
        has_answer = "client answer:" in user_prompt.lower()

        # If client answered clarifying question for Excel (.xlsx)
        if has_answer and ("excel" in q_lower or "xlsx" in user_prompt.lower()):
            return ClassificationResult(
                category=Category.OUT_OF_SCOPE,
                clause_ids=["3.2"],
                confidence=0.95,
                reason=(
                    "Clause 3.2 includes CSV export only; "
                    "native .xlsx workbook requires a change order."
                ),
            )

        # 1. ALREADY_DECIDED (SMS)
        if "sms" in q_lower:
            return ClassificationResult(
                category=Category.ALREADY_DECIDED,
                clause_ids=[],
                decision_id="DEC-002",
                confidence=0.96,
                reason="Contradicts DEC-002 (Notifications are email-only; no SMS).",
            )

        # 2. DUPLICATE (I8, I9, I10)
        if "filter by region" in q_lower or "report filters v2" in q_lower:
            return ClassificationResult(
                category=Category.DUPLICATE,
                clause_ids=["3.2"],
                related_item="I10",
                confidence=0.94,
                reason="Already planned in item I10 (Report filters v2).",
            )
        if "admin analytics dashboard" in q_lower:
            return ClassificationResult(
                category=Category.DUPLICATE,
                clause_ids=["4.1"],
                related_item="I9",
                confidence=0.95,
                reason="Already planned in item I9 (Admin analytics dashboard).",
            )
        if (
            "add csv export" in q_lower or "csv export to the reports" in q_lower
        ) and "wrong" not in q_lower:
            return ClassificationResult(
                category=Category.DUPLICATE,
                clause_ids=["3.2"],
                related_item="I8",
                confidence=0.95,
                reason="Already delivered in item I8 (CSV export).",
            )

        # 3. DEFECT (1.1 and 3.2)
        if "safari" in q_lower or "firefox mobile" in q_lower:
            return ClassificationResult(
                category=Category.DEFECT,
                clause_ids=["1.1"],
                related_item="I1",
                confidence=0.96,
                reason="Browser defect in responsive layout/login under Clause 1.1 warranty.",
            )
        if "wrong date column" in q_lower or "crashes when i pick last year" in q_lower:
            return ClassificationResult(
                category=Category.DEFECT,
                clause_ids=["3.2"],
                related_item="I8" if "csv" in q_lower else "I2",
                confidence=0.94,
                reason="Reports page defect within 30-day warranty of Clause 3.2.",
            )

        # 4. IN_SCOPE (2.4 Theming)
        if (
            "dark mode" in q_lower
            or "dark theme" in q_lower
            or "brand colours" in q_lower
            or "brand typeface" in q_lower
        ):
            return ClassificationResult(
                category=Category.IN_SCOPE,
                clause_ids=["2.4"],
                confidence=0.95,
                reason=(
                    "Covered by Clause 2.4 "
                    "(Theming: light/dark theme, brand colours, typeface)."
                ),
            )

        # 5. UNCLEAR (Excel, PDF, load faster)
        if "excel" in q_lower:
            return ClassificationResult(
                category=Category.UNCLEAR,
                clause_ids=["3.2"],
                confidence=0.82,
                reason=(
                    "Clause 3.2 covers CSV export; "
                    "unclear if CSV-for-Excel or native .xlsx is needed."
                ),
                question=(
                    "Do you need a native .xlsx workbook, "
                    "or is a CSV export that opens in Excel enough?"
                ),
                choices=[
                    "CSV export that opens in Excel (in scope)",
                    "Native .xlsx workbook (change request)",
                ],
            )
        if "pdf export" in q_lower:
            return ClassificationResult(
                category=Category.UNCLEAR,
                clause_ids=["3.2"],
                confidence=0.80,
                reason=(
                    "Clause 3.2 covers CSV export; "
                    "PDF export format/layout needs clarification."
                ),
                question=(
                    "Do you want browser print-to-PDF styling "
                    "or server-generated PDF reports?"
                ),
                choices=["Browser print stylesheet", "Server-generated PDF files"],
            )
        if "load faster" in q_lower:
            return ClassificationResult(
                category=Category.UNCLEAR,
                clause_ids=[],
                confidence=0.78,
                reason="Performance target and specific page are unspecified.",
                question="Which page feels slow, and what load time target do you have in mind?",
                choices=["Reports page with large date range", "Initial login and home screen"],
            )

        # 6. OUT_OF_SCOPE (1.3 Native mobile, 3.5 BI integrations, or unmapped)
        if "android" in q_lower or "iphone" in q_lower or "ios" in q_lower:
            return ClassificationResult(
                category=Category.OUT_OF_SCOPE,
                clause_ids=["1.3"],
                confidence=0.97,
                reason="Clause 1.3 explicitly excludes native iOS and Android apps.",
            )
        if "power bi" in q_lower or "tableau" in q_lower or "looker" in q_lower:
            return ClassificationResult(
                category=Category.OUT_OF_SCOPE,
                clause_ids=["3.5"],
                confidence=0.96,
                reason="Clause 3.5 excludes third-party BI integrations.",
            )

        return ClassificationResult(
            category=Category.OUT_OF_SCOPE,
            clause_ids=[],
            confidence=0.92,
            reason="Not covered by any deliverable in the signed Statement of Work.",
        )
