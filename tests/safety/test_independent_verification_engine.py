"""Independent Verification Engine Test Suite.

Verifies independent verification against authoritative external state,
the DONE Principle (PRS §7), and false-success interception.

Ref: docs/architecture/ARCHITECTURE.md §8.1, §9.1
Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-004, AD-013
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §12
"""

from healthflow_application import AgentTools
from healthflow_domain.external_models import ExternalVerificationResult
from healthflow_infrastructure.simulators import (
    SyntheticAuthorizationGatewayAdapter,
    SyntheticAuthorizationPortalSimulator,
    SyntheticAuthorizationStatusAdapter,
    SyntheticDocumentStoreAdapter,
    SyntheticDocumentStoreSimulator,
    SyntheticEhrAdapter,
    SyntheticEhrSimulator,
    SyntheticPayerAdapter,
    SyntheticPayerSimulator,
    SyntheticVerificationAdapter,
)
from healthflow_safety import evaluate_verification_outcome


def _build_test_tools() -> tuple[AgentTools, SyntheticAuthorizationPortalSimulator]:
    ehr = SyntheticEhrSimulator()
    payer = SyntheticPayerSimulator()
    docs = SyntheticDocumentStoreSimulator()
    portal = SyntheticAuthorizationPortalSimulator()

    tools = AgentTools(
        ehr_port=SyntheticEhrAdapter(ehr),
        payer_port=SyntheticPayerAdapter(payer),
        document_store_port=SyntheticDocumentStoreAdapter(docs),
        gateway_port=SyntheticAuthorizationGatewayAdapter(portal),
        status_gateway_port=SyntheticAuthorizationStatusAdapter(portal),
        verification_port=SyntheticVerificationAdapter(portal),
    )
    return tools, portal


class TestIndependentVerificationEngine:
    """Verifies outcome evaluations across authoritative states."""

    def test_authoritative_approved_confirmed(self) -> None:
        ext_res = ExternalVerificationResult(
            submission_reference="AUTH-1001",
            expected_status="APPROVED",
            verified=True,
            actual_status="APPROVED",
            verification_source="authoritative_portal_backend",
            details="Prior authorization confirmed approved.",
        )
        dec = evaluate_verification_outcome("APPROVED", ext_res)
        assert dec.is_confirmed is True
        assert dec.decision == "CONFIRMED"
        assert dec.error_code is None

    def test_authoritative_denied_mismatch_detected(self) -> None:
        ext_res = ExternalVerificationResult(
            submission_reference="AUTH-1002",
            expected_status="APPROVED",
            verified=False,
            actual_status="DENIED",
            verification_source="authoritative_portal_backend",
            details="MISMATCH DETECTED: Expected 'APPROVED', but state is 'DENIED'.",
        )
        dec = evaluate_verification_outcome("APPROVED", ext_res)
        assert dec.is_confirmed is False
        assert dec.decision == "MISMATCH_DETECTED"
        assert dec.error_code == "VERIFICATION_MISMATCH"

    def test_authoritative_pending_not_confirmed(self) -> None:
        ext_res = ExternalVerificationResult(
            submission_reference="AUTH-1003",
            expected_status="APPROVED",
            verified=False,
            actual_status="PENDING",
            verification_source="authoritative_portal_backend",
            details="Pending clinical review.",
        )
        dec = evaluate_verification_outcome("APPROVED", ext_res)
        assert dec.is_confirmed is False
        assert dec.decision == "NOT_CONFIRMED"
        assert dec.error_code == "OUTCOME_PENDING"

    def test_authoritative_additional_info_required_not_confirmed(self) -> None:
        ext_res = ExternalVerificationResult(
            submission_reference="AUTH-1004",
            expected_status="APPROVED",
            verified=False,
            actual_status="ADDITIONAL_INFO_REQUIRED",
            verification_source="authoritative_portal_backend",
            details="Additional therapy notes needed.",
        )
        dec = evaluate_verification_outcome("APPROVED", ext_res)
        assert dec.is_confirmed is False
        assert dec.decision == "NOT_CONFIRMED"
        assert dec.error_code == "ADDITIONAL_INFO_REQUIRED"

    def test_provider_unavailable_handled(self) -> None:
        dec = evaluate_verification_outcome("APPROVED", None)
        assert dec.is_confirmed is False
        assert dec.decision == "ERROR"
        assert dec.error_code == "VERIFICATION_PROVIDER_UNAVAILABLE"


class TestFalseSuccessScenarioInterception:
    """Verifies that apparent gateway success is intercepted when authoritative backend is denied."""

    def test_false_success_intercepted_at_tool_boundary(self) -> None:
        tools, _ = _build_test_tools()

        # Submit Case 6 (Olivia Chen)
        sub_res = tools.submit_authorization_request(
            patient_id="pat_chen_006",
            plan_id="plan_kaiser_006",
            requirements_id="REQ-plan_kaiser_006-MRI_CERVICAL_SPINE",
            document_ids=["doc_ref_chen_001"],
        )

        # Gateway returns apparent success ACK
        assert sub_res.success is True
        assert sub_res.initial_status == "RECEIVED"
        assert sub_res.submission_reference is not None

        # But independent verification against authoritative portal reveals DENIED
        ver_res = tools.verify_authorization_outcome(
            sub_res.submission_reference, "APPROVED"
        )

        # The safety layer MUST NOT confirm completion!
        assert ver_res.verified is False
        assert ver_res.actual_status == "DENIED"
        assert ver_res.error_code == "VERIFICATION_MISMATCH"
