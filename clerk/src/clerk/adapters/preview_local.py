"""FakePreview and LocalPreviewAdapter implementing PreviewPort."""

from __future__ import annotations

import httpx


class FakePreview:
    """Deterministic in-memory PreviewPort implementation for tests and offline demos."""

    def __init__(self, base_url: str = "http://localhost:4300") -> None:
        self._base_url = base_url.rstrip("/")
        self._deployed: dict[str, str] = {}

    async def deploy_preview(self, work_id: str, branch: str) -> str:
        """Register a preview URL for `(work_id, branch)` and return it."""
        safe_branch = branch.strip("/")
        url = f"{self._base_url}/{safe_branch}/"
        self._deployed[work_id.upper()] = url
        return url

    @property
    def deployed(self) -> dict[str, str]:
        """Return deployed preview URLs keyed by `work_id`."""
        return dict(self._deployed)


class LocalPreviewAdapter:
    """HTTP client PreviewPort implementation calling `scripts/preview_server.py`."""

    def __init__(
        self,
        base_url: str = "http://localhost:4300",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        self._deployed: dict[str, str] = {}

    async def close(self) -> None:
        """Close the HTTP client if owned."""
        if self._owns_client:
            await self._http.aclose()

    async def deploy_preview(self, work_id: str, branch: str) -> str:
        """Trigger a preview build on `PREVIEW_BASE_URL/deploy` and return the preview URL."""
        safe_branch = branch.strip("/")
        fallback_url = f"{self._base_url}/{safe_branch}/"
        try:
            resp = await self._http.post(
                f"{self._base_url}/deploy",
                json={"work_id": work_id.upper(), "branch": safe_branch},
            )
            resp.raise_for_status()
            data = resp.json()
            url = str(data.get("url") or fallback_url)
        except Exception:
            url = fallback_url

        self._deployed[work_id.upper()] = url
        return url

    @property
    def deployed(self) -> dict[str, str]:
        """Return deployed preview URLs keyed by `work_id`."""
        return dict(self._deployed)
