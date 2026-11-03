"""Command-line interface for running and controlling ScopeKeeper Clerk."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import uvicorn

from clerk.adapters.clock import parse_clock_offset
from clerk.db.repositories import LedgerRepository
from clerk.db.session import create_db_engine, create_session_factory, reset_and_seed_db
from clerk.main import create_app
from clerk.settings import Settings, load_all_configs


def run_serve(args: argparse.Namespace) -> None:
    """Start the Clerk FastAPI server with background workers enabled."""
    settings = Settings()
    host = args.host or settings.clerk_host
    port = args.port or settings.clerk_port
    application = create_app(settings=settings, start_workers=True)
    uvicorn.run(
        application,
        host=host,
        port=port,
        log_level=settings.log_level.lower(),
    )


def run_seed(_args: argparse.Namespace) -> None:
    """Reset and seed the ScopeKeeper database from config files."""
    settings = Settings()
    bundle = load_all_configs(Path(settings.clerk_config_dir))
    engine = create_db_engine(settings.database_url)
    reset_and_seed_db(engine, bundle.seed_ledger, bundle.plan)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=bundle.plan)
    repo.set_setting("clock_iso", settings.clock_start)
    print(f"Database seeded at {settings.database_url}; clock reset to {settings.clock_start}")


async def _run_flip_async() -> None:
    from clerk.adapters.clock import SimulatedClock
    from clerk.adapters.switch_inmemory import InMemorySwitch
    from clerk.services.brief import BriefService
    from clerk.services.flip import FlipService

    settings = Settings()
    bundle = load_all_configs(Path(settings.clerk_config_dir))
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=bundle.plan)

    clock_iso = repo.get_setting("clock_iso") or settings.clock_start
    clock = SimulatedClock(clock_iso)
    switch = InMemorySwitch(rooms_config=bundle.rooms, clock=clock)
    await switch.connect()

    brief_service = BriefService(
        repo=repo,
        switch=switch,
        clock=clock,
        scope_map=bundle.scope_map,
    )
    flip_service = FlipService(
        repo=repo,
        switch=switch,
        clock=clock,
        schedule=bundle.schedule,
        rooms_config=bundle.rooms,
        brief_service=brief_service,
    )

    shift = await flip_service.flip_to_autopilot()
    print(f"Handover triggered: {shift.from_holder} -> {shift.to_holder} at {shift.at}")


def run_flip(_args: argparse.Namespace) -> None:
    """Trigger immediate shift handover to Scout (autopilot)."""
    asyncio.run(_run_flip_async())


async def _run_morning_async() -> None:
    from clerk.adapters.clock import SimulatedClock
    from clerk.adapters.switch_inmemory import InMemorySwitch
    from clerk.services.brief import BriefService
    from clerk.services.flip import FlipService

    settings = Settings()
    bundle = load_all_configs(Path(settings.clerk_config_dir))
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=bundle.plan)

    clock_iso = repo.get_setting("clock_iso") or settings.clock_start
    clock = SimulatedClock(clock_iso)
    switch = InMemorySwitch(rooms_config=bundle.rooms, clock=clock)
    await switch.connect()

    brief_service = BriefService(
        repo=repo,
        switch=switch,
        clock=clock,
        scope_map=bundle.scope_map,
    )
    flip_service = FlipService(
        repo=repo,
        switch=switch,
        clock=clock,
        schedule=bundle.schedule,
        rooms_config=bundle.rooms,
        brief_service=brief_service,
    )

    shift = await flip_service.flip_to_copilot(post_brief=True)
    print(f"Morning brief posted; handover: {shift.from_holder} -> {shift.to_holder}")


def run_morning(_args: argparse.Namespace) -> None:
    """Trigger 9:30 AM morning brief and handover to Priya (copilot)."""
    asyncio.run(_run_morning_async())


def run_clock(args: argparse.Namespace) -> None:
    """Advance or set the simulated clock stored in the database."""
    from datetime import datetime

    from clerk.adapters.clock import SimulatedClock

    settings = Settings()
    bundle = load_all_configs(Path(settings.clerk_config_dir))
    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    repo = LedgerRepository(session_factory, default_plan=bundle.plan)

    current_iso = repo.get_setting("clock_iso") or settings.clock_start
    clock = SimulatedClock(current_iso)

    if args.offset:
        delta = parse_clock_offset(args.offset)
        new_dt = clock.advance(delta)
    elif args.iso:
        new_dt = datetime.fromisoformat(args.iso.replace("Z", "+00:00"))
        clock.set_time(new_dt)
    else:
        print(f"Current simulated clock: {current_iso}")
        return

    repo.set_setting("clock_iso", new_dt.isoformat())
    print(f"Simulated clock updated: {new_dt.isoformat()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ScopeKeeper Clerk CLI")
    subparsers = parser.add_subparsers(dest="command")

    serve_p = subparsers.add_parser("serve", help="Run Clerk FastAPI server")
    serve_p.add_argument("--host", default=None, help="Host to bind")
    serve_p.add_argument("--port", type=int, default=None, help="Port to bind")
    serve_p.set_defaults(func=run_serve)

    seed_p = subparsers.add_parser("seed", help="Reset and seed database")
    seed_p.set_defaults(func=run_seed)

    flip_p = subparsers.add_parser("flip", help="Trigger evening autopilot handover")
    flip_p.set_defaults(func=run_flip)

    morning_p = subparsers.add_parser("morning", help="Trigger morning brief and handover")
    morning_p.set_defaults(func=run_morning)

    clock_p = subparsers.add_parser("clock", help="Set or advance simulated clock")
    clock_p.add_argument(
        "offset", nargs="?", default=None, help="Relative offset (e.g. +2h, +14h30m)"
    )
    clock_p.add_argument("--iso", default=None, help="Set exact ISO-8601 timestamp")
    clock_p.set_defaults(func=run_clock)

    args = parser.parse_args()
    if not args.command:
        # Default behavior: run serve
        run_serve(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
