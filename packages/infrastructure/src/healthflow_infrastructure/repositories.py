"""HealthFlow PostgreSQL Repository Implementations.

Concrete implementations of domain repository ports using SQLAlchemy 2.x and PostgreSQL.
Enforces domain isolation: takes domain entities in, returns domain entities out.

Ref: docs/architecture/ARCHITECTURE.md §6, §14
"""

from collections.abc import Sequence
from typing import Self

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
from healthflow_domain.identifiers import (
    CaseId,
    EscalationId,
    PatientId,
    PlanId,
    SubmissionId,
    VerificationId,
)
from healthflow_domain.ports import (
    AuditRepository,
    AuthorizationCaseRepository,
    EscalationRepository,
    InsurancePlanRepository,
    PatientRepository,
    SubmissionRepository,
    UnitOfWork,
    VerificationRepository,
    WorkflowStateRepository,
)
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from healthflow_infrastructure.mappers import (
    audit_to_model,
    case_to_model,
    escalation_to_model,
    insurance_plan_to_model,
    model_to_audit,
    model_to_case,
    model_to_escalation,
    model_to_insurance_plan,
    model_to_patient,
    model_to_submission,
    model_to_transition,
    model_to_verification,
    patient_to_model,
    submission_to_model,
    transition_to_model,
    verification_to_model,
)
from healthflow_infrastructure.models import (
    AuditRecordModel,
    AuthorizationCaseModel,
    EscalationRecordModel,
    InsurancePlanModel,
    PatientModel,
    SubmissionRecordModel,
    VerificationRecordModel,
    WorkflowTransitionModel,
)


class PostgresPatientRepository(PatientRepository):
    """PostgreSQL implementation of PatientRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, patient_id: PatientId) -> Patient | None:
        stmt = select(PatientModel).where(PatientModel.id == str(patient_id))
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_patient(result) if result else None

    def get_by_ehr_reference(self, ehr_reference: str) -> Patient | None:
        stmt = select(PatientModel).where(PatientModel.ehr_reference == ehr_reference)
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_patient(result) if result else None

    def save(self, patient: Patient) -> None:
        existing = self._session.get(PatientModel, str(patient.id))
        if existing:
            existing.name_reference = patient.name_reference
            existing.ehr_reference = patient.ehr_reference
            existing.is_synthetic = patient.is_synthetic
        else:
            model = patient_to_model(patient)
            self._session.add(model)


class PostgresInsurancePlanRepository(InsurancePlanRepository):
    """PostgreSQL implementation of InsurancePlanRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, plan_id: PlanId) -> InsurancePlan | None:
        stmt = select(InsurancePlanModel).where(InsurancePlanModel.id == str(plan_id))
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_insurance_plan(result) if result else None

    def get_by_patient_id(self, patient_id: PatientId) -> Sequence[InsurancePlan]:
        stmt = select(InsurancePlanModel).where(
            InsurancePlanModel.patient_id == str(patient_id)
        )
        results = self._session.execute(stmt).scalars().all()
        return [model_to_insurance_plan(m) for m in results]

    def save(self, plan: InsurancePlan) -> None:
        existing = self._session.get(InsurancePlanModel, str(plan.id))
        if existing:
            existing.insurer_reference = plan.insurer_reference
            existing.plan_type = plan.plan_type
            existing.member_reference = plan.member_reference
        else:
            model = insurance_plan_to_model(plan)
            self._session.add(model)


class PostgresAuthorizationCaseRepository(AuthorizationCaseRepository):
    """PostgreSQL implementation of AuthorizationCaseRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, case_id: CaseId) -> AuthorizationCase | None:
        stmt = select(AuthorizationCaseModel).where(
            AuthorizationCaseModel.id == str(case_id)
        )
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_case(result) if result else None

    def list_all(self, limit: int = 50, offset: int = 0) -> Sequence[AuthorizationCase]:
        stmt = (
            select(AuthorizationCaseModel)
            .order_by(desc(AuthorizationCaseModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        results = self._session.execute(stmt).scalars().all()
        return [model_to_case(m) for m in results]

    def save(self, case: AuthorizationCase) -> None:
        existing = self._session.get(AuthorizationCaseModel, str(case.id))
        if existing:
            existing.procedure_type = case.procedure_type.value
            existing.clinical_indication = case.clinical_indication
            existing.priority = case.priority.value
            existing.current_state = case.current_state.value
            existing.updated_at = case.updated_at
        else:
            model = case_to_model(case)
            self._session.add(model)


class PostgresWorkflowStateRepository(WorkflowStateRepository):
    """PostgreSQL implementation of WorkflowStateRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record_transition(self, transition: WorkflowTransition) -> None:
        model = transition_to_model(transition)
        self._session.add(model)

    def list_by_case_id(self, case_id: CaseId) -> Sequence[WorkflowTransition]:
        stmt = (
            select(WorkflowTransitionModel)
            .where(WorkflowTransitionModel.case_id == str(case_id))
            .order_by(WorkflowTransitionModel.transitioned_at.asc())
        )
        results = self._session.execute(stmt).scalars().all()
        return [model_to_transition(m) for m in results]


class PostgresSubmissionRepository(SubmissionRepository):
    """PostgreSQL implementation of SubmissionRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, submission_id: SubmissionId) -> SubmissionRecord | None:
        stmt = select(SubmissionRecordModel).where(
            SubmissionRecordModel.id == str(submission_id)
        )
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_submission(result) if result else None

    def get_by_reference(self, reference: str) -> SubmissionRecord | None:
        stmt = select(SubmissionRecordModel).where(
            SubmissionRecordModel.submission_reference == reference
        )
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_submission(result) if result else None

    def list_by_case_id(self, case_id: CaseId) -> Sequence[SubmissionRecord]:
        stmt = (
            select(SubmissionRecordModel)
            .where(SubmissionRecordModel.case_id == str(case_id))
            .order_by(desc(SubmissionRecordModel.submitted_at))
        )
        results = self._session.execute(stmt).scalars().all()
        return [model_to_submission(m) for m in results]

    def save(self, record: SubmissionRecord) -> None:
        existing = self._session.get(SubmissionRecordModel, str(record.id))
        if existing:
            existing.initial_status = record.initial_status
        else:
            model = submission_to_model(record)
            self._session.add(model)


class PostgresVerificationRepository(VerificationRepository):
    """PostgreSQL implementation of VerificationRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, verification_id: VerificationId) -> VerificationRecord | None:
        stmt = select(VerificationRecordModel).where(
            VerificationRecordModel.id == str(verification_id)
        )
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_verification(result) if result else None

    def list_by_case_id(self, case_id: CaseId) -> Sequence[VerificationRecord]:
        stmt = (
            select(VerificationRecordModel)
            .where(VerificationRecordModel.case_id == str(case_id))
            .order_by(desc(VerificationRecordModel.verified_at))
        )
        results = self._session.execute(stmt).scalars().all()
        return [model_to_verification(m) for m in results]

    def save(self, record: VerificationRecord) -> None:
        model = verification_to_model(record)
        self._session.add(model)


class PostgresEscalationRepository(EscalationRepository):
    """PostgreSQL implementation of EscalationRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, escalation_id: EscalationId) -> EscalationRecord | None:
        stmt = select(EscalationRecordModel).where(
            EscalationRecordModel.id == str(escalation_id)
        )
        result = self._session.execute(stmt).scalar_one_or_none()
        return model_to_escalation(result) if result else None

    def list_by_case_id(self, case_id: CaseId) -> Sequence[EscalationRecord]:
        stmt = (
            select(EscalationRecordModel)
            .where(EscalationRecordModel.case_id == str(case_id))
            .order_by(desc(EscalationRecordModel.escalated_at))
        )
        results = self._session.execute(stmt).scalars().all()
        return [model_to_escalation(m) for m in results]

    def save(self, record: EscalationRecord) -> None:
        existing = self._session.get(EscalationRecordModel, str(record.id))
        if existing:
            existing.resolved_at = record.resolved_at
            existing.resolution_notes = record.resolution_notes
            existing.resolved_by = record.resolved_by
        else:
            model = escalation_to_model(record)
            self._session.add(model)


class PostgresAuditRepository(AuditRepository):
    """PostgreSQL implementation of AuditRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record_event(self, record: AuditRecord) -> None:
        model = audit_to_model(record)
        self._session.add(model)

    def list_by_case_id(self, case_id: CaseId) -> Sequence[AuditRecord]:
        stmt = (
            select(AuditRecordModel)
            .where(AuditRecordModel.case_id == str(case_id))
            .order_by(AuditRecordModel.timestamp.asc())
        )
        results = self._session.execute(stmt).scalars().all()
        return [model_to_audit(m) for m in results]


class PostgresUnitOfWork(UnitOfWork):
    """PostgreSQL implementation of the UnitOfWork pattern."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self.patients = PostgresPatientRepository(self._session)
        self.insurance_plans = PostgresInsurancePlanRepository(self._session)
        self.cases = PostgresAuthorizationCaseRepository(self._session)
        self.workflow_states = PostgresWorkflowStateRepository(self._session)
        self.submissions = PostgresSubmissionRepository(self._session)
        self.verifications = PostgresVerificationRepository(self._session)
        self.escalations = PostgresEscalationRepository(self._session)
        self.audits = PostgresAuditRepository(self._session)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._session:
            if exc_type:
                self.rollback()
            self._session.close()
            self._session = None

    def commit(self) -> None:
        if self._session:
            self._session.commit()

    def rollback(self) -> None:
        if self._session:
            self._session.rollback()
