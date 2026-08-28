"""Unit tests for Application Services.

Validates use-case orchestration, domain port usage, and entity not found handling.
Tests run using an in-memory test double of UnitOfWork to prove Clean Architecture separation.

Ref: docs/architecture/ARCHITECTURE.md §2.3, §4.5
"""

from collections.abc import Sequence
from typing import Self

import pytest
from healthflow_application import (
    CreateAuthorizationCaseService,
    TransitionWorkflowStateService,
)
from healthflow_domain import (
    AuditEventType,
    AuditRecord,
    AuthorizationCase,
    CaseId,
    CasePriority,
    EntityNotFoundError,
    EscalationId,
    EscalationRecord,
    InsurancePlan,
    Patient,
    PatientId,
    PlanId,
    ProcedureType,
    SubmissionId,
    SubmissionRecord,
    UnitOfWork,
    VerificationId,
    VerificationRecord,
    WorkflowState,
    WorkflowTransition,
)


class InMemoryPatientRepo:
    def __init__(self) -> None:
        self.data: dict[str, Patient] = {}

    def get_by_id(self, patient_id: PatientId) -> Patient | None:
        return self.data.get(str(patient_id))

    def get_by_ehr_reference(self, ehr_reference: str) -> Patient | None:
        for p in self.data.values():
            if p.ehr_reference == ehr_reference:
                return p
        return None

    def save(self, patient: Patient) -> None:
        self.data[str(patient.id)] = patient


class InMemoryInsurancePlanRepo:
    def __init__(self) -> None:
        self.data: dict[str, InsurancePlan] = {}

    def get_by_id(self, plan_id: PlanId) -> InsurancePlan | None:
        return self.data.get(str(plan_id))

    def get_by_patient_id(self, patient_id: PatientId) -> Sequence[InsurancePlan]:
        return [p for p in self.data.values() if p.patient_id == patient_id]

    def save(self, plan: InsurancePlan) -> None:
        self.data[str(plan.id)] = plan


class InMemoryCaseRepo:
    def __init__(self) -> None:
        self.data: dict[str, AuthorizationCase] = {}

    def get_by_id(self, case_id: CaseId) -> AuthorizationCase | None:
        return self.data.get(str(case_id))

    def list_all(self, limit: int = 50, offset: int = 0) -> Sequence[AuthorizationCase]:
        return list(self.data.values())[offset : offset + limit]

    def save(self, case: AuthorizationCase) -> None:
        self.data[str(case.id)] = case


class InMemoryWorkflowStateRepo:
    def __init__(self) -> None:
        self.transitions: list[WorkflowTransition] = []

    def record_transition(self, transition: WorkflowTransition) -> None:
        self.transitions.append(transition)

    def list_by_case_id(self, case_id: CaseId) -> Sequence[WorkflowTransition]:
        return [t for t in self.transitions if t.case_id == case_id]


class InMemoryAuditRepo:
    def __init__(self) -> None:
        self.audits: list[AuditRecord] = []

    def record_event(self, record: AuditRecord) -> None:
        self.audits.append(record)

    def list_by_case_id(self, case_id: CaseId) -> Sequence[AuditRecord]:
        return [a for a in self.audits if a.case_id == case_id]


class InMemorySubmissionRepo:
    def __init__(self) -> None:
        self.data: dict[str, SubmissionRecord] = {}

    def get_by_id(self, submission_id: SubmissionId) -> SubmissionRecord | None:
        return self.data.get(str(submission_id))

    def get_by_reference(self, reference: str) -> SubmissionRecord | None:
        for s in self.data.values():
            if s.submission_reference == reference:
                return s
        return None

    def list_by_case_id(self, case_id: CaseId) -> Sequence[SubmissionRecord]:
        return [s for s in self.data.values() if s.case_id == case_id]

    def save(self, record: SubmissionRecord) -> None:
        self.data[str(record.id)] = record


class InMemoryVerificationRepo:
    def __init__(self) -> None:
        self.data: dict[str, VerificationRecord] = {}

    def get_by_id(self, verification_id: VerificationId) -> VerificationRecord | None:
        return self.data.get(str(verification_id))

    def list_by_case_id(self, case_id: CaseId) -> Sequence[VerificationRecord]:
        return [v for v in self.data.values() if v.case_id == case_id]

    def save(self, record: VerificationRecord) -> None:
        self.data[str(record.id)] = record


class InMemoryEscalationRepo:
    def __init__(self) -> None:
        self.data: dict[str, EscalationRecord] = {}

    def get_by_id(self, escalation_id: EscalationId) -> EscalationRecord | None:
        return self.data.get(str(escalation_id))

    def list_by_case_id(self, case_id: CaseId) -> Sequence[EscalationRecord]:
        return [e for e in self.data.values() if e.case_id == case_id]

    def save(self, record: EscalationRecord) -> None:
        self.data[str(record.id)] = record


class MockUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.patients = InMemoryPatientRepo()
        self.insurance_plans = InMemoryInsurancePlanRepo()
        self.cases = InMemoryCaseRepo()
        self.workflow_states = InMemoryWorkflowStateRepo()
        self.submissions = InMemorySubmissionRepo()
        self.verifications = InMemoryVerificationRepo()
        self.escalations = InMemoryEscalationRepo()
        self.audits = InMemoryAuditRepo()
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if exc_type:
            self.rollback()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class TestApplicationServices:
    def test_create_authorization_case_success(self) -> None:
        uow = MockUnitOfWork()
        patient = Patient(
            id=PatientId.generate(),
            name_reference="Synthetic Jane",
            ehr_reference="EHR-SYN-2001",
        )
        plan = InsurancePlan(
            id=PlanId.generate(),
            patient_id=patient.id,
            insurer_reference="INS-BCBS",
            plan_type="PPO",
            member_reference="MEM-998",
        )
        uow.patients.save(patient)
        uow.insurance_plans.save(plan)

        service = CreateAuthorizationCaseService(uow)
        case = service.execute(
            patient_id=patient.id,
            insurance_plan_id=plan.id,
            procedure_type=ProcedureType.MRI_BRAIN,
            clinical_indication="Persistent migraine with visual aura.",
            priority=CasePriority.URGENT,
            actor="dr_alice",
        )

        assert case.current_state == WorkflowState.INITIATED
        assert case.procedure_type == ProcedureType.MRI_BRAIN
        assert uow.committed is True
        assert len(uow.audits.audits) == 1
        assert uow.audits.audits[0].event_type == AuditEventType.CASE_CREATED

    def test_create_case_missing_patient_raises(self) -> None:
        uow = MockUnitOfWork()
        service = CreateAuthorizationCaseService(uow)
        with pytest.raises(EntityNotFoundError, match="Patient"):
            service.execute(
                patient_id=PatientId.generate(),
                insurance_plan_id=PlanId.generate(),
                procedure_type=ProcedureType.MRI_KNEE,
                clinical_indication="ACL tear suspicion",
            )

    def test_transition_workflow_state_success(self) -> None:
        uow = MockUnitOfWork()
        patient = Patient(
            id=PatientId.generate(),
            name_reference="Synthetic Bob",
            ehr_reference="EHR-SYN-3001",
        )
        plan = InsurancePlan(
            id=PlanId.generate(),
            patient_id=patient.id,
            insurer_reference="INS-AETNA",
            plan_type="HMO",
            member_reference="MEM-555",
        )
        uow.patients.save(patient)
        uow.insurance_plans.save(plan)

        create_service = CreateAuthorizationCaseService(uow)
        case = create_service.execute(
            patient_id=patient.id,
            insurance_plan_id=plan.id,
            procedure_type=ProcedureType.MRI_SHOULDER,
            clinical_indication="Rotator cuff injury",
        )

        transition_service = TransitionWorkflowStateService(uow)
        transition = transition_service.execute(
            case_id=case.id,
            to_state=WorkflowState.GATHERING_INFORMATION,
            actor="agent_runner",
            reason="Starting document and insurance gathering.",
        )

        assert transition.from_state == WorkflowState.INITIATED
        assert transition.to_state == WorkflowState.GATHERING_INFORMATION
        assert case.current_state == WorkflowState.GATHERING_INFORMATION
        assert len(uow.workflow_states.transitions) == 1
        assert len(uow.audits.audits) == 2  # Creation + Transition
        assert uow.audits.audits[1].event_type == AuditEventType.STATE_TRANSITION
