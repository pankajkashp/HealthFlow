"""Infrastructure Adapters for Simulated Healthcare Systems.

Implements the domain ports (EhrPort, PayerPort, DocumentStorePort,
AuthorizationGatewayPort, AuthorizationStatusGatewayPort, VerificationProviderPort)
by wrapping the underlying synthetic simulators.

Ref: docs/architecture/ARCHITECTURE.md §6, §13
"""

from collections.abc import Sequence

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
from healthflow_domain.identifiers import PatientId, PlanId
from healthflow_domain.ports import (
    AuthorizationGatewayPort,
    AuthorizationStatusGatewayPort,
    DocumentStorePort,
    EhrPort,
    PayerPort,
    VerificationProviderPort,
)

from healthflow_infrastructure.simulators.synthetic_authorization_portal import (
    SyntheticAuthorizationPortalSimulator,
)
from healthflow_infrastructure.simulators.synthetic_document_store import (
    SyntheticDocumentStoreSimulator,
)
from healthflow_infrastructure.simulators.synthetic_ehr import (
    SyntheticEhrSimulator,
)
from healthflow_infrastructure.simulators.synthetic_payer import (
    SyntheticPayerSimulator,
)


class SyntheticEhrAdapter(EhrPort):
    """Adapter wrapping SyntheticEhrSimulator to fulfill EhrPort."""

    def __init__(self, simulator: SyntheticEhrSimulator) -> None:
        self._sim = simulator

    def get_patient_record(self, patient_id: PatientId) -> EhrPatientRecord | None:
        return self._sim.get_patient(str(patient_id))

    def get_clinical_history(self, patient_id: PatientId) -> Sequence[str]:
        return self._sim.get_clinical_history(str(patient_id))


class SyntheticPayerAdapter(PayerPort):
    """Adapter wrapping SyntheticPayerSimulator to fulfill PayerPort."""

    def __init__(self, simulator: SyntheticPayerSimulator) -> None:
        self._sim = simulator

    def get_coverage_status(
        self, patient_id: PatientId, plan_id: PlanId
    ) -> PayerCoverageRecord | None:
        return self._sim.get_coverage(str(patient_id), str(plan_id))

    def get_prior_auth_requirements(
        self, plan_id: PlanId, procedure_type: ProcedureType
    ) -> ProcedureRequirements | None:
        return self._sim.get_requirements(str(plan_id), procedure_type.value)


class SyntheticDocumentStoreAdapter(DocumentStorePort):
    """Adapter wrapping SyntheticDocumentStoreSimulator to fulfill DocumentStorePort."""

    def __init__(self, simulator: SyntheticDocumentStoreSimulator) -> None:
        self._sim = simulator

    def get_document_metadata(self, document_reference: str) -> DocumentMetadata | None:
        return self._sim.get_document_metadata(document_reference)

    def get_document_content(self, document_reference: str) -> DocumentContent | None:
        return self._sim.get_document_content(document_reference)


class SyntheticAuthorizationGatewayAdapter(AuthorizationGatewayPort):
    """Adapter wrapping SyntheticAuthorizationPortalSimulator to fulfill AuthorizationGatewayPort."""

    def __init__(self, simulator: SyntheticAuthorizationPortalSimulator) -> None:
        self._sim = simulator

    def submit_authorization(
        self, payload: PortalSubmissionPayload
    ) -> PortalSubmissionAck:
        return self._sim.submit(payload)


class SyntheticAuthorizationStatusAdapter(AuthorizationStatusGatewayPort):
    """Adapter wrapping SyntheticAuthorizationPortalSimulator to fulfill AuthorizationStatusGatewayPort."""

    def __init__(self, simulator: SyntheticAuthorizationPortalSimulator) -> None:
        self._sim = simulator

    def get_submission_status(
        self, submission_reference: str
    ) -> PortalStatusRecord | None:
        return self._sim.get_status(submission_reference)


class SyntheticVerificationAdapter(VerificationProviderPort):
    """Adapter wrapping SyntheticAuthorizationPortalSimulator to fulfill VerificationProviderPort.

    Uses an independent logical query path to verify authoritative external state (AD-004).
    """

    def __init__(self, simulator: SyntheticAuthorizationPortalSimulator) -> None:
        self._sim = simulator

    def verify_outcome(
        self, submission_reference: str, expected_status: str
    ) -> ExternalVerificationResult:
        return self._sim.verify_outcome_independently(
            submission_reference, expected_status
        )
