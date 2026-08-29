"""HealthFlow Application Agent Tool Result Models.

Defines the exact structured result schemas returned by the 9 approved agent tools.
Per AD-014, the agent never receives raw exceptions. All failures are returned
as structured result objects with error_code and error_message.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-014
Ref: docs/architecture/ARCHITECTURE.md §7.2
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PatientRecordResult:
    """Output structure for Tool 1: get_patient_record."""

    success: bool
    patient_id: str | None = None
    name_reference: str | None = None
    ehr_reference: str | None = None
    is_synthetic: bool = True
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class InsurancePlanResult:
    """Output structure for Tool 2: get_insurance_plan."""

    success: bool
    plan_id: str | None = None
    insurer_reference: str | None = None
    plan_type: str | None = None
    member_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class AuthorizationRequirementsResult:
    """Output structure for Tool 3: get_authorization_requirements."""

    success: bool
    requirements_id: str | None = None
    required_document_types: list[str] = field(default_factory=list)
    required_information_fields: list[str] = field(default_factory=list)
    retrieval_confidence: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class DocumentResult:
    """Output structure for Tool 4: get_required_document."""

    success: bool
    document_id: str | None = None
    document_type: str | None = None
    content_reference: str | None = None
    metadata: dict[str, str] | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Output structure for Tool 5: validate_authorization_package."""

    is_valid: bool
    missing_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    validation_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SubmissionResult:
    """Output structure for Tool 6: submit_authorization_request."""

    success: bool
    submission_reference: str | None = None
    initial_status: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class AuthorizationStatusResult:
    """Output structure for Tool 7: get_authorization_status."""

    success: bool
    status: str | None = None
    status_message: str | None = None
    additional_info_required: list[str] | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class VerificationResult:
    """Output structure for Tool 8: verify_authorization_outcome."""

    verified: bool
    actual_status: str
    verification_source: str
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class EscalationResult:
    """Output structure for Tool 9: request_escalation."""

    success: bool
    escalation_id: str | None = None
    workflow_state: str = "ESCALATED"
    error_code: str | None = None
    error_message: str | None = None
