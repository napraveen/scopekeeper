"""State machines for Ask and ChangeRequest lifecycles."""

from __future__ import annotations

from clerk.domain.models import AskStatus, ChangeRequestStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an Ask or ChangeRequest attempts a forbidden state transition."""

    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(
            f"Invalid {entity} state transition: {current!r} -> {target!r}"
        )
        self.entity = entity
        self.current = current
        self.target = target


ALLOWED_ASK_TRANSITIONS: dict[AskStatus, frozenset[AskStatus]] = {
    AskStatus.RECEIVED: frozenset({AskStatus.CLASSIFIED}),
    AskStatus.CLASSIFIED: frozenset(
        {
            AskStatus.QUESTION_PENDING,
            AskStatus.TICKETED,
            AskStatus.CHANGE_OPEN,
            AskStatus.LINKED,
            AskStatus.REMINDED,
            AskStatus.ACCEPTED,  # e.g. goodwill granted directly
        }
    ),
    AskStatus.QUESTION_PENDING: frozenset({AskStatus.CLASSIFIED}),
    AskStatus.CHANGE_OPEN: frozenset(
        {
            AskStatus.CHANGE_SENT,
            AskStatus.DECLINED,
            AskStatus.ACCEPTED,  # goodwill granted on small out-of-scope ask
        }
    ),
    AskStatus.CHANGE_SENT: frozenset(
        {
            AskStatus.APPROVED,
            AskStatus.SWAPPED,
            AskStatus.DECLINED,
        }
    ),
    AskStatus.TICKETED: frozenset({AskStatus.BUILDING}),
    AskStatus.APPROVED: frozenset({AskStatus.BUILDING, AskStatus.INVOICED}),
    AskStatus.SWAPPED: frozenset({AskStatus.BUILDING}),
    AskStatus.BUILDING: frozenset({AskStatus.PREVIEW}),
    AskStatus.PREVIEW: frozenset({AskStatus.ACCEPTED}),
    AskStatus.ACCEPTED: frozenset({AskStatus.INVOICED}),
    AskStatus.LINKED: frozenset(),
    AskStatus.REMINDED: frozenset(),
    AskStatus.DECLINED: frozenset(),
    AskStatus.INVOICED: frozenset(),
}

ALLOWED_CR_TRANSITIONS: dict[ChangeRequestStatus, frozenset[ChangeRequestStatus]] = {
    ChangeRequestStatus.ESTIMATING: frozenset(
        {
            ChangeRequestStatus.AWAITING_CONFIRMATION,
            ChangeRequestStatus.AWAITING_APPROVAL,
            ChangeRequestStatus.SENT,  # in-envelope high-confidence P50 auto-sent
            ChangeRequestStatus.CLOSED,
        }
    ),
    ChangeRequestStatus.AWAITING_CONFIRMATION: frozenset(
        {
            ChangeRequestStatus.AWAITING_APPROVAL,
            ChangeRequestStatus.SENT,  # confirmed and inside envelope
            ChangeRequestStatus.CLOSED,
        }
    ),
    ChangeRequestStatus.AWAITING_APPROVAL: frozenset(
        {
            ChangeRequestStatus.SENT,
            ChangeRequestStatus.CLOSED,  # declined by @account-manager
        }
    ),
    ChangeRequestStatus.SENT: frozenset(
        {
            ChangeRequestStatus.DECIDED,
            ChangeRequestStatus.CLOSED,
        }
    ),
    ChangeRequestStatus.DECIDED: frozenset({ChangeRequestStatus.CLOSED}),
    ChangeRequestStatus.CLOSED: frozenset(),
}


def can_transition_ask(current: AskStatus, target: AskStatus) -> bool:
    """Return True if transitioning an Ask from `current` to `target` is allowed."""
    return target in ALLOWED_ASK_TRANSITIONS.get(current, frozenset())


def transition_ask(current: AskStatus, target: AskStatus) -> AskStatus:
    """Validate and return the new AskStatus, or raise InvalidStateTransitionError."""
    if not can_transition_ask(current, target):
        raise InvalidStateTransitionError("Ask", current.value, target.value)
    return target


def can_transition_cr(
    current: ChangeRequestStatus, target: ChangeRequestStatus
) -> bool:
    """Return True if transitioning a ChangeRequest from `current` to `target` is allowed."""
    return target in ALLOWED_CR_TRANSITIONS.get(current, frozenset())


def transition_cr(
    current: ChangeRequestStatus, target: ChangeRequestStatus
) -> ChangeRequestStatus:
    """Validate and return the new ChangeRequestStatus, or raise InvalidStateTransitionError."""
    if not can_transition_cr(current, target):
        raise InvalidStateTransitionError("ChangeRequest", current.value, target.value)
    return target


# ── Named Transition Helpers ──────────────────────────────────────────────────


def classify_ask(current: AskStatus) -> AskStatus:
    """Transition an ask from received or question_pending to classified."""
    return transition_ask(current, AskStatus.CLASSIFIED)


def ask_question_on_ask(current: AskStatus) -> AskStatus:
    """Transition a classified ask to question_pending."""
    return transition_ask(current, AskStatus.QUESTION_PENDING)


def ticket_ask(current: AskStatus) -> AskStatus:
    """Transition a classified DEFECT or IN_SCOPE ask to ticketed."""
    return transition_ask(current, AskStatus.TICKETED)


def open_change_for_ask(current: AskStatus) -> AskStatus:
    """Transition a classified OUT_OF_SCOPE ask to change_open."""
    return transition_ask(current, AskStatus.CHANGE_OPEN)


def link_duplicate_ask(current: AskStatus) -> AskStatus:
    """Transition a classified DUPLICATE ask to linked."""
    return transition_ask(current, AskStatus.LINKED)


def remind_decided_ask(current: AskStatus) -> AskStatus:
    """Transition a classified ALREADY_DECIDED ask to reminded."""
    return transition_ask(current, AskStatus.REMINDED)


def send_change_order_for_ask(current: AskStatus) -> AskStatus:
    """Transition a change_open ask to change_sent."""
    return transition_ask(current, AskStatus.CHANGE_SENT)


def approve_change_for_ask(current: AskStatus) -> AskStatus:
    """Transition a change_sent ask to approved."""
    return transition_ask(current, AskStatus.APPROVED)


def swap_change_for_ask(current: AskStatus) -> AskStatus:
    """Transition a change_sent ask to swapped."""
    return transition_ask(current, AskStatus.SWAPPED)


def decline_change_for_ask(current: AskStatus) -> AskStatus:
    """Transition a change_open or change_sent ask to declined."""
    return transition_ask(current, AskStatus.DECLINED)


def start_building_ask(current: AskStatus) -> AskStatus:
    """Transition a ticketed, approved, or swapped ask to building."""
    return transition_ask(current, AskStatus.BUILDING)


def publish_preview_for_ask(current: AskStatus) -> AskStatus:
    """Transition a building ask to preview."""
    return transition_ask(current, AskStatus.PREVIEW)


def accept_ask(current: AskStatus) -> AskStatus:
    """Transition a preview (or goodwill) ask to accepted."""
    return transition_ask(current, AskStatus.ACCEPTED)


def invoice_ask(current: AskStatus) -> AskStatus:
    """Transition an accepted or approved paid change ask to invoiced."""
    return transition_ask(current, AskStatus.INVOICED)
