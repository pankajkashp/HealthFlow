"""Integration test for the FALSE-SUCCESS Scenario & The DONE Principle.

CRITICAL PRODUCT REQUIREMENT (PRS §7, §12, AD-004, AD-013):
"The agent cannot say DONE. The environment has to prove DONE."
A tool response saying "submitted successfully" or returning an acknowledgment ID
does NOT prove completion. The authoritative simulated environment must confirm
the expected outcome via an independent access path.

This test demonstrates that an apparent submission success response CANNOT be trusted
as proof of completion when the authoritative backend state shows otherwise.

Ref: docs/architecture/ARCHITECTURE.md §6.5, §6.7, §12
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §12
"""

from healthflow_domain import (
    AuthorizationGatewayPort,
    VerificationProviderPort,
)
from healthflow_domain.external_models import PortalSubmissionPayload
from healthflow_infrastructure.simulators import (
    SyntheticAuthorizationGatewayAdapter,
    SyntheticAuthorizationPortalSimulator,
    SyntheticVerificationAdapter,
)


class TestFalseSuccessScenario:
    def test_false_success_demonstrates_done_principle(self) -> None:
        """Demonstrate that apparent gateway success differs from authoritative state.

        Sequence:
        1. Agent prepares authorization package for Olivia Chen (Case 6).
        2. Agent calls submit_authorization() via AuthorizationGatewayPort.
        3. Portal gateway returns apparent success (HTTP 200 / ACK 'RECEIVED' with reference).
        4. A naive system without independent verification would assume DONE.
        5. Independent verification queries authoritative external state via VerificationProviderPort.
        6. Authoritative state reveals DENIED / REJECTED.
        7. Verification fails (verified=False), mathematically preventing false completion.
        """
        portal = SyntheticAuthorizationPortalSimulator()
        gateway: AuthorizationGatewayPort = SyntheticAuthorizationGatewayAdapter(portal)
        verifier: VerificationProviderPort = SyntheticVerificationAdapter(portal)

        # 1. Submission payload for Case 6 (Olivia Chen - configured for FALSE_SUCCESS)
        payload = PortalSubmissionPayload(
            patient_id="pat_chen_006",
            plan_id="plan_kaiser_006",
            procedure_type="MRI_CERVICAL_SPINE",
            clinical_indication="Cervical spine stenosis with radiating numbness",
            document_references=["doc_ref_chen_001"],
            requesting_physician="dr_lee",
        )

        # 2. Submit to gateway
        ack = gateway.submit_authorization(payload)

        # 3. Gateway returns APPARENT SUCCESS!
        assert ack.success is True
        assert ack.ack_status == "RECEIVED"
        assert ack.submission_reference == "AUTH-ACK-CHEN-006"
        assert ack.error_code is None

        # 4. In a flawed system, an agent would claim "Goal Achieved / Approved".
        # But HealthFlow enforces independent verification:
        expected_status = "APPROVED"

        verification_result = verifier.verify_outcome(
            submission_reference=ack.submission_reference,
            expected_status=expected_status,
        )

        # 5. Authoritative verification intercepts the false success!
        assert verification_result.verified is False
        assert verification_result.expected_status == "APPROVED"
        assert verification_result.actual_status == "DENIED"
        assert "MISMATCH DETECTED" in verification_result.details
        assert (
            verification_result.verification_source
            == "synthetic_portal_authoritative_adjudication_db"
        )
