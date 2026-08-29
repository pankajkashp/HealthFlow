"""Unit tests for the 9 approved HealthFlow agent tools.

Verifies input validation, boundary restrictions, failure behavior,
and structured result schemas for every tool defined in AD-014.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-014
Ref: docs/architecture/ARCHITECTURE.md §7.2
"""

from healthflow_application import (
    AgentTools,
    AuthorizationRequirementsResult,
    AuthorizationStatusResult,
    DocumentResult,
    EscalationResult,
    InsurancePlanResult,
    PatientRecordResult,
    SubmissionResult,
    ValidationResult,
    VerificationResult,
)
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


def _create_test_tools() -> AgentTools:
    """Helper to instantiate AgentTools wired to fresh synthetic simulators."""
    ehr = SyntheticEhrSimulator()
    payer = SyntheticPayerSimulator()
    docs = SyntheticDocumentStoreSimulator()
    portal = SyntheticAuthorizationPortalSimulator()

    return AgentTools(
        ehr_port=SyntheticEhrAdapter(ehr),
        payer_port=SyntheticPayerAdapter(payer),
        document_store_port=SyntheticDocumentStoreAdapter(docs),
        gateway_port=SyntheticAuthorizationGatewayAdapter(portal),
        status_gateway_port=SyntheticAuthorizationStatusAdapter(portal),
        verification_port=SyntheticVerificationAdapter(portal),
    )


class TestTool1GetPatientRecord:
    def test_valid_patient_lookup(self) -> None:
        tools = _create_test_tools()
        result = tools.get_patient_record("pat_jenkins_001")
        assert isinstance(result, PatientRecordResult)
        assert result.success is True
        assert result.patient_id == "pat_jenkins_001"
        assert result.is_synthetic is True
        assert result.name_reference is not None
        assert result.error_code is None

    def test_empty_identifier_validation(self) -> None:
        tools = _create_test_tools()
        result = tools.get_patient_record("")
        assert result.success is False
        assert result.error_code == "INVALID_IDENTIFIER"

    def test_nonexistent_patient(self) -> None:
        tools = _create_test_tools()
        result = tools.get_patient_record("pat_unknown_999")
        assert result.success is False
        assert result.error_code == "PATIENT_NOT_FOUND"


class TestTool2GetInsurancePlan:
    def test_valid_insurance_lookup(self) -> None:
        tools = _create_test_tools()
        result = tools.get_insurance_plan("pat_jenkins_001")
        assert isinstance(result, InsurancePlanResult)
        assert result.success is True
        assert result.plan_id == "plan_bcbs_001"
        assert "Blue Cross" in (result.insurer_reference or "")
        assert result.error_code is None

    def test_empty_patient_id(self) -> None:
        tools = _create_test_tools()
        result = tools.get_insurance_plan("  ")
        assert result.success is False
        assert result.error_code == "INVALID_PATIENT_ID"

    def test_nonexistent_patient_plan(self) -> None:
        tools = _create_test_tools()
        result = tools.get_insurance_plan("pat_uninsured_999")
        assert result.success is False
        assert result.error_code == "PLAN_NOT_FOUND"


class TestTool3GetAuthorizationRequirements:
    def test_valid_mri_requirements(self) -> None:
        tools = _create_test_tools()
        result = tools.get_authorization_requirements(
            "plan_bcbs_001", "MRI_LUMBAR_SPINE"
        )
        assert isinstance(result, AuthorizationRequirementsResult)
        assert result.success is True
        assert result.requirements_id is not None
        assert "physician_referral" in result.required_document_types
        assert result.retrieval_confidence == "HIGH"

    def test_unsupported_procedure_rejection(self) -> None:
        tools = _create_test_tools()
        result = tools.get_authorization_requirements(
            "plan_bcbs_001", "CT_SCAN_ABDOMEN"
        )
        assert result.success is False
        assert result.error_code == "UNSUPPORTED_PROCEDURE"

    def test_empty_plan_id(self) -> None:
        tools = _create_test_tools()
        result = tools.get_authorization_requirements("", "MRI")
        assert result.success is False
        assert result.error_code == "INVALID_PLAN_ID"


class TestTool4GetRequiredDocument:
    def test_valid_document_metadata_retrieval(self) -> None:
        tools = _create_test_tools()
        result = tools.get_required_document(
            "doc_ref_jenkins_001", "physician_referral"
        )
        assert isinstance(result, DocumentResult)
        assert result.success is True
        assert result.document_id == "doc_ref_jenkins_001"
        assert result.document_type == "physician_referral"
        assert result.content_reference is not None
        assert result.metadata is not None
        assert result.metadata["file_format"] == "PDF"

    def test_document_type_mismatch(self) -> None:
        tools = _create_test_tools()
        result = tools.get_required_document(
            "doc_ref_jenkins_001", "laboratory_results"
        )
        assert result.success is False
        assert result.error_code == "DOCUMENT_TYPE_MISMATCH"

    def test_missing_document(self) -> None:
        tools = _create_test_tools()
        result = tools.get_required_document(
            "doc_ref_missing_888", "physician_referral"
        )
        assert result.success is False
        assert result.error_code == "DOCUMENT_NOT_FOUND"


class TestTool5ValidateAuthorizationPackage:
    def test_valid_package_passes_validation(self) -> None:
        tools = _create_test_tools()
        result = tools.validate_authorization_package(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
        )
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.missing_fields) == 0
        assert len(result.conflicts) == 0

    def test_missing_documents_fails_validation(self) -> None:
        tools = _create_test_tools()
        result = tools.validate_authorization_package(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=[],
        )
        assert result.is_valid is False
        assert "supporting_clinical_documents" in result.missing_fields


class TestTool6SubmitAuthorizationRequest:
    def test_successful_submission(self) -> None:
        tools = _create_test_tools()
        result = tools.submit_authorization_request(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
        )
        assert isinstance(result, SubmissionResult)
        assert result.success is True
        assert result.submission_reference is not None
        assert result.initial_status == "RECEIVED"

    def test_submission_blocked_when_validation_fails(self) -> None:
        tools = _create_test_tools()
        # Non-existent patient should fail pre-submission validation
        result = tools.submit_authorization_request(
            patient_id="pat_nonexistent_999",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=[],
        )
        assert result.success is False
        assert result.error_code == "PRE_SUBMISSION_VALIDATION_FAILED"


class TestTool7GetAuthorizationStatus:
    def test_valid_status_query(self) -> None:
        tools = _create_test_tools()
        sub_res = tools.submit_authorization_request(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
        )
        assert sub_res.submission_reference is not None

        status_res = tools.get_authorization_status(sub_res.submission_reference)
        assert isinstance(status_res, AuthorizationStatusResult)
        assert status_res.success is True
        assert status_res.status == "APPROVED"

    def test_empty_reference_validation(self) -> None:
        tools = _create_test_tools()
        result = tools.get_authorization_status("")
        assert result.success is False
        assert result.error_code == "INVALID_SUBMISSION_REF"


class TestTool8VerifyAuthorizationOutcome:
    def test_successful_outcome_verification(self) -> None:
        tools = _create_test_tools()
        sub_res = tools.submit_authorization_request(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
        )
        assert sub_res.submission_reference is not None

        ver_res = tools.verify_authorization_outcome(
            sub_res.submission_reference, "APPROVED"
        )
        assert isinstance(ver_res, VerificationResult)
        assert ver_res.verified is True
        assert ver_res.actual_status == "APPROVED"
        assert ver_res.error_code is None

    def test_outcome_mismatch_detection(self) -> None:
        tools = _create_test_tools()
        sub_res = tools.submit_authorization_request(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_ref_jenkins_001", "doc_ref_jenkins_002"],
        )
        assert sub_res.submission_reference is not None

        # Expect DENIED when actual is APPROVED -> mismatch
        ver_res = tools.verify_authorization_outcome(
            sub_res.submission_reference, "DENIED"
        )
        assert ver_res.verified is False
        assert ver_res.error_code == "VERIFICATION_MISMATCH"

    def test_invalid_expected_status_rejected(self) -> None:
        tools = _create_test_tools()
        result = tools.verify_authorization_outcome("REF-123", "PENDING_CONFIRMATION")
        assert result.verified is False
        assert result.error_code == "INVALID_EXPECTED_STATUS"


class TestTool9RequestEscalation:
    def test_valid_escalation(self) -> None:
        tools = _create_test_tools()
        result = tools.request_escalation(
            reason_code="VALIDATION_CONFLICT",
            reason_summary="Conflicting patient diagnoses discovered between EHR and referral.",
        )
        assert isinstance(result, EscalationResult)
        assert result.success is True
        assert result.workflow_state == "ESCALATED"
        assert result.escalation_id is not None

    def test_invalid_reason_code_rejected(self) -> None:
        tools = _create_test_tools()
        result = tools.request_escalation(
            reason_code="ARBITRARY_UNAPPROVED_CODE",
            reason_summary="Testing invalid code",
        )
        assert result.success is False
        assert result.error_code == "INVALID_REASON_CODE"

    def test_empty_summary_rejected(self) -> None:
        tools = _create_test_tools()
        result = tools.request_escalation(
            reason_code="VERIFICATION_FAILED",
            reason_summary="",
        )
        assert result.success is False
        assert result.error_code == "EMPTY_REASON_SUMMARY"

    def test_excessively_long_summary_rejected(self) -> None:
        tools = _create_test_tools()
        long_summary = "X" * 501
        result = tools.request_escalation(
            reason_code="VERIFICATION_FAILED",
            reason_summary=long_summary,
        )
        assert result.success is False
        assert result.error_code == "REASON_SUMMARY_TOO_LONG"
