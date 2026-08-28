"""HealthFlow Domain Entities.

Core administrative entities representing patients, insurance, authorization cases,
workflow transitions, submissions, verifications, escalations, and audit logs.

Invariants:
- All patient records must be synthetic (is_synthetic == True).
- State transitions on AuthorizationCase must pass deterministic validation.
- All entities use strongly-typed identifiers.

Ref: docs/architecture/ARCHITECTURE.md §5
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from healthflow_domain.enums import (
    AuditEventType,
    CasePriority,
    EscalationReason,
    ProcedureType,
    VerificationStatus,
    WorkflowState,
)
from healthflow_domain.exceptions import (
    DataBoundaryViolationError,
    DomainValidationError,
    InvariantViolationError,
)
from healthflow_domain.identifiers import (
    AuditId,
    CaseId,
    EscalationId,
    PatientId,
    PlanId,
    SubmissionId,
    TransitionId,
    VerificationId,
)
from healthflow_domain.workflow_state import validate_workflow_transition


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Patient:
    """Represents a synthetic patient, subject of a prior-authorization workflow."""

    id: PatientId
    name_reference: str
    ehr_reference: str
    is_synthetic: bool = True
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.is_synthetic:
            raise DataBoundaryViolationError(
                f"Patient '{self.id}' is not marked synthetic. Real PHI is prohibited."
            )
        if not self.name_reference or not self.name_reference.strip():
            raise DomainValidationError("Patient name_reference cannot be empty.")
        if not self.ehr_reference or not self.ehr_reference.strip():
            raise DomainValidationError("Patient ehr_reference cannot be empty.")


@dataclass
class InsurancePlan:
    """Represents the patient's synthetic insurance plan and insurer identity."""

    id: PlanId
    patient_id: PatientId
    insurer_reference: str
    plan_type: str
    member_reference: str
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.insurer_reference or not self.insurer_reference.strip():
            raise DomainValidationError(
                "InsurancePlan insurer_reference cannot be empty."
            )
        if not self.member_reference or not self.member_reference.strip():
            raise DomainValidationError(
                "InsurancePlan member_reference cannot be empty."
            )


@dataclass
class WorkflowTransition:
    """Represents an immutable record of a state transition."""

    id: TransitionId
    case_id: CaseId
    from_state: WorkflowState
    to_state: WorkflowState
    reason: str
    actor: str
    transitioned_at: datetime = field(default_factory=_now)


@dataclass
class AuthorizationCase:
    """Aggregate root for an MRI prior-authorization administrative workflow."""

    id: CaseId
    patient_id: PatientId
    insurance_plan_id: PlanId
    procedure_type: ProcedureType
    clinical_indication: str
    priority: CasePriority = CasePriority.ROUTINE
    current_state: WorkflowState = WorkflowState.INITIATED
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.clinical_indication or not self.clinical_indication.strip():
            raise DomainValidationError("clinical_indication cannot be empty.")

    def transition_to(
        self,
        to_state: WorkflowState,
        verification_status: VerificationStatus | None = None,
        actor: str = "system",
        reason: str = "",
    ) -> WorkflowTransition:
        """Attempt to transition the case to a new state.

        Validates all transition rules and updates current_state if legal.
        Returns a WorkflowTransition entity for persistence and audit.
        """
        validate_workflow_transition(
            from_state=self.current_state,
            to_state=to_state,
            verification_status=verification_status,
        )

        from_state = self.current_state
        self.current_state = to_state
        self.updated_at = _now()

        return WorkflowTransition(
            id=TransitionId.generate(),
            case_id=self.id,
            from_state=from_state,
            to_state=to_state,
            reason=reason
            or f"Transitioned from {from_state.value} to {to_state.value}",
            actor=actor,
            transitioned_at=self.updated_at,
        )


@dataclass
class SubmissionRecord:
    """Represents a submitted prior-authorization request to the external portal."""

    id: SubmissionId
    case_id: CaseId
    submission_reference: str
    payload_hash: str
    initial_status: str
    submitted_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.submission_reference or not self.submission_reference.strip():
            raise DomainValidationError(
                "SubmissionRecord submission_reference cannot be empty."
            )
        if not self.payload_hash or not self.payload_hash.strip():
            raise DomainValidationError(
                "SubmissionRecord payload_hash cannot be empty."
            )


@dataclass
class VerificationRecord:
    """Represents an independent verification check of a claimed outcome."""

    id: VerificationId
    case_id: CaseId
    submission_reference: str
    status: VerificationStatus
    verification_details: str
    verified_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.submission_reference or not self.submission_reference.strip():
            raise DomainValidationError(
                "VerificationRecord submission_reference cannot be empty."
            )


@dataclass
class EscalationRecord:
    """Represents a human escalation trigger when autonomous progress halts."""

    id: EscalationId
    case_id: CaseId
    reason: EscalationReason
    from_state: WorkflowState
    notes: str
    escalated_at: datetime = field(default_factory=_now)
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    resolved_by: str | None = None

    def resolve(self, resolution_notes: str, resolved_by: str) -> None:
        """Resolve this escalation with human input."""
        if not resolution_notes or not resolution_notes.strip():
            raise DomainValidationError(
                "resolution_notes cannot be empty when resolving."
            )
        if not resolved_by or not resolved_by.strip():
            raise DomainValidationError("resolved_by cannot be empty when resolving.")
        if self.resolved_at is not None:
            raise InvariantViolationError("Escalation has already been resolved.")

        self.resolved_at = _now()
        self.resolution_notes = resolution_notes
        self.resolved_by = resolved_by


@dataclass
class AuditRecord:
    """Immutable audit trail record for significant domain and system events."""

    id: AuditId
    event_type: AuditEventType
    case_id: CaseId | None
    details: dict[str, Any]
    actor: str
    timestamp: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise DomainValidationError("AuditRecord actor cannot be empty.")
