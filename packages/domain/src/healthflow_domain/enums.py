"""HealthFlow Domain Enums.

Defines all enumerated value types across the HealthFlow domain.
All 12 workflow states are defined here per AD-013.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-013
Ref: docs/architecture/ARCHITECTURE.md §11
"""

from enum import StrEnum


class WorkflowState(StrEnum):
    """The 12 authoritative workflow states for MRI Prior Authorization (AD-013).

    Terminal states: COMPLETED, DENIED, FAILED.
    """

    INITIATED = "INITIATED"
    GATHERING_INFORMATION = "GATHERING_INFORMATION"
    VALIDATING = "VALIDATING"
    PREPARING_SUBMISSION = "PREPARING_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    MONITORING = "MONITORING"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    VERIFYING = "VERIFYING"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        """Return True if this state is a terminal workflow state."""
        return self in (
            WorkflowState.COMPLETED,
            WorkflowState.DENIED,
            WorkflowState.FAILED,
        )


class ProcedureType(StrEnum):
    """Supported MRI procedure categories (MVP scope: MRI Prior Authorization)."""

    MRI_BRAIN = "MRI_BRAIN"
    MRI_LUMBAR_SPINE = "MRI_LUMBAR_SPINE"
    MRI_CERVICAL_SPINE = "MRI_CERVICAL_SPINE"
    MRI_KNEE = "MRI_KNEE"
    MRI_SHOULDER = "MRI_SHOULDER"
    MRI_ABDOMEN = "MRI_ABDOMEN"
    MRI_PELVIS = "MRI_PELVIS"


class VerificationStatus(StrEnum):
    """Outcome status from an independent verification check (AD-004, AD-014)."""

    CONFIRMED = "CONFIRMED"
    NOT_CONFIRMED = "NOT_CONFIRMED"
    ERROR = "ERROR"


class CasePriority(StrEnum):
    """Priority level for an authorization case."""

    ROUTINE = "ROUTINE"
    URGENT = "URGENT"


class EscalationReason(StrEnum):
    """Categorized triggers for human escalation."""

    AMBIGUOUS_INFORMATION = "AMBIGUOUS_INFORMATION"
    CONFLICTING_SOURCES = "CONFLICTING_SOURCES"
    SAFETY_GATE_FAILURE = "SAFETY_GATE_FAILURE"
    CLINICAL_DECISION_REQUIRED = "CLINICAL_DECISION_REQUIRED"
    UNAUTHORIZED_PERMISSION = "UNAUTHORIZED_PERMISSION"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    HUMAN_REQUESTED = "HUMAN_REQUESTED"


class AuditEventType(StrEnum):
    """Types of auditable domain and system events."""

    CASE_CREATED = "CASE_CREATED"
    STATE_TRANSITION = "STATE_TRANSITION"
    TOOL_INVOKED = "TOOL_INVOKED"
    VALIDATION_EXECUTED = "VALIDATION_EXECUTED"
    SAFETY_GATE_EVALUATED = "SAFETY_GATE_EVALUATED"
    SUBMISSION_SENT = "SUBMISSION_SENT"
    STATUS_POLLED = "STATUS_POLLED"
    VERIFICATION_PERFORMED = "VERIFICATION_PERFORMED"
    ESCALATION_TRIGGERED = "ESCALATION_TRIGGERED"
    ESCALATION_RESOLVED = "ESCALATION_RESOLVED"
