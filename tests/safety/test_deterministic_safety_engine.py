"""Deterministic Safety Engine Test Suite.

Verifies input validation, injection defense, permission check engine,
and pre-action safety gates in packages/safety.

Ref: docs/architecture/ARCHITECTURE.md §8
Ref: docs/product/PRODUCT_REQUIREMENTS.md §8, §11, §16, §21
"""

import pytest
from healthflow_domain.enums import WorkflowState
from healthflow_domain.external_models import (
    DocumentMetadata,
    EhrPatientRecord,
    PayerCoverageRecord,
)
from healthflow_safety import (
    UserRole,
    check_action_permission,
    evaluate_pre_submission_safety_gate,
    validate_document_reference,
    validate_escalation_inputs,
    validate_patient_identifier,
    validate_plan_identifier,
    validate_procedure_type,
    validate_submission_inputs,
    validate_verification_inputs,
)


class TestInputValidationAndSanitization:
    """Verifies deterministic rule-based input sanitization and validation."""

    def test_valid_patient_identifier(self) -> None:
        res = validate_patient_identifier("pat_jenkins_001")
        assert res.is_valid is True
        assert res.sanitized_value == "pat_jenkins_001"
        assert res.error_code is None

    def test_empty_patient_identifier_rejected(self) -> None:
        res = validate_patient_identifier("   ")
        assert res.is_valid is False
        assert res.error_code == "INVALID_IDENTIFIER"

    def test_patient_identifier_length_exceeded_rejected(self) -> None:
        res = validate_patient_identifier("pat_" + "x" * 65)
        assert res.is_valid is False
        assert res.error_code == "IDENTIFIER_TOO_LONG"

    @pytest.mark.parametrize(
        "malicious_payload",
        [
            "pat_123; DROP TABLE cases;--",
            "pat_123' OR 1=1--",
            "pat_123/*comment*/",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "pat_123 UNION SELECT * FROM users",
        ],
    )
    def test_injection_patterns_rejected(self, malicious_payload: str) -> None:
        res = validate_patient_identifier(malicious_payload)
        assert res.is_valid is False
        assert res.error_code in {
            "INJECTION_ATTEMPT_DETECTED",
            "MALFORMED_IDENTIFIER",
        }

    def test_valid_plan_identifier(self) -> None:
        res = validate_plan_identifier("plan_bcbs_001")
        assert res.is_valid is True
        assert res.sanitized_value == "plan_bcbs_001"

    def test_valid_procedure_type(self) -> None:
        res = validate_procedure_type("MRI_LUMBAR_SPINE")
        assert res.is_valid is True
        assert res.sanitized_value == "MRI_LUMBAR_SPINE"

    def test_non_mri_procedure_rejected(self) -> None:
        res = validate_procedure_type("CT_SCAN_CHEST")
        assert res.is_valid is False
        assert res.error_code == "UNSUPPORTED_PROCEDURE"

    def test_valid_document_reference(self) -> None:
        res = validate_document_reference("doc_ref_jenkins_001", "physician_referral")
        assert res.is_valid is True
        assert res.sanitized_value["reference"] == "doc_ref_jenkins_001"

    def test_valid_submission_inputs(self) -> None:
        res = validate_submission_inputs(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=["doc_001", "doc_002"],
        )
        assert res.is_valid is True
        assert res.sanitized_value["patient_id"] == "pat_jenkins_001"

    def test_empty_document_ids_in_submission_rejected(self) -> None:
        res = validate_submission_inputs(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            requirements_id="REQ-plan_bcbs_001-MRI",
            document_ids=[],
        )
        assert res.is_valid is False
        assert res.error_code == "EMPTY_DOCUMENT_LIST"

    def test_valid_verification_inputs(self) -> None:
        res = validate_verification_inputs("AUTH-12345", "APPROVED")
        assert res.is_valid is True
        assert res.sanitized_value["expected_status"] == "APPROVED"

    def test_invalid_expected_verification_status_rejected(self) -> None:
        res = validate_verification_inputs("AUTH-12345", "ASSUMED_APPROVED")
        assert res.is_valid is False
        assert res.error_code == "INVALID_EXPECTED_STATUS"

    def test_valid_escalation_inputs(self) -> None:
        res = validate_escalation_inputs(
            reason_code="VALIDATION_CONFLICT",
            reason_summary="Clinical contradiction detected in conservative therapy duration.",
        )
        assert res.is_valid is True

    def test_unapproved_escalation_reason_rejected(self) -> None:
        res = validate_escalation_inputs(
            reason_code="ARBITRARY_UNAPPROVED_REASON",
            reason_summary="Testing invalid code",
        )
        assert res.is_valid is False
        assert res.error_code == "INVALID_REASON_CODE"


class TestDeterministicPermissionEngine:
    """Verifies state-based action permissions and role boundaries."""

    def test_submit_allowed_in_preparing_submission(self) -> None:
        res = check_action_permission(
            "submit_authorization_request",
            WorkflowState.PREPARING_SUBMISSION,
            UserRole.AGENT,
        )
        assert res.allowed is True
        assert res.denial_reason is None

    @pytest.mark.parametrize(
        "prohibited_state",
        [
            WorkflowState.INITIATED,
            WorkflowState.GATHERING_INFORMATION,
            WorkflowState.VALIDATING,
            WorkflowState.SUBMITTED,
            WorkflowState.MONITORING,
            WorkflowState.VERIFYING,
            WorkflowState.COMPLETED,
            WorkflowState.DENIED,
            WorkflowState.FAILED,
        ],
    )
    def test_submit_prohibited_in_non_preparing_states(
        self, prohibited_state: WorkflowState
    ) -> None:
        res = check_action_permission(
            "submit_authorization_request",
            prohibited_state,
            UserRole.AGENT,
        )
        assert res.allowed is False
        assert res.denial_reason is not None

    @pytest.mark.parametrize(
        "terminal_state",
        [WorkflowState.COMPLETED, WorkflowState.DENIED, WorkflowState.FAILED],
    )
    def test_all_actions_prohibited_in_terminal_states(
        self, terminal_state: WorkflowState
    ) -> None:
        for action in [
            "get_patient_record",
            "get_insurance_plan",
            "submit_authorization_request",
            "get_authorization_status",
            "verify_authorization_outcome",
            "request_escalation",
        ]:
            res = check_action_permission(action, terminal_state, UserRole.AGENT)
            assert res.allowed is False
            assert "terminal state" in (res.denial_reason or "").lower()

    def test_unknown_action_denied(self) -> None:
        res = check_action_permission(
            "arbitrary_unauthorized_action",
            WorkflowState.GATHERING_INFORMATION,
            UserRole.AGENT,
        )
        assert res.allowed is False
        assert "unrecognized or unauthorized" in (res.denial_reason or "").lower()


class TestPreSubmissionSafetyGate:
    """Verifies the mandatory pre-action safety gate pipeline."""

    def _valid_patient(self) -> EhrPatientRecord:
        return EhrPatientRecord(
            patient_id="pat_jenkins_001",
            name_reference="Sarah Jenkins (Synthetic)",
            ehr_reference="EHR-SYN-1001",
            active_diagnoses=["M54.5"],
            clinical_notes_summary="Chronic low back pain radiating to left leg.",
            is_synthetic=True,
        )

    def _valid_coverage(self) -> PayerCoverageRecord:
        return PayerCoverageRecord(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            insurer_name="Blue Cross Blue Shield",
            is_active=True,
            in_network=True,
            requires_prior_authorization=True,
            coverage_notes="Prior authorization required for lumbar spine MRI.",
        )

    def _valid_docs(self) -> list[DocumentMetadata]:
        return [
            DocumentMetadata(
                document_reference="doc_001",
                patient_id="pat_jenkins_001",
                document_type="physician_referral",
                created_date="2026-08-01",
                author_reference="dr_smith",
                file_format="PDF",
                content_hash="hash1",
            ),
            DocumentMetadata(
                document_reference="doc_002",
                patient_id="pat_jenkins_001",
                document_type="conservative_therapy_notes",
                created_date="2026-08-05",
                author_reference="pt_jones",
                file_format="PDF",
                content_hash="hash2",
            ),
        ]

    def test_safety_gate_passes_for_valid_package(self) -> None:
        res = evaluate_pre_submission_safety_gate(
            patient_record=self._valid_patient(),
            coverage_record=self._valid_coverage(),
            required_document_types=[
                "physician_referral",
                "conservative_therapy_notes",
            ],
            gathered_documents=self._valid_docs(),
            clinical_indication="Severe radiculopathy refractory to physical therapy",
        )
        assert res.allowed is True
        assert len(res.violations) == 0

    def test_safety_gate_rejects_non_synthetic_patient(self) -> None:
        class NonSyntheticPatientStub:
            patient_id = "pat_real_123"
            name_reference = "Real Patient"
            ehr_reference = "EHR-REAL-123"
            clinical_notes_summary = "Real medical record."
            is_synthetic = False

        res = evaluate_pre_submission_safety_gate(
            patient_record=NonSyntheticPatientStub(),
            coverage_record=self._valid_coverage(),
            required_document_types=["physician_referral"],
            gathered_documents=self._valid_docs(),
            clinical_indication="Legitimate clinical indication",
        )
        assert res.allowed is False
        assert any(v.code == "DATA_BOUNDARY_VIOLATION" for v in res.violations)

    def test_safety_gate_rejects_inactive_coverage(self) -> None:
        inactive_cov = PayerCoverageRecord(
            patient_id="pat_jenkins_001",
            plan_id="plan_bcbs_001",
            insurer_name="Blue Cross Blue Shield",
            is_active=False,  # VIOLATION
            in_network=True,
            requires_prior_authorization=True,
            coverage_notes="Policy terminated.",
        )
        res = evaluate_pre_submission_safety_gate(
            patient_record=self._valid_patient(),
            coverage_record=inactive_cov,
            required_document_types=["physician_referral"],
            gathered_documents=self._valid_docs(),
            clinical_indication="Legitimate clinical indication",
        )
        assert res.allowed is False
        assert any(v.code == "INACTIVE_COVERAGE" for v in res.violations)

    def test_safety_gate_rejects_missing_required_document(self) -> None:
        res = evaluate_pre_submission_safety_gate(
            patient_record=self._valid_patient(),
            coverage_record=self._valid_coverage(),
            required_document_types=[
                "physician_referral",
                "physical_therapy_evaluation",  # MISSING
            ],
            gathered_documents=self._valid_docs(),
            clinical_indication="Legitimate clinical indication",
        )
        assert res.allowed is False
        assert any(v.code == "MISSING_REQUIRED_DOCUMENT" for v in res.violations)

    def test_safety_gate_rejects_clinical_notes_conflict(self) -> None:
        conflict_patient = EhrPatientRecord(
            patient_id="pat_jenkins_001",
            name_reference="Sarah Jenkins (Synthetic)",
            ehr_reference="EHR-SYN-1001",
            active_diagnoses=["M54.5"],
            clinical_notes_summary="Discrepancy: Clinical notes conflict with MRI indication.",
            is_synthetic=True,
        )
        res = evaluate_pre_submission_safety_gate(
            patient_record=conflict_patient,
            coverage_record=self._valid_coverage(),
            required_document_types=["physician_referral"],
            gathered_documents=self._valid_docs(),
            clinical_indication="Clinical indication",
        )
        assert res.allowed is False
        assert any(v.code == "CLINICAL_DATA_CONFLICT" for v in res.violations)
