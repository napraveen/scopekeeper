"""MemoryService for answering '@clerk what did we agree about <topic>?'."""

from __future__ import annotations

from clerk.db.repositories import LedgerRepository
from clerk.domain.categories import normalize_tokens
from clerk.domain.templates import format_usd
from clerk.ports.protocols import LLMPort


class MemoryService:
    """Service that searches decisions, asks, change requests, and swaps with cited links."""

    def __init__(self, repo: LedgerRepository, llm: LLMPort | None = None) -> None:
        self._repo = repo
        self._llm = llm

    def find_evidence_lines(self, topic: str) -> list[str]:
        """Return matched evidence lines with links from decisions, CRs, swaps, and asks."""
        cleaned_topic = topic.strip().rstrip("?.!")
        tokens = normalize_tokens(cleaned_topic)
        raw_words = {
            w.lower().strip(".,?!'\"")
            for w in cleaned_topic.split()
            if len(w.strip(".,?!'\"")) >= 2
        }
        search_terms = tokens | raw_words
        topic_lower = cleaned_topic.lower()

        lines: list[str] = []

        # 1. Search recorded decisions
        for dec in self._repo.list_decisions():
            dec_words = normalize_tokens(dec.text) | {
                w.lower().strip(".,;:") for w in dec.text.split()
            }
            if (
                (search_terms and (search_terms & dec_words))
                or (topic_lower and topic_lower in dec.text.lower())
                or dec.id.lower() == topic_lower
            ):
                lines.append(f'- Decision {dec.id} ({dec.date}): "{dec.text}" ({dec.link})')

        # 2. Search change requests
        for cr in self._repo.list_change_requests():
            cr_words = normalize_tokens(cr.title) | {
                w.lower().strip(".,;:") for w in cr.title.split()
            }
            if (
                (search_terms and (search_terms & cr_words))
                or (topic_lower and topic_lower in cr.title.lower())
                or cr.id.lower() == topic_lower
            ):
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

        # 3. Search swaps
        crs_by_id = {cr.id: cr for cr in self._repo.list_change_requests()}
        for sw in self._repo.list_swaps():
            sw_text = f"{sw.added_title} {' '.join(sw.removed_item_ids)}"
            sw_words = normalize_tokens(sw_text) | {
                w.lower().strip(".,;:") for w in sw_text.split()
            }
            if (
                (search_terms and (search_terms & sw_words))
                or (topic_lower and topic_lower in sw_text.lower())
            ):
                removed_str = ", ".join(sw.removed_item_ids)
                cr_match = crs_by_id.get(sw.cr_id)
                sw_link = (
                    cr_match.room.url
                    if cr_match
                    else f"https://slack.com/archives/{sw.cr_id.lower()}"
                )
                lines.append(
                    f'- Swap {sw.id} ({sw.cr_id}): replaced {removed_str} '
                    f'with "{sw.added_title}" at $0 ({sw_link})'
                )

        # 4. Search asks
        for ask in self._repo.list_asks():
            ask_words = normalize_tokens(ask.quote) | {
                w.lower().strip(".,;:") for w in ask.quote.split()
            }
            if (
                (search_terms and (search_terms & ask_words))
                or (topic_lower and topic_lower in ask.quote.lower())
                or ask.id.lower() == topic_lower
            ):
                cat_str = ask.category.value if ask.category else ask.status.value
                lines.append(f'- Ask {ask.id} [{cat_str}]: "{ask.quote}" ({ask.source.url})')

        return lines

    def query(self, topic: str) -> str:
        """Search recorded decisions, asks, and change requests for `topic` (2-4 lines)."""
        cleaned_topic = topic.strip().rstrip("?.!")
        lines = self.find_evidence_lines(cleaned_topic)
        if not lines:
            return f"No recorded decision, ask, or change request found about '{cleaned_topic}'."

        header = f"Recorded agreements matching '{cleaned_topic}':"
        return "\n".join([header, *lines[:3]])

    async def answer(self, topic: str) -> str:
        """Async memory query returning a 2-4 line cited response."""
        return self.query(topic)
