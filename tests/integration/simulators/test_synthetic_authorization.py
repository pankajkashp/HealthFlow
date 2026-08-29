"""Integration tests for Synthetic Authorization Portal Simulator & Adapters.

Verifies electronic submission intake, status tracking, authoritative state management,
and independent outcome verification.
Ref: docs/architecture/ARCHITECTURE.md §6.5, §6.6, §6.7, §13
"""

from healthflow_domain import (
    AuthorizationGatewayPort,
    AuthorizationStatusGatewayPort,
    VerificationProviderPort,
)
from healthflow_domain.external_models import (
    PortalSubmissionPayload,
)
from healthflow_infrastructure.simulators import (
    SyntheticAuthorizationGatewayAdapter,
    SyntheticAuthorizationPortalSimulator,
    SyntheticAuthorizationStatusAdapter,
    SyntheticVerificationAdapter,
)


class TestSyntheticAuthorizationPortal:
    def test_successful_submission_returns_ack(self) -> None:
        portal = SyntheticAuthorizationPortalSimulator()
        payload = PortalSubmissionPayload(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            procedure_type="MRI_LUMBAR_SPINE",
            clinical_indication="L5-S1 lumbar radiculopathy",
            document_references=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
            requesting_physician="dr_alvarez",
        )

        ack = portal.submit(payload)
        assert ack.success is True
        assert ack.ack_status == "RECEIVED"
        assert ack.submission_reference is not None
        assert ack.submission_reference.startswith("AUTH-ACK-JENKINS-001")

        # Query authoritative status
        status = portal.get_status(ack.submission_reference)
        assert status is not None
        assert status.portal_status == "APPROVED"

    def test_portal_downtime_returns_gateway_timeout(self) -> None:
        portal = SyntheticAuthorizationPortalSimulator()
        portal.set_availability(False)

        payload = PortalSubmissionPayload(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            procedure_type="MRI_LUMBAR_SPINE",
            clinical_indication="L5-S1 lumbar radiculopathy",
            document_references=["doc_ref_jenkins_001"],
            requesting_physician="dr_alvarez",
        )
        ack = portal.submit(payload)
        assert ack.success is False
        assert ack.ack_status == "GATEWAY_TIMEOUT"
        assert ack.error_code == "ERR_PORTAL_UNAVAILABLE"

    def test_independent_verification_approved(self) -> None:
        portal = SyntheticAuthorizationPortalSimulator()
        payload = PortalSubmissionPayload(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            procedure_type="MRI_LUMBAR_SPINE",
            clinical_indication="L5-S1 lumbar radiculopathy",
            document_references=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
            requesting_physician="dr_alvarez",
        )
        ack = portal.submit(payload)
        assert ack.submission_reference is not None

        # Verify expected outcome
        ver_result = portal.verify_outcome_independently(
            submission_reference=ack.submission_reference,
            expected_status="APPROVED",
        )
        assert ver_result.verified is True
        assert ver_result.actual_status == "APPROVED"
        assert ver_result.expected_status == "APPROVED"

    def test_independent_verification_mismatch_fails(self) -> None:
        portal = SyntheticAuthorizationPortalSimulator()
        payload = PortalSubmissionPayload(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            procedure_type="MRI_LUMBAR_SPINE",
            clinical_indication="L5-S1 lumbar radiculopathy",
            document_references=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
            requesting_physician="dr_alvarez",
        )
        ack = portal.submit(payload)
        assert ack.submission_reference is not None

        # If agent expects DENIED, but authoritative state is APPROVED -> mismatch!
        ver_result = portal.verify_outcome_independently(
            submission_reference=ack.submission_reference,
            expected_status="DENIED",
        )
        assert ver_result.verified is False
        assert "MISMATCH DETECTED" in ver_result.details

    def test_adapters_implement_domain_ports(self) -> None:
        portal = SyntheticAuthorizationPortalSimulator()
        gateway_adapter: AuthorizationGatewayPort = (
            SyntheticAuthorizationGatewayAdapter(portal)
        )
        status_adapter: AuthorizationStatusGatewayPort = (
            SyntheticAuthorizationStatusAdapter(portal)
        )
        verify_adapter: VerificationProviderPort = SyntheticVerificationAdapter(portal)

        payload = PortalSubmissionPayload(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            procedure_type="MRI_LUMBAR_SPINE",
            clinical_indication="L5-S1 radiculopathy",
            document_references=["doc_ref_jenkins_001"],
            requesting_physician="dr_test",
        )

        ack = gateway_adapter.submit_authorization(payload)
        assert ack.success is True
        assert ack.submission_reference is not None

        status = status_adapter.get_submission_status(ack.submission_reference)
        assert status is not None
        assert status.portal_status == "APPROVED"

        ver = verify_adapter.verify_outcome(ack.submission_reference, "APPROVED")
        assert ver.verified is True
