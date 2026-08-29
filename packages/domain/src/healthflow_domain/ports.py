"""HealthFlow Domain Ports & Repository Interfaces.

Defines repository and Unit of Work interfaces, as well as external system
ports (EHR, Payer, Document Store, Authorization Portal, Verification Provider)
as typing.Protocols.

Ref: docs/architecture/ARCHITECTURE.md §6, §13, §14
"""

from collections.abc import Sequence
from typing import Protocol, Self

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
from healthflow_domain.enums import ProcedureType
from healthflow_domain.external_models import (
    DocumentContent,
    DocumentMetadata,
    EhrPatientRecord,
    ExternalVerificationResult,
    PayerCoverageRecord,
    PortalStatusRecord,
    PortalSubmissionAck,
    PortalSubmissionPayload,
    ProcedureRequirements,
)
from healthflow_domain.identifiers import (
    CaseId,
    EscalationId,
    PatientId,
    PlanId,
    SubmissionId,
    VerificationId,
)


class PatientRepository(Protocol):
    """Port for retrieving and saving synthetic patient records in internal database."""

    def get_by_id(self, patient_id: PatientId) -> Patient | None: ...

    def get_by_ehr_reference(self, ehr_reference: str) -> Patient | None: ...

    def save(self, patient: Patient) -> None: ...


class InsurancePlanRepository(Protocol):
    """Port for retrieving and saving insurance plan records in internal database."""

    def get_by_id(self, plan_id: PlanId) -> InsurancePlan | None: ...

    def get_by_patient_id(self, patient_id: PatientId) -> Sequence[InsurancePlan]: ...

    def save(self, plan: InsurancePlan) -> None: ...


class AuthorizationCaseRepository(Protocol):
    """Port for persisting and querying AuthorizationCase aggregate roots."""

    def get_by_id(self, case_id: CaseId) -> AuthorizationCase | None: ...

    def list_all(
        self, limit: int = 50, offset: int = 0
    ) -> Sequence[AuthorizationCase]: ...

    def save(self, case: AuthorizationCase) -> None: ...


class WorkflowStateRepository(Protocol):
    """Port for tracking and querying workflow transitions."""

    def record_transition(self, transition: WorkflowTransition) -> None: ...

    def list_by_case_id(self, case_id: CaseId) -> Sequence[WorkflowTransition]: ...


class SubmissionRepository(Protocol):
    """Port for storing and retrieving portal submission records."""

    def get_by_id(self, submission_id: SubmissionId) -> SubmissionRecord | None: ...

    def get_by_reference(self, reference: str) -> SubmissionRecord | None: ...

    def list_by_case_id(self, case_id: CaseId) -> Sequence[SubmissionRecord]: ...

    def save(self, record: SubmissionRecord) -> None: ...


class VerificationRepository(Protocol):
    """Port for storing and querying independent verification records."""

    def get_by_id(
        self, verification_id: VerificationId
    ) -> VerificationRecord | None: ...

    def list_by_case_id(self, case_id: CaseId) -> Sequence[VerificationRecord]: ...

    def save(self, record: VerificationRecord) -> None: ...


class EscalationRepository(Protocol):
    """Port for storing, querying, and updating human escalation records."""

    def get_by_id(self, escalation_id: EscalationId) -> EscalationRecord | None: ...

    def list_by_case_id(self, case_id: CaseId) -> Sequence[EscalationRecord]: ...

    def save(self, record: EscalationRecord) -> None: ...


class AuditRepository(Protocol):
    """Port for appending and querying immutable audit trail records."""

    def record_event(self, record: AuditRecord) -> None: ...

    def list_by_case_id(self, case_id: CaseId) -> Sequence[AuditRecord]: ...


class UnitOfWork(Protocol):
    """Unit of Work interface managing transactional boundaries."""

    patients: PatientRepository
    insurance_plans: InsurancePlanRepository
    cases: AuthorizationCaseRepository
    workflow_states: WorkflowStateRepository
    submissions: SubmissionRepository
    verifications: VerificationRepository
    escalations: EscalationRepository
    audits: AuditRepository

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


# ==============================================================================
# External System Ports (Phase 3)
# ==============================================================================


class EhrPort(Protocol):
    """Port for interacting with external Electronic Health Record system."""

    def get_patient_record(self, patient_id: PatientId) -> EhrPatientRecord | None: ...

    def get_clinical_history(self, patient_id: PatientId) -> Sequence[str]: ...


class PayerPort(Protocol):
    """Port for interacting with external insurance payer system."""

    def get_coverage_status(
        self, patient_id: PatientId, plan_id: PlanId
    ) -> PayerCoverageRecord | None: ...

    def get_prior_auth_requirements(
        self, plan_id: PlanId, procedure_type: ProcedureType
    ) -> ProcedureRequirements | None: ...


class DocumentStorePort(Protocol):
    """Port for retrieving clinical documentation from external document store."""

    def get_document_metadata(
        self, document_reference: str
    ) -> DocumentMetadata | None: ...

    def get_document_content(
        self, document_reference: str
    ) -> DocumentContent | None: ...


class AuthorizationGatewayPort(Protocol):
    """Port for submitting requests to external authorization portal (Mutating)."""

    def submit_authorization(
        self, payload: PortalSubmissionPayload
    ) -> PortalSubmissionAck: ...


class AuthorizationStatusGatewayPort(Protocol):
    """Port for querying current status from external authorization portal."""

    def get_submission_status(
        self, submission_reference: str
    ) -> PortalStatusRecord | None: ...


class VerificationProviderPort(Protocol):
    """Port for independently verifying outcome via a separate access path (AD-004)."""

    def verify_outcome(
        self, submission_reference: str, expected_status: str
    ) -> ExternalVerificationResult: ...
