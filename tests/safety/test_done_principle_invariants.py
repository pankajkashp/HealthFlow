"""Safety invariant tests for the DONE principle (PRS §7, §12, AD-013).

CRITICAL PRODUCT PRINCIPLE:
"The agent cannot say DONE. The environment has to prove DONE."
A tool response saying "submitted successfully" does NOT prove completion.
The authoritative simulated environment must confirm the expected outcome.

COMPLETED can ONLY be reached from VERIFYING when the VerificationProvider
returns CONFIRMED. All other transition attempts MUST be rejected deterministically.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-013
Ref: docs/architecture/ARCHITECTURE.md §11.3
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §12
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
)


def _create_case(state: WorkflowState) -> AuthorizationCase:
    return AuthorizationCase(
        id=CaseId.generate(),
        patient_id=PatientId.generate(),
        insurance_plan_id=PlanId.generate(),
        procedure_type=ProcedureType.MRI_BRAIN,
        clinical_indication="Severe intractable headaches",
        priority=CasePriority.ROUTINE,
        current_state=state,
    )


class TestDonePrincipleSafetyInvariants:
    """Verifies that the DONE principle is enforced as an unbypassable domain invariant."""

    def test_verifying_to_completed_with_confirmed_succeeds(self) -> None:
        """Legitimate path: VERIFYING -> COMPLETED with VerificationStatus.CONFIRMED."""
        case = _create_case(WorkflowState.VERIFYING)
        transition = case.transition_to(
            WorkflowState.COMPLETED,
            verification_status=VerificationStatus.CONFIRMED,
            actor="verification_engine",
            reason="Outcome independently verified in portal.",
        )
        assert case.current_state == WorkflowState.COMPLETED
        assert transition.to_state == WorkflowState.COMPLETED

    def test_verifying_to_completed_without_status_fails(self) -> None:
        """VERIFYING -> COMPLETED without verification status must be rejected."""
        case = _create_case(WorkflowState.VERIFYING)
        with pytest.raises(
            InvalidWorkflowTransitionError,
            match="COMPLETED requires independent VerificationStatus.CONFIRMED",
        ):
            case.transition_to(WorkflowState.COMPLETED, verification_status=None)

    def test_verifying_to_completed_with_not_confirmed_fails(self) -> None:
        """VERIFYING -> COMPLETED with NOT_CONFIRMED status must be rejected."""
        case = _create_case(WorkflowState.VERIFYING)
        with pytest.raises(
            InvalidWorkflowTransitionError,
            match="COMPLETED requires independent VerificationStatus.CONFIRMED",
        ):
            case.transition_to(
                WorkflowState.COMPLETED,
                verification_status=VerificationStatus.NOT_CONFIRMED,
            )

    def test_verifying_to_completed_with_error_status_fails(self) -> None:
        """VERIFYING -> COMPLETED with ERROR status must be rejected."""
        case = _create_case(WorkflowState.VERIFYING)
        with pytest.raises(
            InvalidWorkflowTransitionError,
            match="COMPLETED requires independent VerificationStatus.CONFIRMED",
        ):
            case.transition_to(
                WorkflowState.COMPLETED,
                verification_status=VerificationStatus.ERROR,
            )

    @pytest.mark.parametrize(
        "non_verifying_state",
        [
            WorkflowState.INITIATED,
            WorkflowState.GATHERING_INFORMATION,
            WorkflowState.VALIDATING,
            WorkflowState.PREPARING_SUBMISSION,
            WorkflowState.SUBMITTED,
            WorkflowState.MONITORING,
            WorkflowState.FOLLOW_UP_REQUIRED,
            WorkflowState.ESCALATED,
        ],
    )
    def test_all_non_verifying_states_cannot_transition_to_completed(
        self, non_verifying_state: WorkflowState
    ) -> None:
        """Zero tolerance: No state other than VERIFYING can ever transition to COMPLETED."""
        case = _create_case(non_verifying_state)
        with pytest.raises(InvalidWorkflowTransitionError):
            case.transition_to(
                WorkflowState.COMPLETED,
                verification_status=VerificationStatus.CONFIRMED,
            )

    def test_submission_cannot_bypass_monitoring_and_verification(self) -> None:
        """A SUBMITTED state cannot jump directly to COMPLETED."""
        case = _create_case(WorkflowState.SUBMITTED)
        with pytest.raises(InvalidWorkflowTransitionError):
            case.transition_to(
                WorkflowState.COMPLETED,
                verification_status=VerificationStatus.CONFIRMED,
            )
