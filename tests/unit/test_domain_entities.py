"""Unit tests for HealthFlow Domain Entities.

Verifies construction, invariants, data boundary enforcement, and validation rules.
Ref: docs/architecture/ARCHITECTURE.md §5
"""

import pytest
from healthflow_domain import (
    AuditEventType,
    AuditId,
    AuditRecord,
    AuthorizationCase,
    CaseId,
    CasePriority,
    DataBoundaryViolationError,
    DomainValidationError,
    EscalationId,
    EscalationReason,
    EscalationRecord,
    InsurancePlan,
    InvariantViolationError,
    Patient,
    PatientId,
    PlanId,
    ProcedureType,
    SubmissionId,
    SubmissionRecord,
    VerificationId,
    VerificationRecord,
    VerificationStatus,
    WorkflowState,
)


class TestPatientEntity:
    def test_valid_patient_creation(self) -> None:
        patient = Patient(
            id=PatientId.generate(),
            name_reference="Synthetic John Doe",
            ehr_reference="EHR-SYN-1001",
            is_synthetic=True,
        )
        assert patient.is_synthetic is True
        assert "EHR-SYN-1001" in patient.ehr_reference

    def test_rejects_non_synthetic_patient(self) -> None:
        """Enforces synthetic data boundary rule: real patient data is forbidden."""
        with pytest.raises(DataBoundaryViolationError, match="Real PHI is prohibited"):
            Patient(
                id=PatientId.generate(),
                name_reference="Real Patient",
                ehr_reference="EHR-REAL-001",
                is_synthetic=False,
            )

    def test_rejects_empty_name_reference(self) -> None:
        with pytest.raises(
            DomainValidationError, match="name_reference cannot be empty"
        ):
            Patient(
                id=PatientId.generate(),
                name_reference="   ",
                ehr_reference="EHR-SYN-1002",
            )

    def test_rejects_empty_ehr_reference(self) -> None:
        with pytest.raises(
            DomainValidationError, match="ehr_reference cannot be empty"
        ):
            Patient(
                id=PatientId.generate(),
                name_reference="Patient Two",
                ehr_reference="",
            )


class TestInsurancePlanEntity:
    def test_valid_insurance_plan(self) -> None:
        plan = InsurancePlan(
            id=PlanId.generate(),
            patient_id=PatientId.generate(),
            insurer_reference="INS-ACME-HEALTH",
            plan_type="HMO",
            member_reference="MEM-12345",
        )
        assert plan.plan_type == "HMO"
        assert plan.insurer_reference == "INS-ACME-HEALTH"

    def test_rejects_empty_insurer_reference(self) -> None:
        with pytest.raises(
            DomainValidationError, match="insurer_reference cannot be empty"
        ):
            InsurancePlan(
                id=PlanId.generate(),
                patient_id=PatientId.generate(),
                insurer_reference="",
                plan_type="PPO",
                member_reference="MEM-123",
            )


class TestAuthorizationCaseEntity:
    def test_initial_case_creation(self) -> None:
        case = AuthorizationCase(
            id=CaseId.generate(),
            patient_id=PatientId.generate(),
            insurance_plan_id=PlanId.generate(),
            procedure_type=ProcedureType.MRI_LUMBAR_SPINE,
            clinical_indication="Persistent lower back pain radiating to left leg for 8 weeks.",
            priority=CasePriority.ROUTINE,
        )
        assert case.current_state == WorkflowState.INITIATED
        assert case.procedure_type == ProcedureType.MRI_LUMBAR_SPINE
        assert case.priority == CasePriority.ROUTINE

    def test_rejects_empty_indication(self) -> None:
        with pytest.raises(
            DomainValidationError, match="clinical_indication cannot be empty"
        ):
            AuthorizationCase(
                id=CaseId.generate(),
                patient_id=PatientId.generate(),
                insurance_plan_id=PlanId.generate(),
                procedure_type=ProcedureType.MRI_BRAIN,
                clinical_indication="   ",
            )


class TestSubmissionRecordEntity:
    def test_valid_submission_record(self) -> None:
        sub = SubmissionRecord(
            id=SubmissionId.generate(),
            case_id=CaseId.generate(),
            submission_reference="PORTAL-REF-9988",
            payload_hash="sha256:abcd1234ef5678",
            initial_status="PENDING_REVIEW",
        )
        assert sub.submission_reference == "PORTAL-REF-9988"

    def test_rejects_empty_submission_reference(self) -> None:
        with pytest.raises(
            DomainValidationError, match="submission_reference cannot be empty"
        ):
            SubmissionRecord(
                id=SubmissionId.generate(),
                case_id=CaseId.generate(),
                submission_reference="",
                payload_hash="hash123",
                initial_status="PENDING",
            )


class TestVerificationRecordEntity:
    def test_valid_verification_record(self) -> None:
        ver = VerificationRecord(
            id=VerificationId.generate(),
            case_id=CaseId.generate(),
            submission_reference="PORTAL-REF-9988",
            status=VerificationStatus.CONFIRMED,
            verification_details="Confirmed authorization #AUTH-7761 active in portal.",
        )
        assert ver.status == VerificationStatus.CONFIRMED


class TestEscalationRecordEntity:
    def test_escalation_and_resolution(self) -> None:
        esc = EscalationRecord(
            id=EscalationId.generate(),
            case_id=CaseId.generate(),
            reason=EscalationReason.SAFETY_GATE_FAILURE,
            from_state=WorkflowState.PREPARING_SUBMISSION,
            notes="Missing required prior conservative therapy clinical notes.",
        )
        assert esc.resolved_at is None

        esc.resolve(
            resolution_notes="Physician reviewed and provided physical therapy records.",
            resolved_by="dr_smith",
        )
        assert esc.resolved_at is not None
        assert esc.resolved_by == "dr_smith"

    def test_cannot_resolve_twice(self) -> None:
        esc = EscalationRecord(
            id=EscalationId.generate(),
            case_id=CaseId.generate(),
            reason=EscalationReason.AMBIGUOUS_INFORMATION,
            from_state=WorkflowState.GATHERING_INFORMATION,
            notes="Conflicting member ID in records.",
        )
        esc.resolve(resolution_notes="Resolved", resolved_by="nurse_jane")
        with pytest.raises(InvariantViolationError, match="already been resolved"):
            esc.resolve(resolution_notes="Resolved again", resolved_by="nurse_jane")


class TestAuditRecordEntity:
    def test_valid_audit_record(self) -> None:
        audit = AuditRecord(
            id=AuditId.generate(),
            event_type=AuditEventType.CASE_CREATED,
            case_id=CaseId.generate(),
            details={"action": "created", "initial_state": "INITIATED"},
            actor="dr_smith",
        )
        assert audit.event_type == AuditEventType.CASE_CREATED
        assert audit.actor == "dr_smith"
