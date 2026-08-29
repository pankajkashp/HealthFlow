"""HealthFlow Domain External System Models.

Strongly-typed data transfer objects representing external system information
at the boundary between the application layer and external healthcare systems.

Ref: docs/architecture/ARCHITECTURE.md §6, §13
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EhrPatientRecord:
    """Patient clinical and demographic record retrieved from synthetic EHR."""

    patient_id: str
    name_reference: str
    ehr_reference: str
    clinical_notes_summary: str
    active_diagnoses: list[str] = field(default_factory=list)
    conservative_therapy_completed: bool = False
    conservative_therapy_duration_weeks: int = 0
    is_synthetic: bool = True

    def __post_init__(self) -> None:
        if not self.is_synthetic:
            raise ValueError("EhrPatientRecord must be marked is_synthetic=True.")


@dataclass(frozen=True)
class PayerCoverageRecord:
    """Coverage and eligibility record from synthetic insurance/payer system."""

    plan_id: str
    patient_id: str
    insurer_name: str
    is_active: bool
    in_network: bool
    requires_prior_authorization: bool
    coverage_notes: str


@dataclass(frozen=True)
class ProcedureRequirements:
    """Prior authorization clinical and documentation requirements for a procedure."""

    plan_id: str
    procedure_type: str
    required_document_types: list[str]
    required_clinical_fields: list[str]
    minimum_conservative_therapy_weeks: int
    requires_specialist_referral: bool


@dataclass(frozen=True)
class DocumentMetadata:
    """Metadata describing an archived clinical document."""

    document_reference: str
    document_type: str
    patient_id: str
    created_date: str
    author_reference: str
    file_format: str
    content_hash: str


@dataclass(frozen=True)
class DocumentContent:
    """Synthetic document content and associated metadata."""

    document_reference: str
    document_type: str
    text_content: str
    metadata: DocumentMetadata


@dataclass(frozen=True)
class PortalSubmissionPayload:
    """Electronic authorization package submitted to the payer portal."""

    patient_id: str
    plan_id: str
    procedure_type: str
    clinical_indication: str
    document_references: list[str]
    requesting_physician: str


@dataclass(frozen=True)
class PortalSubmissionAck:
    """Immediate acknowledgment returned by portal on submission attempt."""

    success: bool
    submission_reference: str | None
    ack_status: str
    received_timestamp: str = field(default_factory=_utc_now_iso)
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class PortalStatusRecord:
    """Authoritative decision status queried from the payer portal."""

    submission_reference: str
    portal_status: str
    status_message: str
    determination_date: str | None = None
    additional_info_requested: list[str] | None = None


@dataclass(frozen=True)
class ExternalVerificationResult:
    """Result of an independent outcome verification check against external systems."""

    verified: bool
    submission_reference: str
    expected_status: str
    actual_status: str
    verification_source: str
    details: str
    verified_at: str = field(default_factory=_utc_now_iso)
