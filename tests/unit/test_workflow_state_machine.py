"""Unit tests for the 12-State Workflow State Machine (AD-013).

Validates the full transition graph, valid paths, invalid paths,
terminal state immutability, and state invariants.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-013
Ref: docs/architecture/ARCHITECTURE.md §11
"""

import pytest
from healthflow_domain import (
    AuthorizationCase,
    CaseId,
    CasePriority,
    InvalidWorkflowTransitionError,
    PatientId,
    PlanId,
    ProcedureType,
    VerificationStatus,
    WorkflowState,
    is_transition_allowed,
    validate_workflow_transition,
)


def _create_case(
    initial_state: WorkflowState = WorkflowState.INITIATED,
) -> AuthorizationCase:
    return AuthorizationCase(
        id=CaseId.generate(),
        patient_id=PatientId.generate(),
        insurance_plan_id=PlanId.generate(),
        procedure_type=ProcedureType.MRI_LUMBAR_SPINE,
        clinical_indication="Severe sciatica",
        priority=CasePriority.ROUTINE,
        current_state=initial_state,
    )


class TestWorkflowStateEnumeration:
    def test_exactly_twelve_states_defined(self) -> None:
        """Verify the exact 12 states required by AD-013 are defined."""
        expected_states = {
            "INITIATED",
            "GATHERING_INFORMATION",
            "VALIDATING",
            "PREPARING_SUBMISSION",
            "SUBMITTED",
            "MONITORING",
            "FOLLOW_UP_REQUIRED",
            "VERIFYING",
            "ESCALATED",
            "COMPLETED",
            "DENIED",
            "FAILED",
        }
        actual_states = {state.value for state in WorkflowState}
        assert actual_states == expected_states
        assert len(WorkflowState) == 12

    def test_terminal_states_flagged_correctly(self) -> None:
        """Verify only COMPLETED, DENIED, FAILED are terminal."""
        terminal_states = {s for s in WorkflowState if s.is_terminal}
        assert terminal_states == {
            WorkflowState.COMPLETED,
            WorkflowState.DENIED,
            WorkflowState.FAILED,
        }


class TestValidWorkflowTransitions:
    @pytest.mark.parametrize(
        "from_state, to_state, ver_status",
        [
            (WorkflowState.INITIATED, WorkflowState.GATHERING_INFORMATION, None),
            (WorkflowState.GATHERING_INFORMATION, WorkflowState.VALIDATING, None),
            (WorkflowState.GATHERING_INFORMATION, WorkflowState.ESCALATED, None),
            (WorkflowState.VALIDATING, WorkflowState.PREPARING_SUBMISSION, None),
            (WorkflowState.VALIDATING, WorkflowState.GATHERING_INFORMATION, None),
            (WorkflowState.VALIDATING, WorkflowState.ESCALATED, None),
            (WorkflowState.PREPARING_SUBMISSION, WorkflowState.SUBMITTED, None),
            (WorkflowState.PREPARING_SUBMISSION, WorkflowState.ESCALATED, None),
            (WorkflowState.SUBMITTED, WorkflowState.MONITORING, None),
            (WorkflowState.MONITORING, WorkflowState.VERIFYING, None),
            (WorkflowState.MONITORING, WorkflowState.FOLLOW_UP_REQUIRED, None),
            (WorkflowState.MONITORING, WorkflowState.ESCALATED, None),
            (WorkflowState.FOLLOW_UP_REQUIRED, WorkflowState.VALIDATING, None),
            (WorkflowState.FOLLOW_UP_REQUIRED, WorkflowState.ESCALATED, None),
            (
                WorkflowState.VERIFYING,
                WorkflowState.COMPLETED,
                VerificationStatus.CONFIRMED,
            ),
            (WorkflowState.VERIFYING, WorkflowState.DENIED, None),
            (WorkflowState.VERIFYING, WorkflowState.ESCALATED, None),
            (WorkflowState.ESCALATED, WorkflowState.GATHERING_INFORMATION, None),
            (WorkflowState.ESCALATED, WorkflowState.PREPARING_SUBMISSION, None),
            (WorkflowState.ESCALATED, WorkflowState.DENIED, None),
            (WorkflowState.ESCALATED, WorkflowState.FAILED, None),
        ],
    )
    def test_permitted_transitions_succeed(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
        ver_status: VerificationStatus | None,
    ) -> None:
        assert is_transition_allowed(from_state, to_state) is True
        validate_workflow_transition(
            from_state, to_state, verification_status=ver_status
        )

        case = _create_case(initial_state=from_state)
        transition = case.transition_to(
            to_state, verification_status=ver_status, actor="test_actor"
        )
        assert case.current_state == to_state
        assert transition.from_state == from_state
        assert transition.to_state == to_state


class TestProhibitedWorkflowTransitions:
    def test_cannot_transition_out_of_completed(self) -> None:
        case = _create_case(WorkflowState.COMPLETED)
        for state in WorkflowState:
            with pytest.raises(InvalidWorkflowTransitionError, match="terminal state"):
                case.transition_to(state)

    def test_cannot_transition_out_of_denied(self) -> None:
        case = _create_case(WorkflowState.DENIED)
        for state in WorkflowState:
            with pytest.raises(InvalidWorkflowTransitionError, match="terminal state"):
                case.transition_to(state)

    def test_cannot_transition_out_of_failed(self) -> None:
        case = _create_case(WorkflowState.FAILED)
        for state in WorkflowState:
            with pytest.raises(InvalidWorkflowTransitionError, match="terminal state"):
                case.transition_to(state)

    def test_cannot_skip_to_submitted_from_initiated(self) -> None:
        case = _create_case(WorkflowState.INITIATED)
        with pytest.raises(
            InvalidWorkflowTransitionError, match="not in the allowed graph"
        ):
            case.transition_to(WorkflowState.SUBMITTED)

    def test_cannot_skip_to_completed_from_initiated(self) -> None:
        case = _create_case(WorkflowState.INITIATED)
        with pytest.raises(InvalidWorkflowTransitionError):
            case.transition_to(
                WorkflowState.COMPLETED,
                verification_status=VerificationStatus.CONFIRMED,
            )

    def test_cannot_skip_to_completed_from_monitoring(self) -> None:
        case = _create_case(WorkflowState.MONITORING)
        with pytest.raises(InvalidWorkflowTransitionError):
            case.transition_to(
                WorkflowState.COMPLETED,
                verification_status=VerificationStatus.CONFIRMED,
            )
