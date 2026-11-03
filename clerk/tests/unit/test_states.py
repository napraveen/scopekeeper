"""Unit tests for Ask and ChangeRequest state machine transitions."""

from __future__ import annotations

import pytest

from clerk.domain.models import AskStatus, ChangeRequestStatus
from clerk.domain.states import (
    ALLOWED_ASK_TRANSITIONS,
    ALLOWED_CR_TRANSITIONS,
    InvalidStateTransitionError,
    accept_ask,
    approve_change_for_ask,
    ask_question_on_ask,
    can_transition_ask,
    can_transition_cr,
    classify_ask,
    decline_change_for_ask,
    invoice_ask,
    link_duplicate_ask,
    open_change_for_ask,
    publish_preview_for_ask,
    remind_decided_ask,
    send_change_order_for_ask,
    start_building_ask,
    swap_change_for_ask,
    ticket_ask,
    transition_ask,
    transition_cr,
)


def test_all_allowed_ask_transitions_succeed() -> None:
    """Every allowed AskStatus transition in the transition table must validate."""
    for current, targets in ALLOWED_ASK_TRANSITIONS.items():
        for target in targets:
            assert can_transition_ask(current, target) is True
            assert transition_ask(current, target) == target


def test_named_ask_transition_helpers() -> None:
    """Verify every named Ask transition helper."""
    assert classify_ask(AskStatus.RECEIVED) == AskStatus.CLASSIFIED
    assert ask_question_on_ask(AskStatus.CLASSIFIED) == AskStatus.QUESTION_PENDING
    assert classify_ask(AskStatus.QUESTION_PENDING) == AskStatus.CLASSIFIED
    assert ticket_ask(AskStatus.CLASSIFIED) == AskStatus.TICKETED
    assert open_change_for_ask(AskStatus.CLASSIFIED) == AskStatus.CHANGE_OPEN
    assert link_duplicate_ask(AskStatus.CLASSIFIED) == AskStatus.LINKED
    assert remind_decided_ask(AskStatus.CLASSIFIED) == AskStatus.REMINDED
    assert send_change_order_for_ask(AskStatus.CHANGE_OPEN) == AskStatus.CHANGE_SENT
    assert approve_change_for_ask(AskStatus.CHANGE_SENT) == AskStatus.APPROVED
    assert swap_change_for_ask(AskStatus.CHANGE_SENT) == AskStatus.SWAPPED
    assert decline_change_for_ask(AskStatus.CHANGE_SENT) == AskStatus.DECLINED
    assert start_building_ask(AskStatus.TICKETED) == AskStatus.BUILDING
    assert publish_preview_for_ask(AskStatus.BUILDING) == AskStatus.PREVIEW
    assert accept_ask(AskStatus.PREVIEW) == AskStatus.ACCEPTED
    assert invoice_ask(AskStatus.ACCEPTED) == AskStatus.INVOICED


def test_forbidden_ask_transitions_raise() -> None:
    """Every unlisted AskStatus transition must raise InvalidStateTransitionError."""
    for current in AskStatus:
        allowed = ALLOWED_ASK_TRANSITIONS.get(current, frozenset())
        for target in AskStatus:
            if target not in allowed:
                assert can_transition_ask(current, target) is False
                with pytest.raises(InvalidStateTransitionError) as exc_info:
                    transition_ask(current, target)
                assert exc_info.value.entity == "Ask"
                assert exc_info.value.current == current.value
                assert exc_info.value.target == target.value


def test_all_allowed_cr_transitions_succeed() -> None:
    """Every allowed ChangeRequestStatus transition in the transition table must validate."""
    for current, targets in ALLOWED_CR_TRANSITIONS.items():
        for target in targets:
            assert can_transition_cr(current, target) is True
            assert transition_cr(current, target) == target


def test_forbidden_cr_transitions_raise() -> None:
    """Every unlisted ChangeRequestStatus transition must raise InvalidStateTransitionError."""
    for current in ChangeRequestStatus:
        allowed = ALLOWED_CR_TRANSITIONS.get(current, frozenset())
        for target in ChangeRequestStatus:
            if target not in allowed:
                assert can_transition_cr(current, target) is False
                with pytest.raises(InvalidStateTransitionError) as exc_info:
                    transition_cr(current, target)
                assert exc_info.value.entity == "ChangeRequest"
                assert exc_info.value.current == current.value
                assert exc_info.value.target == target.value
