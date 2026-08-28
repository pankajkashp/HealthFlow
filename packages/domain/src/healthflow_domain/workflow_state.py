"""HealthFlow Workflow State Machine & Transition Rules.

Implements the authoritative 12-state transition matrix and invariants resolved in AD-013.
Enforces the core DONE principle: COMPLETED is only reachable from VERIFYING with
a verified outcome.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-013
Ref: docs/architecture/ARCHITECTURE.md §11.3
"""

from typing import Final

from healthflow_domain.enums import VerificationStatus, WorkflowState
from healthflow_domain.exceptions import InvalidWorkflowTransitionError

# The authoritative transition map defined in AD-013
ALLOWED_TRANSITIONS: Final[dict[WorkflowState, frozenset[WorkflowState]]] = {
    WorkflowState.INITIATED: frozenset(
        {
            WorkflowState.GATHERING_INFORMATION,
        }
    ),
    WorkflowState.GATHERING_INFORMATION: frozenset(
        {
            WorkflowState.VALIDATING,
            WorkflowState.ESCALATED,
        }
    ),
    WorkflowState.VALIDATING: frozenset(
        {
            WorkflowState.PREPARING_SUBMISSION,
            WorkflowState.GATHERING_INFORMATION,
            WorkflowState.ESCALATED,
        }
    ),
    WorkflowState.PREPARING_SUBMISSION: frozenset(
        {
            WorkflowState.SUBMITTED,
            WorkflowState.ESCALATED,
        }
    ),
    WorkflowState.SUBMITTED: frozenset(
        {
            WorkflowState.MONITORING,
        }
    ),
    WorkflowState.MONITORING: frozenset(
        {
            WorkflowState.VERIFYING,
            WorkflowState.FOLLOW_UP_REQUIRED,
            WorkflowState.ESCALATED,
        }
    ),
    WorkflowState.FOLLOW_UP_REQUIRED: frozenset(
        {
            WorkflowState.VALIDATING,
            WorkflowState.ESCALATED,
        }
    ),
    WorkflowState.VERIFYING: frozenset(
        {
            WorkflowState.COMPLETED,
            WorkflowState.DENIED,
            WorkflowState.ESCALATED,
        }
    ),
    WorkflowState.ESCALATED: frozenset(
        {
            WorkflowState.GATHERING_INFORMATION,
            WorkflowState.PREPARING_SUBMISSION,
            WorkflowState.DENIED,
            WorkflowState.FAILED,
        }
    ),
    # Terminal states have NO outgoing transitions
    WorkflowState.COMPLETED: frozenset(),
    WorkflowState.DENIED: frozenset(),
    WorkflowState.FAILED: frozenset(),
}


def is_transition_allowed(from_state: WorkflowState, to_state: WorkflowState) -> bool:
    """Return True if the state transition exists in the allowed transition graph."""
    allowed_destinations = ALLOWED_TRANSITIONS.get(from_state, frozenset())
    return to_state in allowed_destinations


def validate_workflow_transition(
    from_state: WorkflowState,
    to_state: WorkflowState,
    verification_status: VerificationStatus | None = None,
) -> None:
    """Validate a requested workflow state transition against all domain rules.

    Raises:
        InvalidWorkflowTransitionError: If the transition is illegal or violates invariants.
    """
    # 1. Check if source is already terminal
    if from_state.is_terminal:
        raise InvalidWorkflowTransitionError(
            from_state=from_state.value,
            to_state=to_state.value,
            reason=f"Source state '{from_state.value}' is a terminal state. No transitions allowed.",
        )

    # 2. Check transition graph
    if not is_transition_allowed(from_state, to_state):
        raise InvalidWorkflowTransitionError(
            from_state=from_state.value,
            to_state=to_state.value,
            reason=f"Transition from {from_state.value} to {to_state.value} is not in the allowed graph.",
        )

    # 3. Specific Invariant: COMPLETED requires VERIFYING + VerificationStatus.CONFIRMED
    if to_state == WorkflowState.COMPLETED:
        if from_state != WorkflowState.VERIFYING:
            raise InvalidWorkflowTransitionError(
                from_state=from_state.value,
                to_state=to_state.value,
                reason="COMPLETED can ONLY be reached from VERIFYING.",
            )
        if verification_status != VerificationStatus.CONFIRMED:
            raise InvalidWorkflowTransitionError(
                from_state=from_state.value,
                to_state=to_state.value,
                reason="COMPLETED requires independent VerificationStatus.CONFIRMED (DONE principle).",
            )
