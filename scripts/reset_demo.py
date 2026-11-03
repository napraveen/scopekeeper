"""Reset ScopeKeeper demo environment to the clean `seed-v1` state in under a minute.

Per Section 14 of `BUILD_PROMPT.md`, `reset_demo.py`:
1. Posts a closing note and archives any open change rooms (`acme-cr-*`) if Switch is configured,
2. Restores the SQLite/Postgres database to the initial seed state (`config/seed-ledger.yaml` + `config/plan.yaml`),
3. Resets `demo-app/acme-portal` to the `seed-v1` tag, deletes all `sk/*` branches and local tickets,
4. Clears deployed preview worktrees under `.previews/`, and
5. Resets the simulated clock in the database to `CLOCK_START` (`2026-11-05T19:00:00+05:30`).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Ensure clerk package is importable when invoked directly via `python scripts/reset_demo.py`
REPO_ROOT = Path(__file__).resolve().parents[1]
CLERK_SRC = REPO_ROOT / "clerk" / "src"
if str(CLERK_SRC) not in sys.path:
    sys.path.insert(0, str(CLERK_SRC))

from clerk.adapters.clock import SimulatedClock  # noqa: E402
from clerk.adapters.switch_protocol import SwitchProtocolAdapter  # noqa: E402
from clerk.db.repositories import LedgerRepository  # noqa: E402
from clerk.db.session import (  # noqa: E402
    create_db_engine,
    create_session_factory,
    reset_and_seed_db,
)
from clerk.domain.models import ChangeRequestStatus, ChatApp  # noqa: E402
from clerk.ports import RoomRef  # noqa: E402
from clerk.settings import Settings, load_all_configs  # noqa: E402


def _force_remove_dir(target: Path) -> None:
    if not target.exists():
        return

    def _onerror(func: object, path: str, _exc_info: object) -> None:
        os.chmod(path, stat.S_IWRITE)
        if callable(func):
            func(path)

    shutil.rmtree(target, onerror=_onerror)


def reset_git_repo(repo_path: Path) -> dict[str, Any]:
    """Reset `acme-portal` to tag `seed-v1` and delete all `sk/*` branches and `tickets/`."""
    if not (repo_path / ".git").exists():
        # If the repo hasn't been generated yet, generate it using seed_history.py
        seed_script = REPO_ROOT / "demo-app" / "seed" / "seed_history.py"
        env = os.environ.copy()
        env["DEMO_REPO_PATH"] = str(repo_path)
        subprocess.run([sys.executable, str(seed_script)], env=env, check=True)

    # Prune any leftover git worktrees first
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=str(repo_path),
        check=False,
        capture_output=True,
        text=True,
    )

    subprocess.run(
        ["git", "checkout", "-f", "main"],
        cwd=str(repo_path),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "reset", "--hard", "seed-v1"],
        cwd=str(repo_path),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "clean", "-fd"],
        cwd=str(repo_path),
        check=True,
        capture_output=True,
        text=True,
    )

    # List and delete all `sk/*` branches
    branches_out = subprocess.run(
        ["git", "branch", "--list", "sk/*"],
        cwd=str(repo_path),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    deleted_branches: list[str] = []
    for raw_line in branches_out.splitlines():
        branch = raw_line.strip().lstrip("* ").strip()
        if branch:
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=str(repo_path),
                check=True,
                capture_output=True,
                text=True,
            )
            deleted_branches.append(branch)

    tickets_dir = repo_path / "tickets"
    if tickets_dir.exists():
        _force_remove_dir(tickets_dir)

    head_sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(repo_path),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    return {
        "head_sha": head_sha,
        "deleted_branches": deleted_branches,
    }


def clear_previews(previews_dir: Path | None = None) -> int:
    """Remove deployed local preview directories."""
    target = previews_dir or (REPO_ROOT / ".previews")
    if not target.exists():
        return 0
    count = sum(1 for p in target.iterdir() if p.is_dir())
    _force_remove_dir(target)
    target.mkdir(parents=True, exist_ok=True)
    return count


async def archive_open_change_rooms(
    repo: LedgerRepository,
    switch_adapter: Any | None = None,
) -> list[str]:
    """Post a closing note and archive open change rooms before DB reset."""
    archived: list[str] = []
    try:
        crs = repo.list_change_requests()
    except Exception:
        return archived

    open_crs = [cr for cr in crs if cr.status != ChangeRequestStatus.CLOSED]
    if not open_crs or switch_adapter is None:
        return archived

    for cr in open_crs:
        room_ref = RoomRef(id=cr.room.room, name=cr.room.room, app=ChatApp.SLACK)
        try:
            await switch_adapter.post(
                room_ref,
                f"Demo reset: closing change room `{cr.room.room}` for `{cr.id}`.",
            )
            await switch_adapter.archive_room(room_ref)
            archived.append(cr.room.room)
        except Exception:
            continue
    return archived


async def run_reset_async(
    *,
    database_url: str | None = None,
    config_dir: Path | None = None,
    demo_repo_path: Path | None = None,
    previews_dir: Path | None = None,
    clock_start: str | None = None,
    switch_adapter: Any | None = None,
) -> dict[str, Any]:
    """Perform the full ScopeKeeper demo reset and return a summary dictionary."""
    started = time.monotonic()
    settings = Settings()
    cfg_dir = config_dir or (REPO_ROOT / "config")
    bundle = load_all_configs(cfg_dir)

    db_url = database_url or settings.database_url
    if demo_repo_path:
        repo_path = demo_repo_path.resolve()
    else:
        root_portal = (REPO_ROOT / "demo-app" / "acme-portal").resolve()
        repo_path = root_portal if root_portal.exists() else settings.demo_repo_path.resolve()
    start_iso = clock_start or settings.clock_start

    engine = create_db_engine(db_url)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=bundle.plan)

    # 1. Close & archive open change rooms if a live/fake Switch adapter is active
    live_switch = switch_adapter
    created_live_switch = False
    if live_switch is None and settings.clerk_agent_id and settings.clerk_api_key:
        clock = SimulatedClock(start_iso)
        live_switch = SwitchProtocolAdapter(
            base_url=settings.switch_base_url,
            ws_url=settings.switch_ws_url,
            agent_id=settings.clerk_agent_id,
            api_key=settings.clerk_api_key,
            rooms_config=bundle.rooms,
            clock=clock,
        )
        created_live_switch = True

    archived_rooms = await archive_open_change_rooms(repo, live_switch)
    if created_live_switch and live_switch is not None:
        await live_switch.close()

    # 2. Restore database to seed state and reset simulated clock to CLOCK_START
    reset_and_seed_db(engine, bundle.seed_ledger, bundle.plan)
    repo.set_setting("clock_iso", start_iso)

    # 3. Reset acme-portal git repo to seed-v1 and delete sk/* branches
    git_summary = reset_git_repo(repo_path)

    # 4. Clear deployed previews
    cleared_previews = clear_previews(previews_dir)

    elapsed = round(time.monotonic() - started, 3)
    return {
        "database_reset": True,
        "clock_iso": start_iso,
        "archived_rooms": archived_rooms,
        "git": git_summary,
        "cleared_previews": cleared_previews,
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    summary = asyncio.run(run_reset_async())
    print(
        f"Reset complete in {summary['elapsed_seconds']}s: "
        f"clock={summary['clock_iso']}, "
        f"head={summary['git']['head_sha']}, "
        f"deleted_branches={len(summary['git']['deleted_branches'])}, "
        f"archived_rooms={len(summary['archived_rooms'])}."
    )


if __name__ == "__main__":
    main()
