"""LocalGitHost adapter implementing GitHostPort with local ticket files and PR registry."""

from __future__ import annotations

from pathlib import Path

from clerk.ports.protocols import PullRequestRef, TicketRef


class LocalGitHost:
    """Offline and local-repository GitHostPort implementation."""

    def __init__(self, repo_path: Path | None = None) -> None:
        self._repo_path = repo_path
        self._tickets: dict[str, TicketRef] = {}
        self._branches: set[str] = set()
        self._pull_requests: dict[str, PullRequestRef] = {}

    async def create_ticket(self, ask_id: str, title: str, body: str) -> TicketRef:
        """Create `tickets/ASK-NNNN.md` (and write to disk if `repo_path` is provided)."""
        norm_id = ask_id.upper()
        rel_path = f"tickets/{norm_id}.md"
        if self._repo_path is not None:
            tickets_dir = self._repo_path / "tickets"
            tickets_dir.mkdir(parents=True, exist_ok=True)
            file_path = tickets_dir / f"{norm_id}.md"
            file_path.write_text(f"# [{norm_id}] {title}\n\n{body}\n", encoding="utf-8")
        ticket = TicketRef(
            id=norm_id,
            ask_id=norm_id,
            title=title,
            url=rel_path,
        )
        self._tickets[norm_id] = ticket
        return ticket

    async def ensure_branch(self, branch: str) -> str:
        """Record or verify a `sk/ask-NNNN-<slug>` branch."""
        self._branches.add(branch)
        return branch

    async def find_pull_request(self, branch: str) -> PullRequestRef | None:
        """Return a registered pull request for `branch`, if any."""
        return self._pull_requests.get(branch)

    def register_pull_request(
        self, work_id: str, branch: str, title: str, url: str
    ) -> PullRequestRef:
        """Register a simulated pull request so polling or DONE lookup succeeds."""
        pr = PullRequestRef(
            work_id=work_id.upper(),
            branch=branch,
            title=title,
            url=url,
        )
        self._pull_requests[branch] = pr
        return pr

    @property
    def tickets(self) -> dict[str, TicketRef]:
        """Return all created tickets keyed by ask_id."""
        return dict(self._tickets)
