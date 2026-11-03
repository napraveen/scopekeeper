"""Database engine, session factory, schema initialization, and seed loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from clerk.db.tables import (
    AskRow,
    Base,
    ChangeRequestRow,
    DecisionRow,
    GoodwillRow,
    SettingRow,
)
from clerk.domain.models import Plan, SeedLedgerConfig


def create_db_engine(database_url: str | Path) -> Engine:
    """Create a SQLAlchemy engine for SQLite (file or in-memory) or Postgres."""
    if isinstance(database_url, Path):
        database_url.parent.mkdir(parents=True, exist_ok=True)
        url_str = f"sqlite:///{database_url}"
    else:
        url_str = database_url
        if url_str.startswith("sqlite:///") and ":memory:" not in url_str:
            db_file = Path(url_str.removeprefix("sqlite:///"))
            db_file.parent.mkdir(parents=True, exist_ok=True)

    connect_args: dict[str, Any] = {}
    if url_str.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(url_str, connect_args=connect_args, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a configured SQLAlchemy sessionmaker."""
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def init_db(engine: Engine) -> None:
    """Create all database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def reset_and_seed_db(
    engine: Engine,
    seed_ledger: SeedLedgerConfig,
    plan: Plan,
    simulated_start: str = "2026-11-05T19:00:00+05:30",
) -> None:
    """Drop and recreate all tables, then populate seed-ledger.yaml and plan.yaml."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        seed_database_from_config(
            session=session,
            seed_ledger=seed_ledger,
            plan=plan,
            simulated_start=simulated_start,
        )


def seed_database_from_config(
    session: Session,
    seed_ledger: SeedLedgerConfig,
    plan: Plan,
    simulated_start: str = "2026-11-05T19:00:00+05:30",
) -> None:
    """Idempotently load seed decisions, asks, change requests, goodwill, and plan JSON."""
    for dec in seed_ledger.decisions:
        if session.get(DecisionRow, dec.id) is None:
            session.add(
                DecisionRow(
                    id=dec.id,
                    date=dec.date,
                    text=dec.text,
                    link=dec.link,
                    source=dec.source,
                )
            )

    for ask_data in seed_ledger.asks:
        ask_id = str(ask_data["id"])
        if session.get(AskRow, ask_id) is None:
            session.add(
                AskRow(
                    id=ask_id,
                    source_room=str(ask_data.get("source_room", "acme-client")),
                    source_message_id=str(ask_data.get("source_message_id", "")),
                    source_link=str(ask_data.get("source_link", "")),
                    requester=str(ask_data.get("requester", "Sam")),
                    quote=str(ask_data["quote"]),
                    category=ask_data.get("category"),
                    clause_ids=list(ask_data.get("clause_ids", [])),
                    related_item=ask_data.get("related_item"),
                    decision_id=ask_data.get("decision_id"),
                    confidence=(
                        float(ask_data["confidence"])
                        if ask_data.get("confidence") is not None
                        else None
                    ),
                    reason=ask_data.get("reason"),
                    status=str(ask_data.get("status", "accepted")),
                    cr_id=ask_data.get("cr_id"),
                    question_id=ask_data.get("question_id"),
                    created_at=str(ask_data["created_at"]),
                    decided_at=ask_data.get("decided_at"),
                    version=1,
                )
            )

    for cr_data in seed_ledger.change_requests:
        cr_id = str(cr_data["id"])
        if session.get(ChangeRequestRow, cr_id) is None:
            room_id = str(cr_data.get("room_id", f"acme-{cr_id.lower()}"))
            session.add(
                ChangeRequestRow(
                    id=cr_id,
                    ask_id=str(cr_data["ask_id"]),
                    title=str(cr_data.get("title", "")),
                    room_id=room_id,
                    room_url=str(cr_data.get("room_url", f"https://slack.com/archives/{room_id}")),
                    status=str(cr_data.get("status", "decided")),
                    estimate=cr_data.get("estimate"),
                    confirmed_hours=(
                        int(cr_data["confirmed_hours"])
                        if cr_data.get("confirmed_hours") is not None
                        else None
                    ),
                    smaller_confirmed_hours=None,
                    confirmed_by=cr_data.get("confirmed_by"),
                    options=list(cr_data.get("options", [])),
                    envelope_result=cr_data.get("envelope_result"),
                    approved_by=cr_data.get("approved_by"),
                    approved_at=cr_data.get("approved_at"),
                    approved_options=cr_data.get("approved_options"),
                    client_choice=cr_data.get("client_choice"),
                    created_at=str(cr_data["created_at"]),
                    decided_at=cr_data.get("decided_at"),
                    version=1,
                )
            )

    for gw in seed_ledger.goodwill:
        if session.get(GoodwillRow, gw.id) is None:
            session.add(
                GoodwillRow(
                    id=gw.id,
                    ask_id=gw.ask_id,
                    hours=float(gw.hours),
                    reason=gw.reason,
                    approved_by=gw.approved_by,
                    month=gw.month,
                    date=gw.date or f"{gw.month}-03",
                    link=gw.link or "",
                )
            )

    if session.get(SettingRow, "plan_json") is None:
        session.add(SettingRow(key="plan_json", value=plan.model_dump_json()))

    if session.get(SettingRow, "clock_iso") is None:
        session.add(SettingRow(key="clock_iso", value=simulated_start))
