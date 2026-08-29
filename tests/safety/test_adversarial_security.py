"""Adversarial Security & Safety Boundary Test Suite.

Verifies that deterministic controls cannot be bypassed by prompt manipulation,
malicious inputs, unauthorized tool calls, unverified completion claims,
or out-of-order workflow actions.

Ref: docs/architecture/ARCHITECTURE.md §8.2, §16
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §8, §21
"""

import pytest
from healthflow_application import AgentTools
from healthflow_domain.enums import WorkflowState
from healthflow_domain.external_models import PayerCoverageRecord
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
from healthflow_safety import (
    UserRole,
    check_action_permission,
    evaluate_pre_submission_safety_gate,
)


def _build_test_tools() -> AgentTools:
    portal = SyntheticAuthorizationPortalSimulator()
    return AgentTools(
        ehr_port=SyntheticEhrAdapter(SyntheticEhrSimulator()),
        payer_port=SyntheticPayerAdapter(SyntheticPayerSimulator()),
        document_store_port=SyntheticDocumentStoreAdapter(
            SyntheticDocumentStoreSimulator()
        ),
        gateway_port=SyntheticAuthorizationGatewayAdapter(portal),
        status_gateway_port=SyntheticAuthorizationStatusAdapter(portal),
        verification_port=SyntheticVerificationAdapter(portal),
    )


class TestAdversarialSecurityBoundaries:
    """Verifies that the agent cannot breach deterministic control boundaries."""

    def test_unauthorized_tool_call_blocked_by_permission_engine(self) -> None:
        """Agent cannot invent or call arbitrary tools."""
        res = check_action_permission(
            "execute_raw_sql_query",
            WorkflowState.GATHERING_INFORMATION,
            UserRole.AGENT,
        )
        assert res.allowed is False
        assert "unrecognized or unauthorized" in (res.denial_reason or "").lower()

    def test_out_of_order_submission_blocked(self) -> None:
        """Agent cannot jump directly from GATHERING_INFORMATION to submit."""
        tools = _build_test_tools()
        tools.set_workflow_state(WorkflowState.GATHERING_INFORMATION)

        res = tools.submit_authorization_request(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
        )
        assert res.success is False
        assert res.error_code == "PERMISSION_DENIED"
        assert "not permitted in state 'GATHERING_INFORMATION'" in (
            res.error_message or ""
        )

    def test_terminal_state_mutation_blocked(self) -> None:
        """No actions can be performed on a COMPLETED case."""
        tools = _build_test_tools()
        tools.set_workflow_state(WorkflowState.COMPLETED)

        # Attempt read
        read_res = tools.get_patient_record("pat_jenkins_001")
        assert read_res.success is False
        assert read_res.error_code == "PERMISSION_DENIED"

        # Attempt write
        write_res = tools.submit_authorization_request(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001"],
        )
        assert write_res.success is False
        assert write_res.error_code == "PERMISSION_DENIED"

    def test_non_synthetic_data_injection_blocked(self) -> None:
        """Safety gate blocks ingestion/submission of non-synthetic patient data."""

        class NonSyntheticPatientStub:
            patient_id = "pat_real_999"
            name_reference = "Real Hospital Patient"
            ehr_reference = "EHR-PROD-999"
            clinical_notes_summary = "Real hospital data."
            is_synthetic = False

        cov = PayerCoverageRecord(
            patient_id="pat_real_999",
            plan_id="plan_bcbs_001",
            insurer_name="BCBS",
            is_active=True,
            in_network=True,
            requires_prior_authorization=True,
            coverage_notes="Active",
        )
        gate_res = evaluate_pre_submission_safety_gate(
            patient_record=NonSyntheticPatientStub(),
            coverage_record=cov,
            required_document_types=["physician_referral"],
            gathered_documents=[],
            clinical_indication="Legitimate clinical indication",
        )
        assert gate_res.allowed is False
        assert any(v.code == "DATA_BOUNDARY_VIOLATION" for v in gate_res.violations)

    @pytest.mark.parametrize(
        "sql_injection_attempt",
        [
            "pat_123'; DELETE FROM authorization_cases;--",
            "pat_123' OR '1'='1",
            "pat_123' UNION SELECT * FROM patients;--",
        ],
    )
    def test_sql_injection_payload_in_identifier_rejected(
        self, sql_injection_attempt: str
    ) -> None:
        tools = _build_test_tools()
        res = tools.get_patient_record(sql_injection_attempt)
        assert res.success is False
        assert res.error_code in {
            "INJECTION_ATTEMPT_DETECTED",
            "MALFORMED_IDENTIFIER",
        }

    def test_claim_of_completion_on_submission_ack_prevented(self) -> None:
        """The agent receives submission ACK ('RECEIVED'). It cannot claim completion without verification."""
        tools = _build_test_tools()
        tools.set_workflow_state(WorkflowState.PREPARING_SUBMISSION)

        sub_res = tools.submit_authorization_request(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
        )
        assert sub_res.success is True
        assert sub_res.initial_status == "RECEIVED"
        assert sub_res.submission_reference is not None

        # The submission acknowledgment alone has NOT verified outcome
        assert sub_res.initial_status != "COMPLETED"
        # Independent verification must be called
        ver_res = tools.verify_authorization_outcome(
            sub_res.submission_reference, "APPROVED"
        )
        assert ver_res.verified is True
        assert ver_res.actual_status == "APPROVED"
