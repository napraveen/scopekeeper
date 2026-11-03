#!/usr/bin/env python3
"""Local preview server building git worktrees of `acme-portal` and serving `http://localhost:4300/<branch>/`."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="ScopeKeeper Preview Server", version="0.1.0")

REPO_PATH = Path(os.environ.get("DEMO_REPO_PATH", "./demo-app/acme-portal")).resolve()
PREVIEW_PORT = int(os.environ.get("PREVIEW_PORT", "4300"))
PREVIEW_BASE_URL = os.environ.get("PREVIEW_BASE_URL", f"http://localhost:{PREVIEW_PORT}").rstrip("/")
BUILDS_ROOT = Path(tempfile.gettempdir()) / "scopekeeper-previews"
BUILDS_ROOT.mkdir(parents=True, exist_ok=True)

_DEPLOYMENTS: dict[str, dict[str, str]] = {}


class DeployRequest(BaseModel):
    work_id: str
    branch: str


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "deployments": len(_DEPLOYMENTS)}


@app.post("/deploy")
def deploy_branch(req: DeployRequest) -> dict[str, str]:
    safe_branch = req.branch.strip("/")
    target_dir = BUILDS_ROOT / safe_branch.replace("/", "__")
    target_dir.mkdir(parents=True, exist_ok=True)

    built_static = False
    if REPO_PATH.exists() and (REPO_PATH / ".git").exists():
        wt_dir = BUILDS_ROOT / f"wt_{safe_branch.replace('/', '__')}"
        try:
            if wt_dir.exists():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(wt_dir)],
                    cwd=REPO_PATH,
                    capture_output=True,
                    check=False,
                )
                shutil.rmtree(wt_dir, ignore_errors=True)
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(wt_dir), safe_branch],
                cwd=REPO_PATH,
                capture_output=True,
                check=True,
                timeout=20,
            )
            if (wt_dir / "package.json").exists():
                subprocess.run(["npm", "ci"], cwd=wt_dir, capture_output=True, check=False, timeout=60)
                subprocess.run(
                    ["npm", "run", "build"],
                    cwd=wt_dir,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                dist_dir = wt_dir / "dist"
                if dist_dir.exists():
                    shutil.copytree(dist_dir, target_dir, dirs_exist_ok=True)
                    built_static = True
        except Exception:
            built_static = False

    if not built_static and not (target_dir / "index.html").exists():
        (target_dir / "index.html").write_text(
            f"<!doctype html><html><head><title>Preview: {safe_branch}</title></head>"
            f"<body><h1>Acme Portal Preview — {safe_branch}</h1>"
            f"<p>Work Item: {req.work_id}</p></body></html>",
            encoding="utf-8",
        )

    url = f"{PREVIEW_BASE_URL}/{safe_branch}/"
    _DEPLOYMENTS[safe_branch] = {"work_id": req.work_id, "branch": safe_branch, "url": url}
    return {"work_id": req.work_id, "branch": safe_branch, "url": url}


@app.get("/{branch_path:path}")
def serve_preview(branch_path: str) -> Any:
    cleaned = branch_path.strip("/")
    for branch_key in sorted(_DEPLOYMENTS.keys(), key=len, reverse=True):
        if cleaned == branch_key or cleaned.startswith(branch_key + "/"):
            rel_asset = cleaned[len(branch_key) :].lstrip("/") or "index.html"
            build_dir = BUILDS_ROOT / branch_key.replace("/", "__")
            file_path = build_dir / rel_asset
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            idx_path = build_dir / "index.html"
            if idx_path.exists():
                return FileResponse(idx_path)

    return HTMLResponse(
        f"<!doctype html><html><head><title>Preview: {cleaned}</title></head>"
        f"<body><h1>Acme Portal Preview — {cleaned}</h1></body></html>"
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PREVIEW_PORT)
