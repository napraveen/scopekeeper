"""Parsers for acme-intake messages, Estimator JSON blocks, @clerk commands, and Builder."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from clerk.domain.models import (
    Confidence,
    Estimate,
    EstimateVersion,
    OptionKey,
    SimilarMerge,
)

EXPECTED_INTAKE_FORMAT = (
    "Expected one of:\n"
    '  ASK | "<exact quote>" | requester=<name> | link=<url>\n'
    '  ANSWER Q-NNNN | "<quote>" | link=<url>\n'
    "  DECISION CR-NNN <A|B|C|D|DECLINE> | link=<url>\n"
    "  ACCEPT ASK-NNNN | link=<url>\n"
    '  DISPUTE ASK-NNNN | "<quote>" | link=<url>\n'
    "  DRAFT ASK-NNNN: <text>"
)

EXPECTED_ESTIMATE_FORMAT = (
    "Expected a fenced code block tagged `scopekeeper-estimate` containing JSON:\n"
    "```scopekeeper-estimate\n"
    '{"cr_id": "CR-NNN", "full": {"p50_hours": 10, "p90_hours": 14, "confidence": "high"}, ...}\n'
    "```"
)

EXPECTED_CLERK_COMMAND_FORMAT = (
    "Expected a valid @clerk command:\n"
    "  @clerk confirm\n"
    "  @clerk hours <N>  (or: @clerk hours smaller <N>)\n"
    "  @clerk approve  (or: @clerk approve A,C,D)\n"
    "  @clerk price <A|B|C|D> <amount>\n"
    "  @clerk goodwill <ASK-NNNN>\n"
    "  @clerk decline <CR-NNN> <reason>\n"
    "  @clerk ledger | @clerk invoice <month> | @clerk renewal | @clerk status [CR-NNN]\n"
    "  @clerk what did we agree about <topic>?\n"
    "  @clerk flip now | @clerk morning now | @clerk clock +<N>h"
)


class ParseError(ValueError):
    """Raised when an incoming agent or human message does not match expected protocol syntax."""

    def __init__(self, message: str, *, expected_format: str) -> None:
        super().__init__(f"{message}\n{expected_format}")
        self.reason = message
        self.expected_format = expected_format


# ── Parsed Message Dataclasses ────────────────────────────────────────────────


@dataclass(frozen=True)
class IntakeAskMessage:
    """Scout -> Clerk: ASK | "<quote>" | requester=<name> | link=<url>"""

    quote: str
    requester: str
    link: str


@dataclass(frozen=True)
class IntakeAnswerMessage:
    """Scout -> Clerk: ANSWER Q-0001 | "<quote>" | link=<url>"""

    question_id: str
    quote: str
    link: str


@dataclass(frozen=True)
class IntakeDecisionMessage:
    """Scout -> Clerk: DECISION CR-004 D | link=<url>"""

    cr_id: str
    choice: OptionKey | Literal["DECLINE"]
    link: str


@dataclass(frozen=True)
class IntakeAcceptMessage:
    """Scout -> Clerk: ACCEPT ASK-0008 | link=<url>"""

    ask_id: str
    link: str


@dataclass(frozen=True)
class IntakeDisputeMessage:
    """Scout -> Clerk: DISPUTE ASK-0009 | "<quote>" | link=<url>"""

    ask_id: str
    quote: str
    link: str


@dataclass(frozen=True)
class IntakeDraftMessage:
    """Scout -> Clerk (copilot mode): DRAFT ASK-0007: <text>"""

    ask_id: str
    text: str


IntakeMessage = (
    IntakeAskMessage
    | IntakeAnswerMessage
    | IntakeDecisionMessage
    | IntakeAcceptMessage
    | IntakeDisputeMessage
    | IntakeDraftMessage
)


@dataclass(frozen=True)
class ClerkReadyMessage:
    """Clerk -> Scout: READY ASK-0007\\n<text>"""

    target_id: str
    text: str


@dataclass(frozen=True)
class ClerkQuestionMessage:
    """Clerk -> Scout: QUESTION Q-0001 for ASK-0009\\n<text>\\nChoices: ..."""

    question_id: str
    ask_id: str
    text: str
    choices: list[str]


@dataclass(frozen=True)
class ClerkModeMessage:
    """Clerk -> Scout: MODE autopilot until ... or MODE copilot"""

    mode: Literal["autopilot", "copilot"]
    until_note: str | None = None


ClerkToScoutMessage = ClerkReadyMessage | ClerkQuestionMessage | ClerkModeMessage


@dataclass(frozen=True)
class ParsedEstimatorReply:
    """Estimator -> Clerk: scopekeeper-estimate JSON payload."""

    cr_id: str
    estimate: Estimate


@dataclass(frozen=True)
class BuilderDoneMessage:
    """Builder -> Clerk: @clerk DONE W-0003 pr=<url>"""

    work_id: str
    pr_url: str


# ── People's @clerk Commands ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ConfirmCommand:
    """@clerk confirm [CR-NNN]"""

    cr_id: str | None = None


@dataclass(frozen=True)
class HoursCommand:
    """@clerk hours [smaller] <N>"""

    hours: int
    version: Literal["full", "smaller"] = "full"
    cr_id: str | None = None


@dataclass(frozen=True)
class ApproveCommand:
    """@clerk approve [A,C,D]"""

    options: list[OptionKey] | None = None
    cr_id: str | None = None


@dataclass(frozen=True)
class PriceOverrideCommand:
    """@clerk price <A|B|C|D> <usd>"""

    option: OptionKey
    price_usd: Decimal
    cr_id: str | None = None


@dataclass(frozen=True)
class GoodwillCommand:
    """@clerk goodwill ASK-NNNN [reason]"""

    ask_id: str
    reason: str | None = None


@dataclass(frozen=True)
class DeclineCommand:
    """@clerk decline CR-NNN <reason>"""

    cr_id: str | None
    reason: str


@dataclass(frozen=True)
class LedgerCommand:
    """@clerk ledger [month]"""

    month: str | None = None


@dataclass(frozen=True)
class InvoiceCommand:
    """@clerk invoice <month>"""

    month: str


@dataclass(frozen=True)
class RenewalCommand:
    """@clerk renewal"""


@dataclass(frozen=True)
class StatusCommand:
    """@clerk status [CR-NNN | ASK-NNNN]"""

    target_id: str | None = None


@dataclass(frozen=True)
class MemoryQueryCommand:
    """@clerk what did we agree about <topic>?"""

    topic: str


@dataclass(frozen=True)
class DemoControlCommand:
    """@clerk flip now | @clerk morning now | @clerk clock +10h"""

    action: Literal["flip_now", "morning_now", "clock"]
    offset: str | None = None


ClerkCommand = (
    ConfirmCommand
    | HoursCommand
    | ApproveCommand
    | PriceOverrideCommand
    | GoodwillCommand
    | DeclineCommand
    | LedgerCommand
    | InvoiceCommand
    | RenewalCommand
    | StatusCommand
    | MemoryQueryCommand
    | DemoControlCommand
)


# ── Helper Strippers ──────────────────────────────────────────────────────────


def _strip_code_fences(text: str) -> str:
    """Remove surrounding markdown code fences and leading @mentions if present."""
    cleaned = text.strip()
    fence_match = re.match(r"^```[a-zA-Z0-9_-]*\s*\n(.*?)\n```\s*$", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    elif cleaned.startswith("`") and cleaned.endswith("`") and "\n" not in cleaned:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _unquote(val: str) -> str:
    """Strip surrounding straight or curly quotes and whitespace."""
    s = val.strip()
    if len(s) >= 2 and (
        (s[0] == '"' and s[-1] == '"')
        or (s[0] == "'" and s[-1] == "'")
        or (s[0] == "\u201c" and s[-1] == "\u201d")
    ):
        return s[1:-1].strip()
    return s


def _clean_url(val: str) -> str:
    """Extract clean URL from `link=<url>` or `<https://...>`."""
    s = val.strip()
    if s.lower().startswith("link="):
        s = s[5:].strip()
    s = _unquote(s)
    if s.startswith("<") and s.endswith(">"):
        s = s[1:-1].strip()
    return s


def _normalize_id(raw_id: str, prefix: str) -> str:
    """Normalize an ID like 'ask-0007' or 'cr-004' to uppercase canonical form."""
    cleaned = raw_id.strip().upper()
    if not cleaned.startswith(prefix.upper()):
        raise ValueError(f"Expected {prefix} ID, got {raw_id!r}")
    return cleaned


# ── acme-intake Parser (Scout -> Clerk) ───────────────────────────────────────


def parse_intake_message(text: str) -> IntakeMessage:
    """Parse a single Scout -> Clerk protocol line in acme-intake."""
    cleaned = _strip_code_fences(text)
    # Strip optional leading @clerk mention
    cleaned = re.sub(r"^@(?:acme-)?clerk[:\s,]*", "", cleaned, flags=re.IGNORECASE).strip()

    if not cleaned:
        raise ParseError("Empty intake message.", expected_format=EXPECTED_INTAKE_FORMAT)

    # 1. Check DRAFT ASK-NNNN: <text>
    draft_match = re.match(
        r"^DRAFT\s+(?:\|\s*)?(ASK-\d+)\s*(?:[:|])\s*(.+)$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if draft_match:
        ask_id = draft_match.group(1).upper()
        draft_text = _unquote(draft_match.group(2))
        if not draft_text:
            raise ParseError("DRAFT message text is empty.", expected_format=EXPECTED_INTAKE_FORMAT)
        return IntakeDraftMessage(ask_id=ask_id, text=draft_text)

    parts = [p.strip() for p in cleaned.split("|")]
    head = parts[0]
    head_tokens = head.split()
    if not head_tokens:
        raise ParseError(
            f"Unrecognized intake command in {text!r}.",
            expected_format=EXPECTED_INTAKE_FORMAT,
        )

    verb = head_tokens[0].upper()

    if verb == "ASK":
        # ASK | "<quote>" | requester=<name> | link=<url>
        if len(parts) < 3:
            raise ParseError(
                "ASK requires quote, requester=<name>, and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        quote = _unquote(parts[1])
        requester = ""
        link = ""
        for p in parts[2:]:
            if re.match(r"^requester\s*=", p, flags=re.IGNORECASE):
                requester = _unquote(re.split(r"=", p, maxsplit=1)[1])
            elif re.match(r"^link\s*=", p, flags=re.IGNORECASE) or p.startswith("http"):
                link = _clean_url(re.split(r"=", p, maxsplit=1)[1] if "=" in p else p)
        if not quote or not requester or not link:
            raise ParseError(
                "ASK must include non-empty quote, requester=<name>, and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        return IntakeAskMessage(quote=quote, requester=requester, link=link)

    if verb == "ANSWER":
        # ANSWER Q-0001 | "<quote>" | link=<url>  OR  ANSWER | Q-0001 | "<quote>" | link=<url>
        if len(head_tokens) >= 2:
            q_id = _normalize_id(head_tokens[1], "Q-")
            rem_parts = parts[1:]
        elif len(parts) >= 4:
            q_id = _normalize_id(parts[1], "Q-")
            rem_parts = parts[2:]
        else:
            raise ParseError(
                "ANSWER requires question ID (Q-NNNN), quote, and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        if len(rem_parts) < 2:
            raise ParseError(
                "ANSWER requires both an answer quote and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        quote = _unquote(rem_parts[0])
        link = ""
        for p in rem_parts[1:]:
            if re.match(r"^link\s*=", p, flags=re.IGNORECASE) or p.startswith("http"):
                link = _clean_url(re.split(r"=", p, maxsplit=1)[1] if "=" in p else p)
        if not quote or not link:
            raise ParseError(
                "ANSWER quote and link=<url> must be non-empty.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        return IntakeAnswerMessage(question_id=q_id, quote=quote, link=link)

    if verb == "DECISION":
        # DECISION CR-004 D | link=<url>  OR  DECISION | CR-004 | D | link=<url>
        if len(head_tokens) >= 3:
            cr_id = _normalize_id(head_tokens[1], "CR-")
            raw_choice = " ".join(head_tokens[2:])
            rem_parts = parts[1:]
        elif len(head_tokens) == 2 and len(parts) >= 3:
            cr_id = _normalize_id(head_tokens[1], "CR-")
            raw_choice = parts[1]
            rem_parts = parts[2:]
        elif len(parts) >= 4:
            cr_id = _normalize_id(parts[1], "CR-")
            raw_choice = parts[2]
            rem_parts = parts[3:]
        else:
            raise ParseError(
                "DECISION requires CR-NNN, choice (A/B/C/D/DECLINE), and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        choice_norm = _unquote(raw_choice).upper()
        if choice_norm in {"NOT NOW", "DECLINE", "DECLINED", "NO"}:
            choice: OptionKey | Literal["DECLINE"] = "DECLINE"
        elif choice_norm in {"A", "B", "C", "D"}:
            choice = OptionKey(choice_norm)
        else:
            raise ParseError(
                f"Invalid DECISION choice {raw_choice!r}; expected A, B, C, D, or DECLINE.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        link = ""
        for p in rem_parts:
            if re.match(r"^link\s*=", p, flags=re.IGNORECASE) or p.startswith("http"):
                link = _clean_url(re.split(r"=", p, maxsplit=1)[1] if "=" in p else p)
        if not link:
            raise ParseError(
                "DECISION requires link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        return IntakeDecisionMessage(cr_id=cr_id, choice=choice, link=link)

    if verb == "ACCEPT":
        # ACCEPT ASK-0008 | link=<url>
        if len(head_tokens) >= 2:
            ask_id = _normalize_id(head_tokens[1], "ASK-")
            rem_parts = parts[1:]
        elif len(parts) >= 3:
            ask_id = _normalize_id(parts[1], "ASK-")
            rem_parts = parts[2:]
        else:
            raise ParseError(
                "ACCEPT requires ASK-NNNN and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        link = ""
        for p in rem_parts:
            if re.match(r"^link\s*=", p, flags=re.IGNORECASE) or p.startswith("http"):
                link = _clean_url(re.split(r"=", p, maxsplit=1)[1] if "=" in p else p)
        if not link:
            raise ParseError(
                "ACCEPT requires link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        return IntakeAcceptMessage(ask_id=ask_id, link=link)

    if verb == "DISPUTE":
        # DISPUTE ASK-0009 | "<quote>" | link=<url>
        if len(head_tokens) >= 2:
            ask_id = _normalize_id(head_tokens[1], "ASK-")
            rem_parts = parts[1:]
        elif len(parts) >= 4:
            ask_id = _normalize_id(parts[1], "ASK-")
            rem_parts = parts[2:]
        else:
            raise ParseError(
                "DISPUTE requires ASK-NNNN, quote, and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        if len(rem_parts) < 2:
            raise ParseError(
                "DISPUTE requires quote and link=<url>.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        quote = _unquote(rem_parts[0])
        link = ""
        for p in rem_parts[1:]:
            if re.match(r"^link\s*=", p, flags=re.IGNORECASE) or p.startswith("http"):
                link = _clean_url(re.split(r"=", p, maxsplit=1)[1] if "=" in p else p)
        if not quote or not link:
            raise ParseError(
                "DISPUTE quote and link=<url> must be non-empty.",
                expected_format=EXPECTED_INTAKE_FORMAT,
            )
        return IntakeDisputeMessage(ask_id=ask_id, quote=quote, link=link)

    raise ParseError(
        f"Unrecognized acme-intake command {verb!r}.",
        expected_format=EXPECTED_INTAKE_FORMAT,
    )


def parse_intake_messages(text: str) -> list[IntakeMessage]:
    """Parse one or more Scout -> Clerk protocol lines in a single chat message."""
    cleaned = _strip_code_fences(text)
    lines = [
        line.strip()
        for line in cleaned.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        raise ParseError("Empty intake message.", expected_format=EXPECTED_INTAKE_FORMAT)

    # If the first line is DRAFT, the draft text may span multiple lines
    if re.match(r"^(?:@(?:acme-)?clerk[:\s,]*)?DRAFT\b", lines[0], flags=re.IGNORECASE):
        return [parse_intake_message(cleaned)]

    return [parse_intake_message(line) for line in lines]


# ── Clerk -> Scout Parser (for builtin Scout & contract tests) ────────────────


def parse_clerk_to_scout_message(text: str) -> ClerkToScoutMessage:
    """Parse a message sent by Clerk to Scout in acme-intake."""
    cleaned = _strip_code_fences(text)
    cleaned = re.sub(r"^@(?:acme-)?scout[:\s,]*", "", cleaned, flags=re.IGNORECASE).strip()

    mode_match = re.match(
        r"^MODE\s+(autopilot|copilot)(?:\s+until\s+(.+))?$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if mode_match:
        mode_val: Literal["autopilot", "copilot"] = (
            "autopilot" if mode_match.group(1).lower() == "autopilot" else "copilot"
        )
        until_note = mode_match.group(2).strip() if mode_match.group(2) else None
        return ClerkModeMessage(mode=mode_val, until_note=until_note)

    ready_match = re.match(
        r"^READY\s+((?:ASK|CR)-\d+)\s*\n(.+)$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if ready_match:
        return ClerkReadyMessage(
            target_id=ready_match.group(1).upper(),
            text=ready_match.group(2).strip(),
        )

    q_match = re.match(
        r"^QUESTION\s+(Q-\d+)\s+for\s+(ASK-\d+)\s*\n(.+)$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if q_match:
        q_id = q_match.group(1).upper()
        ask_id = q_match.group(2).upper()
        body = q_match.group(3).strip()
        choices: list[str] = []
        q_lines: list[str] = []
        for line in body.splitlines():
            if line.strip().lower().startswith("choices:"):
                raw_choices = line.strip()[len("choices:") :].strip()
                parts = re.split(r"\s*\d+\)\s*", raw_choices)
                choices = [p.strip() for p in parts if p.strip()]
            else:
                q_lines.append(line.strip())
        return ClerkQuestionMessage(
            question_id=q_id,
            ask_id=ask_id,
            text="\n".join(q_lines).strip(),
            choices=choices,
        )

    raise ParseError(
        f"Unrecognized Clerk->Scout message: {text!r}",
        expected_format="Expected READY, QUESTION, or MODE command.",
    )


# ── Estimator Reply Parser ────────────────────────────────────────────────────


def parse_estimator_reply(text: str, posted_at: str = "") -> ParsedEstimatorReply:
    """Parse the Estimator's `scopekeeper-estimate` fenced JSON block."""
    match = re.search(
        r"```scopekeeper-estimate\s*\n(.*?)\n```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        # Fallback: tolerate ```json block if it contains cr_id and full
        match = re.search(
            r"```(?:json)?\s*\n(\{.*?\"cr_id\".*?\})\s*\n```",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if not match:
        raise ParseError(
            "Missing `scopekeeper-estimate` fenced JSON block.",
            expected_format=EXPECTED_ESTIMATE_FORMAT,
        )

    raw_json = match.group(1).strip()
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ParseError(
            f"Invalid JSON in `scopekeeper-estimate` block: {exc}",
            expected_format=EXPECTED_ESTIMATE_FORMAT,
        ) from exc

    if not isinstance(data, dict) or "cr_id" not in data or "full" not in data:
        raise ParseError(
            "Estimate JSON must contain 'cr_id' and 'full'.",
            expected_format=EXPECTED_ESTIMATE_FORMAT,
        )

    try:
        cr_id = _normalize_id(str(data["cr_id"]), "CR-")
        full_raw = data["full"]
        full = EstimateVersion(
            title=full_raw.get("title"),
            p50_hours=int(full_raw["p50_hours"]),
            p90_hours=int(full_raw["p90_hours"]),
            confidence=Confidence(str(full_raw["confidence"]).lower()),
        )
        smaller: EstimateVersion | None = None
        if data.get("smaller"):
            sm_raw = data["smaller"]
            smaller = EstimateVersion(
                title=sm_raw.get("title"),
                p50_hours=int(sm_raw["p50_hours"]),
                p90_hours=int(sm_raw["p90_hours"]),
                confidence=Confidence(str(sm_raw["confidence"]).lower()),
            )
        similar = [
            SimilarMerge(ref=str(s["ref"]), hours=int(s["hours"])) for s in data.get("similar", [])
        ]
        estimate = Estimate(
            full=full,
            smaller=smaller,
            touches=[str(t) for t in data.get("touches", [])],
            similar=similar,
            risks=[str(r) for r in data.get("risks", [])],
            assumptions=[str(a) for a in data.get("assumptions", [])],
            posted_at=posted_at or str(data.get("posted_at", "")),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ParseError(
            f"Malformed estimate fields: {exc}",
            expected_format=EXPECTED_ESTIMATE_FORMAT,
        ) from exc

    return ParsedEstimatorReply(cr_id=cr_id, estimate=estimate)


# ── Builder Reply Parser ──────────────────────────────────────────────────────


def parse_builder_done(text: str) -> BuilderDoneMessage:
    """Parse Builder completion message: `@clerk DONE W-0003 pr=<url>`."""
    cleaned = _strip_code_fences(text)
    match = re.search(
        r"\bDONE\s+(W-\d+)\s+pr\s*=\s*([^\s>]+>?)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ParseError(
            "Could not parse Builder DONE message.",
            expected_format="Expected: @clerk DONE W-NNNN pr=<url>",
        )
    work_id = match.group(1).upper()
    pr_url = _clean_url(match.group(2))
    return BuilderDoneMessage(work_id=work_id, pr_url=pr_url)


# ── People's @clerk Commands Parser ───────────────────────────────────────────

_MONTH_NAMES: dict[str, str] = {
    "january": "01",
    "jan": "01",
    "february": "02",
    "feb": "02",
    "march": "03",
    "mar": "03",
    "april": "04",
    "apr": "04",
    "may": "05",
    "june": "06",
    "jun": "06",
    "july": "07",
    "jul": "07",
    "august": "08",
    "aug": "08",
    "september": "09",
    "sep": "09",
    "sept": "09",
    "october": "10",
    "oct": "10",
    "november": "11",
    "nov": "11",
    "december": "12",
    "dec": "12",
}


def _normalize_month(raw_month: str, default_year: int = 2026) -> str:
    """Convert 'november' or '2026-11' into 'YYYY-MM'."""
    cleaned = raw_month.strip().lower()
    if re.match(r"^\d{4}-\d{2}$", cleaned):
        return cleaned
    if cleaned in _MONTH_NAMES:
        return f"{default_year}-{_MONTH_NAMES[cleaned]}"
    raise ValueError(f"Unrecognized month {raw_month!r}")


def parse_clerk_command(
    text: str, default_cr_id: str | None = None, default_year: int = 2026
) -> ClerkCommand:
    """Parse an internal human command addressed to @clerk."""
    cleaned = _strip_code_fences(text)
    # Strip leading @clerk or clerk:
    cleaned = re.sub(
        r"^(?:@(?:acme-)?clerk|clerk)\b[:\s,]*", "", cleaned, flags=re.IGNORECASE
    ).strip()

    if not cleaned:
        raise ParseError("Empty @clerk command.", expected_format=EXPECTED_CLERK_COMMAND_FORMAT)

    # 1. Demo controls
    if re.match(r"^flip\s+now\b", cleaned, flags=re.IGNORECASE):
        return DemoControlCommand(action="flip_now")
    if re.match(r"^morning\s+now\b", cleaned, flags=re.IGNORECASE):
        return DemoControlCommand(action="morning_now")
    clock_match = re.match(r"^clock\s+(.+)$", cleaned, flags=re.IGNORECASE)
    if clock_match:
        return DemoControlCommand(action="clock", offset=clock_match.group(1).strip())

    # 2. Memory query: "what did we agree about <topic>?"
    mem_match = re.match(
        r"^what\s+did\s+we\s+agree\s+(?:about|on)\s+(.+?)\??\s*$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if mem_match:
        return MemoryQueryCommand(topic=mem_match.group(1).strip().rstrip("?"))

    # 3. @clerk confirm [CR-NNN]
    confirm_match = re.match(r"^confirm(?:\s+(CR-\d+))?\s*$", cleaned, flags=re.IGNORECASE)
    if confirm_match:
        cr_id = confirm_match.group(1).upper() if confirm_match.group(1) else default_cr_id
        return ConfirmCommand(cr_id=cr_id)

    # 4. @clerk hours [CR-NNN] [smaller] <N>
    hours_match = re.match(
        r"^hours(?:\s+(CR-\d+))?(?:\s+(smaller|full))?\s+(\d+)(?:\s*h(?:ours?)?)?\s*$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if hours_match:
        cr_id = hours_match.group(1).upper() if hours_match.group(1) else default_cr_id
        ver_raw = (hours_match.group(2) or "full").lower()
        ver: Literal["full", "smaller"] = "smaller" if ver_raw == "smaller" else "full"
        hrs = int(hours_match.group(3))
        if hrs <= 0:
            raise ParseError(
                "Confirmed hours must be positive.",
                expected_format=EXPECTED_CLERK_COMMAND_FORMAT,
            )
        return HoursCommand(hours=hrs, version=ver, cr_id=cr_id)

    # 5. @clerk approve [CR-NNN] [A,C,D]
    approve_match = re.match(
        r"^approve(?:\s+(CR-\d+))?(?:\s+([A-Da-d,\s]+))?\s*$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if approve_match:
        cr_id = approve_match.group(1).upper() if approve_match.group(1) else default_cr_id
        opts_raw = approve_match.group(2)
        if not opts_raw:
            return ApproveCommand(options=None, cr_id=cr_id)
        tokens = [t.strip().upper() for t in re.split(r"[,\s]+", opts_raw) if t.strip()]
        options: list[OptionKey] = []
        for tok in tokens:
            if tok not in {"A", "B", "C", "D"}:
                raise ParseError(
                    f"Invalid option key {tok!r} in approve command.",
                    expected_format=EXPECTED_CLERK_COMMAND_FORMAT,
                )
            key = OptionKey(tok)
            if key not in options:
                options.append(key)
        return ApproveCommand(options=options, cr_id=cr_id)

    # 6. @clerk price [CR-NNN] <A|B|C|D> <amount>
    price_match = re.match(
        r"^price(?:\s+(CR-\d+))?\s+([A-Da-d])\s+\$?([0-9,]+(?:\.\d{1,2})?)\s*$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if price_match:
        cr_id = price_match.group(1).upper() if price_match.group(1) else default_cr_id
        opt = OptionKey(price_match.group(2).upper())
        raw_amt = price_match.group(3).replace(",", "")
        try:
            amt = Decimal(raw_amt)
        except InvalidOperation as exc:
            raise ParseError(
                f"Invalid price amount {price_match.group(3)!r}.",
                expected_format=EXPECTED_CLERK_COMMAND_FORMAT,
            ) from exc
        return PriceOverrideCommand(option=opt, price_usd=amt, cr_id=cr_id)

    # 7. @clerk goodwill <ASK-NNNN> [reason]
    gw_match = re.match(r"^goodwill\s+(ASK-\d+)(?:\s+(.+))?\s*$", cleaned, flags=re.IGNORECASE)
    if gw_match:
        ask_id = gw_match.group(1).upper()
        reason = gw_match.group(2).strip() if gw_match.group(2) else None
        return GoodwillCommand(ask_id=ask_id, reason=reason)

    # 8. @clerk decline [CR-NNN] <reason>
    dec_match = re.match(r"^decline(?:\s+(CR-\d+))?\s+(.+)$", cleaned, flags=re.IGNORECASE)
    if dec_match:
        cr_id = dec_match.group(1).upper() if dec_match.group(1) else default_cr_id
        reason = dec_match.group(2).strip()
        return DeclineCommand(cr_id=cr_id, reason=reason)

    # 9. Read-only queries: ledger, invoice, renewal, status
    ledger_match = re.match(r"^ledger(?:\s+(\S+))?\s*$", cleaned, flags=re.IGNORECASE)
    if ledger_match:
        m_arg = ledger_match.group(1)
        month = _normalize_month(m_arg, default_year) if m_arg else None
        return LedgerCommand(month=month)

    inv_match = re.match(r"^invoice\s+(\S+)\s*$", cleaned, flags=re.IGNORECASE)
    if inv_match:
        try:
            month = _normalize_month(inv_match.group(1), default_year)
        except ValueError as exc:
            raise ParseError(str(exc), expected_format=EXPECTED_CLERK_COMMAND_FORMAT) from exc
        return InvoiceCommand(month=month)

    if re.match(r"^renewal\s*$", cleaned, flags=re.IGNORECASE):
        return RenewalCommand()

    status_match = re.match(r"^status(?:\s+((?:CR|ASK)-\d+))?\s*$", cleaned, flags=re.IGNORECASE)
    if status_match:
        target = status_match.group(1).upper() if status_match.group(1) else default_cr_id
        return StatusCommand(target_id=target)

    raise ParseError(
        f"Could not parse @clerk command: {text!r}",
        expected_format=EXPECTED_CLERK_COMMAND_FORMAT,
    )
