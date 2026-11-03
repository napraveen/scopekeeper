"""FakePreview and LocalPreviewAdapter implementing PreviewPort."""

from __future__ import annotations


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
