"""Phase 7 integration tests for `seed_history.py` and `reset_demo.py`."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from clerk.adapters.clock import SimulatedClock
from clerk.adapters.switch_inmemory import InMemorySwitch
from clerk.db.repositories import LedgerRepository
from clerk.db.session import create_db_engine, create_session_factory, reset_and_seed_db
from clerk.settings import ConfigBundle

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, file_path: Path) -> object:
    spec = importlib.util.spec_from_file_location(name, file_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_seed_history_and_reset_demo_end_to_end(
    config_bundle: ConfigBundle,
    tmp_path: Path,
) -> None:
    """Verify `seed_history.py` deterministic git repo and `reset_demo.py` full restoration."""
    seed_mod = _load_module("seed_history", REPO_ROOT / "demo-app" / "seed" / "seed_history.py")
    reset_mod = _load_module("reset_demo", REPO_ROOT / "scripts" / "reset_demo.py")

    portal_dir = tmp_path / "acme-portal"
    seeded_repo = REPO_ROOT / "demo-app" / "acme-portal"
    if not (seeded_repo / ".git").exists():
        stats = seed_mod.generate_acme_portal(portal_dir)  # type: ignore[attr-defined]
        assert stats["total_commits"] == 41
        assert stats["effort_merges"] == 8
    else:
        import shutil

        shutil.copytree(seeded_repo, portal_dir)
        commit_count = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=str(portal_dir),
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        assert commit_count == 41

    # Verify all 8 Effort-Hours trailers exist in git merge history
    log_out = subprocess.run(
        ["git", "log", "--merges", "--format=%B"],
        cwd=str(portal_dir),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    for hours in (30, 16, 40, 61, 18, 52, 14, 12):
        assert f"Effort-Hours: {hours}" in log_out

    # Verify tag `seed-v1` points to HEAD
    tag_sha = subprocess.run(
        ["git", "rev-parse", "seed-v1^{commit}"],
        cwd=str(portal_dir),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(portal_dir),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tag_sha == head_sha

    # Verify planted Safari bug in Login.tsx, dark tokens in tokens.css, and pre-push hook
    login_tsx = (portal_dir / "src" / "pages" / "Login.tsx").read_text(encoding="utf-8")
    assert 'new Date("2026-11-04 10:00")' in login_tsx
    tokens_css = (portal_dir / "src" / "theme" / "tokens.css").read_text(encoding="utf-8")
    assert '[data-theme="dark"]' in tokens_css
    pre_push = (portal_dir / ".git" / "hooks" / "pre-push").read_text(encoding="utf-8")
    assert "refs/heads/main" in pre_push

    # Dirty the repo: create a `sk/ask-0007-fix-safari` branch, commit a file, and add a ticket
    subprocess.run(
        ["git", "checkout", "-b", "sk/ask-0007-fix-safari"],
        cwd=str(portal_dir),
        check=True,
        capture_output=True,
    )
    (portal_dir / "tickets").mkdir(parents=True, exist_ok=True)
    (portal_dir / "tickets" / "ASK-0007.md").write_text("# Fix Safari login", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(portal_dir), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "fix: safari iso date"],
        cwd=str(portal_dir),
        check=True,
        capture_output=True,
    )

    # Create a SQLite file DB and mutate it with a new ask and an open Change Request
    db_file = tmp_path / "test_reset.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_db_engine(db_url)
    reset_and_seed_db(engine, config_bundle.seed_ledger, config_bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=config_bundle.plan)

    ask = repo.create_ask(
        quote="Add a native iOS widget",
        requester="Sam",
        created_at="2026-11-05T21:00:00+05:30",
    )
    repo.create_change_request(
        cr_id="CR-004",
        ask_id=ask.id,
        title="Native iOS widget",
        room_id="acme-cr-004-ios-widget",
        room_url="https://slack.com/archives/acme-cr-004",
        created_at="2026-11-05T21:01:00+05:30",
    )
    repo.set_setting("clock_iso", "2026-11-06T12:00:00+05:30")

    previews_dir = tmp_path / ".previews"
    (previews_dir / "sk-ask-0007").mkdir(parents=True, exist_ok=True)

    clock = SimulatedClock("2026-11-06T12:00:00+05:30")
    switch = InMemorySwitch(rooms_config=config_bundle.rooms, clock=clock)
    await switch.connect()

    # Run `reset_demo.run_reset_async`
    summary = await reset_mod.run_reset_async(  # type: ignore[attr-defined]
        database_url=db_url,
        config_dir=config_bundle.config_dir,
        demo_repo_path=portal_dir,
        previews_dir=previews_dir,
        clock_start="2026-11-05T19:00:00+05:30",
        switch_adapter=switch,
    )

    assert summary["database_reset"] is True
    assert summary["clock_iso"] == "2026-11-05T19:00:00+05:30"
    assert "acme-cr-004-ios-widget" in summary["archived_rooms"]
    assert "sk/ask-0007-fix-safari" in summary["git"]["deleted_branches"]
    assert summary["cleared_previews"] == 1
    assert summary["elapsed_seconds"] < 60.0

    # Verify DB is back to seed state (6 asks, 3 CRs, clock reset)
    assert len(repo.list_asks()) == 6
    assert len(repo.list_change_requests()) == 3
    assert repo.get_setting("clock_iso") == "2026-11-05T19:00:00+05:30"
    assert not (portal_dir / "tickets").exists()
