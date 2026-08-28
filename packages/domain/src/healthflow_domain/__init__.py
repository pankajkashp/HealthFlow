"""HealthFlow Domain Layer.

Core business concepts, port interfaces, value objects, and transition rules.
This layer has ZERO external framework dependencies.

Ref: docs/architecture/ARCHITECTURE.md §2.4, §4.4
"""

from healthflow_domain.entities import (
    AuditRecord,
    AuthorizationCase,
    EscalationRecord,
    InsurancePlan,
    Patient,
    SubmissionRecord,
    VerificationRecord,
    WorkflowTransition,
)
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
    DomainError,
    DomainValidationError,
    EntityNotFoundError,
    InvalidWorkflowTransitionError,
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
from healthflow_domain.ports import (
    AuditRepository,
    AuthorizationCaseRepository,
    EscalationRepository,
    InsurancePlanRepository,
    PatientRepository,
    SubmissionRepository,
    UnitOfWork,
    VerificationRepository,
    WorkflowStateRepository,
)
from healthflow_domain.workflow_state import (
    ALLOWED_TRANSITIONS,
    is_transition_allowed,
    validate_workflow_transition,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "AuditEventType",
    "AuditId",
    "AuditRecord",
    "AuditRepository",
    "AuthorizationCase",
    "AuthorizationCaseRepository",
    "CaseId",
    "CasePriority",
    "DataBoundaryViolationError",
    "DomainError",
    "DomainValidationError",
    "EntityNotFoundError",
    "EscalationId",
    "EscalationReason",
    "EscalationRecord",
    "EscalationRepository",
    "InsurancePlan",
    "InsurancePlanRepository",
    "InvalidWorkflowTransitionError",
    "InvariantViolationError",
    "Patient",
    "PatientId",
    "PatientRepository",
    "PlanId",
    "ProcedureType",
    "SubmissionId",
    "SubmissionRecord",
    "SubmissionRepository",
    "TransitionId",
    "UnitOfWork",
    "VerificationId",
    "VerificationRecord",
    "VerificationRepository",
    "VerificationStatus",
    "WorkflowState",
    "WorkflowStateRepository",
    "WorkflowTransition",
    "is_transition_allowed",
    "validate_workflow_transition",
]
