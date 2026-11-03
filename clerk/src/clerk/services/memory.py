"""MemoryService for answering '@clerk what did we agree about <topic>?'."""

from __future__ import annotations

from clerk.db.repositories import LedgerRepository
from clerk.domain.categories import normalize_tokens
from clerk.domain.templates import format_usd


class MemoryService:
    """Service that searches decisions, asks, and change requests with cited links."""

    def __init__(self, repo: LedgerRepository) -> None:
        self._repo = repo

    def query(self, topic: str) -> str:
        """Search recorded decisions, asks, and change requests for `topic` (2-4 lines)."""
        tokens = normalize_tokens(topic)
        if not tokens:
            tokens = {w.lower() for w in topic.strip().split() if w.strip()}

        lines: list[str] = []

        # 1. Search decisions
        for dec in self._repo.list_decisions():
            dec_tokens = normalize_tokens(dec.text) | {w.lower() for w in dec.text.split()}
            if tokens & dec_tokens or topic.lower() in dec.text.lower():
                lines.append(f'- Decision {dec.id} ({dec.date}): "{dec.text}" ({dec.link})')

        # 2. Search change requests
        for cr in self._repo.list_change_requests():
            cr_tokens = normalize_tokens(cr.title)
            if tokens & cr_tokens or topic.lower() in cr.title.lower():
                choice_str = cr.client_choice or cr.status.value
                price_note = ""
                if cr.client_choice and cr.options:
                    for opt in cr.options:
                        if opt.key.value == cr.client_choice:
                            price_note = f" at {format_usd(opt.price_cents)}"
                            break
                lines.append(
                    f"- Change Request {cr.id} ({cr.title}): "
                    f"{choice_str}{price_note} ({cr.room.url})"
                )

        # 3. Search asks
        for ask in self._repo.list_asks():
            ask_tokens = normalize_tokens(ask.quote)
            if tokens & ask_tokens or topic.lower() in ask.quote.lower():
                cat_str = ask.category.value if ask.category else ask.status.value
                lines.append(f'- Ask {ask.id} [{cat_str}]: "{ask.quote}" ({ask.source.url})')

        if not lines:
            return f"No recorded decision, ask, or change request found about '{topic}'."

        header = f"Recorded agreements matching '{topic}':"
        return "\n".join([header, *lines[:3]])
