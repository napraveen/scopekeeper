"""SQLAlchemy 2.0 ORM table definitions for ScopeKeeper."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all Clerk database models."""


class AskRow(Base):
    """Client ask table (`asks`)."""

    __tablename__ = "asks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_room: Mapped[str] = mapped_column(String(128), nullable=False)
    source_message_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    source_link: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requester: Mapped[str] = mapped_column(String(128), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    clause_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_item: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    cr_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    question_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class QuestionRow(Base):
    """Clarifying question table (`questions`)."""

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ask_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    asked_at: Mapped[str] = mapped_column(String(64), nullable=False)
    answered_at: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ChangeRequestRow(Base):
    """Out-of-scope change request table (`change_requests`)."""

    __tablename__ = "change_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ask_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    room_id: Mapped[str] = mapped_column(String(128), nullable=False)
    room_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    estimate: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confirmed_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smaller_confirmed_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    envelope_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    client_choice: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class DecisionRow(Base):
    """Recorded scope/architecture decisions table (`decisions`)."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    date: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)


class WorkItemRow(Base):
    """Builder work items table (`work_items`)."""

    __tablename__ = "work_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ask_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cr_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ticket_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    branch: Mapped[str] = mapped_column(String(256), nullable=False)
    pr_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class GoodwillRow(Base):
    """Monthly goodwill grants table (`goodwill`)."""

    __tablename__ = "goodwill"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ask_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    hours: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(128), nullable=False)
    month: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    link: Mapped[str] = mapped_column(Text, default="", nullable=False)


class SwapRow(Base):
    """Recorded scope swaps table (`swaps`)."""

    __tablename__ = "swaps"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    cr_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    added_title: Mapped[str] = mapped_column(Text, nullable=False)
    removed_item_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hours_added: Mapped[int] = mapped_column(Integer, nullable=False)
    hours_removed: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class RoleShiftRow(Base):
    """@client-desk role handover audit table (`role_shifts`)."""

    __tablename__ = "role_shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    from_holder: Mapped[str] = mapped_column(String(128), nullable=False)
    to_holder: Mapped[str] = mapped_column(String(128), nullable=False)
    at: Mapped[str] = mapped_column(String(64), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EventRow(Base):
    """Audit and SSE stream event log table (`events`)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ask_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    cr_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    room_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    message_link: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProcessedEventRow(Base):
    """Idempotency tracking table for processed Switch events (`processed_events`)."""

    __tablename__ = "processed_events"

    switch_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    processed_at: Mapped[str] = mapped_column(String(64), nullable=False)


class SettingRow(Base):
    """Key-value runtime settings table (`settings`)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
