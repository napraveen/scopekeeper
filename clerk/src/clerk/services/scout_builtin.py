"""BuiltinScout fallback agent (never imports clerk.db or clerk.domain.pricing)."""

from __future__ import annotations

from typing import Literal

from clerk.adapters.llm_scripted import ScoutSplitOutput
from clerk.domain.parsing import (
    ClerkModeMessage,
    ClerkQuestionMessage,
    ClerkReadyMessage,
    ParseError,
    parse_clerk_to_scout_message,
)
from clerk.domain.templates import render_acknowledgement, render_handover_greeting
from clerk.ports.protocols import LLMPort


class BuiltinScout:
    """Custom agent fallback for Scout that operates only in acme-client and acme-intake."""

    def __init__(self, llm: LLMPort, agent_name: str = "acme-scout") -> None:
        self._llm = llm
        self._agent_name = agent_name
        self._mode: Literal["autopilot", "copilot"] = "copilot"
        self._last_question_id: str | None = None
        self._last_cr_id: str | None = None
        self._last_preview_ask_id: str | None = None

    @property
    def mode(self) -> Literal["autopilot", "copilot"]:
        """Return Scout's current operating mode."""
        return self._mode

    async def handle_intake_command_from_clerk(
        self, text: str
    ) -> tuple[Literal["assume_role", "release_role", "post_client", "noop"], str | None]:
        """Parse a Clerk -> Scout message in acme-intake and return the client action."""
        try:
            parsed = parse_clerk_to_scout_message(text)
        except ParseError:
            return ("noop", None)

        if isinstance(parsed, ClerkModeMessage):
            self._mode = parsed.mode
            if parsed.mode == "autopilot":
                greeting = render_handover_greeting("Sam", "11 PM", "Priya")
                return ("assume_role", greeting)
            return ("release_role", None)

        if isinstance(parsed, ClerkReadyMessage):
            if parsed.target_id.startswith("CR-"):
                self._last_cr_id = parsed.target_id
            elif "ready to try:" in parsed.text.lower():
                self._last_preview_ask_id = parsed.target_id
            return ("post_client", parsed.text)

        if isinstance(parsed, ClerkQuestionMessage):
            self._last_question_id = parsed.question_id
            choices_str = " ".join(f"{idx}) {c}" for idx, c in enumerate(parsed.choices, 1))
            return ("post_client", f"{parsed.text}\nChoices: {choices_str}")

        return ("noop", None)

    async def handle_client_message(
        self,
        *,
        sender: str,
        text: str,
        message_link: str,
    ) -> tuple[str | None, list[str]]:
        """Process a client message in acme-client and return (client_ack, intake_lines)."""
        cleaned = text.strip()
        lower = cleaned.lower()

        # 1. Check if client is accepting a preview ("accept")
        if lower in {"accept", "accepted", "looks good", "lgtm"} and self._last_preview_ask_id:
            ask_id = self._last_preview_ask_id
            self._last_preview_ask_id = None
            return (None, [f"ACCEPT {ask_id} | link={message_link}"])

        # 2. Check if client is choosing a change order option (A, B, C, D, not now)
        if lower in {"a", "b", "c", "d", "not now", "decline"} and self._last_cr_id is not None:
            cr_id = self._last_cr_id
            choice = "DECLINE" if lower in {"not now", "decline"} else lower.upper()
            self._last_cr_id = None
            return (None, [f"DECISION {cr_id} {choice} | link={message_link}"])

        # 3. Check if client is answering the active clarifying question
        if self._last_question_id is not None and len(cleaned.split()) <= 15:
            q_id = self._last_question_id
            self._last_question_id = None
            return (
                None,
                [f'ANSWER {q_id} | "{cleaned}" | link={message_link}'],
            )

        # 4. Split client message into individual asks via LLMPort
        split_out = await self._llm.json(
            "Split the client message into individual scope asks.",
            cleaned,
            ScoutSplitOutput,
        )
        asks = [a.strip() for a in split_out.asks if a.strip()] or [cleaned]
        ack = render_acknowledgement(sender, len(asks)) if self._mode == "autopilot" else None
        intake_lines = [f'ASK | "{q}" | requester={sender} | link={message_link}' for q in asks]
        return (ack, intake_lines)
