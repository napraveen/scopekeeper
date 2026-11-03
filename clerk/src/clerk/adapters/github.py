"""GitHubHostAdapter implementing GitHostPort against the GitHub REST API v3."""

from __future__ import annotations

import httpx

from clerk.ports.protocols import PullRequestRef, TicketRef


class GitHubHostAdapter:
    """GitHub REST API implementation of GitHostPort for issues, branches, and PR discovery."""

    def __init__(
        self,
        *,
        repo: str,
        token: str,
        base_url: str = "https://api.github.com",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._repo = repo.strip("/")
        self._owner = self._repo.split("/")[0] if "/" in self._repo else "pixel-and-co"
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(base_url=self._base_url, timeout=15.0)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def close(self) -> None:
        """Close the underlying HTTP client if owned."""
        if self._owns_client:
            await self._http.aclose()

    async def create_ticket(self, ask_id: str, title: str, body: str) -> TicketRef:
        """Create a GitHub issue for `ask_id`."""
        norm_id = ask_id.upper()
        url = f"{self._base_url}/repos/{self._repo}/issues"
        payload = {
            "title": f"[{norm_id}] {title}",
            "body": body,
            "labels": ["scopekeeper"],
        }
        resp = await self._http.post(url, headers=self._headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        issue_num = str(data.get("number") or norm_id)
        html_url = str(
            data.get("html_url") or f"https://github.com/{self._repo}/issues/{issue_num}"
        )
        return TicketRef(
            id=f"#{issue_num}",
            ask_id=norm_id,
            title=title,
            url=html_url,
        )

    async def ensure_branch(self, branch: str) -> str:
        """Validate `branch` is a `sk/ask-*` feature branch and never `main`."""
        cleaned = branch.strip()
        if cleaned in {"main", "master"}:
            raise ValueError(
                f"Branch {cleaned!r} is protected; Builder must use sk/ask-NNNN-<slug>."
            )
        return cleaned

    async def find_pull_request(self, branch: str) -> PullRequestRef | None:
        """Poll GitHub for an open pull request from `branch`."""
        url = f"{self._base_url}/repos/{self._repo}/pulls"
        params = {
            "state": "open",
            "head": f"{self._owner}:{branch}",
        }
        resp = await self._http.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        items = resp.json()
        if not isinstance(items, list) or not items:
            return None
        first = items[0]
        if not isinstance(first, dict):
            return None
        pr_num = first.get("number", 1)
        title = str(first.get("title") or branch)
        html_url = str(
            first.get("html_url") or f"https://github.com/{self._repo}/pull/{pr_num}"
        )
        return PullRequestRef(
            work_id=f"PR-{pr_num}",
            branch=branch,
            title=title,
            url=html_url,
        )
