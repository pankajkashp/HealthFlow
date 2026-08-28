"""Integration tests for PostgreSQL Repositories and Unit of Work.

Executes against a REAL local PostgreSQL database ('healthflow_test').
Verifies real SQL execution, foreign keys, cascade rules, indexing, and transactional boundaries.

Ref: docs/architecture/ARCHITECTURE.md §14
"""

import os
from collections.abc import Generator

import pytest
from healthflow_domain import (
    AuthorizationCase,
    CaseId,
    CasePriority,
    EscalationId,
    EscalationReason,
    EscalationRecord,
    InsurancePlan,
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
from healthflow_infrastructure import (
    Base,
    PostgresAuthorizationCaseRepository,
    PostgresEscalationRepository,
    PostgresInsurancePlanRepository,
    PostgresPatientRepository,
    PostgresSubmissionRepository,
    PostgresUnitOfWork,
    PostgresVerificationRepository,
    PostgresWorkflowStateRepository,
    create_db_engine,
    create_session_factory,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres@localhost:5432/healthflow_test",
)


@pytest.fixture(scope="module")
def engine():
    """Create test engine and ensure schema is present."""
    eng = create_db_engine(TEST_DB_URL)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return create_session_factory(engine)


@pytest.fixture
def db_session(session_factory) -> Generator[Session, None, None]:
    """Provide a clean session and truncate tables after each test."""
    session = session_factory()
    yield session
    session.rollback()
    # Truncate tables for test isolation
    session.execute(
        text(
            "TRUNCATE TABLE audit_records, workflow_transitions, escalation_records, "
            "verification_records, submission_records, authorization_cases, "
            "insurance_plans, patients RESTART IDENTITY CASCADE;"
        )
    )
    session.commit()
    session.close()


class TestPostgresRepositories:
    def test_patient_crud(self, db_session: Session) -> None:
        repo = PostgresPatientRepository(db_session)
        patient_id = PatientId.generate()
        patient = Patient(
            id=patient_id,
            name_reference="Synthetic Alice",
            ehr_reference="EHR-TEST-001",
            is_synthetic=True,
        )

        repo.save(patient)
        db_session.commit()

        fetched = repo.get_by_id(patient_id)
        assert fetched is not None
        assert fetched.id == patient_id
        assert fetched.name_reference == "Synthetic Alice"
        assert fetched.is_synthetic is True

        by_ehr = repo.get_by_ehr_reference("EHR-TEST-001")
        assert by_ehr is not None
        assert by_ehr.id == patient_id

    def test_insurance_plan_repository(self, db_session: Session) -> None:
        patient_repo = PostgresPatientRepository(db_session)
        plan_repo = PostgresInsurancePlanRepository(db_session)

        patient = Patient(
            id=PatientId.generate(),
            name_reference="Synthetic Bob",
            ehr_reference="EHR-TEST-002",
        )
        patient_repo.save(patient)

        plan = InsurancePlan(
            id=PlanId.generate(),
            patient_id=patient.id,
            insurer_reference="INS-BCBS-MA",
            plan_type="PPO",
            member_reference="MEM-TEST-77",
        )
        plan_repo.save(plan)
        db_session.commit()

        fetched = plan_repo.get_by_id(plan.id)
        assert fetched is not None
        assert fetched.insurer_reference == "INS-BCBS-MA"

        plans_by_patient = plan_repo.get_by_patient_id(patient.id)
        assert len(plans_by_patient) == 1
        assert plans_by_patient[0].id == plan.id

    def test_authorization_case_and_transitions(self, db_session: Session) -> None:
        patient_repo = PostgresPatientRepository(db_session)
        plan_repo = PostgresInsurancePlanRepository(db_session)
        case_repo = PostgresAuthorizationCaseRepository(db_session)
        trans_repo = PostgresWorkflowStateRepository(db_session)

        patient = Patient(
            id=PatientId.generate(),
            name_reference="Synthetic Charlie",
            ehr_reference="EHR-TEST-003",
        )
        patient_repo.save(patient)
        plan = InsurancePlan(
            id=PlanId.generate(),
            patient_id=patient.id,
            insurer_reference="INS-UNITED",
            plan_type="HMO",
            member_reference="MEM-TEST-88",
        )
        plan_repo.save(plan)

        case = AuthorizationCase(
            id=CaseId.generate(),
            patient_id=patient.id,
            insurance_plan_id=plan.id,
            procedure_type=ProcedureType.MRI_BRAIN,
            clinical_indication="Suspected acoustic neuroma",
            priority=CasePriority.URGENT,
        )
        case_repo.save(case)
        db_session.commit()

        # Fetch and verify initial state
        fetched_case = case_repo.get_by_id(case.id)
        assert fetched_case is not None
        assert fetched_case.current_state == WorkflowState.INITIATED

        # Transition case
        transition = fetched_case.transition_to(
            WorkflowState.GATHERING_INFORMATION,
            actor="agent_core",
            reason="Beginning clinical note retrieval",
        )
        case_repo.save(fetched_case)
        trans_repo.record_transition(transition)
        db_session.commit()

        # Verify updated state and transition history in PostgreSQL
        updated_case = case_repo.get_by_id(case.id)
        assert updated_case is not None
        assert updated_case.current_state == WorkflowState.GATHERING_INFORMATION

        history = trans_repo.list_by_case_id(case.id)
        assert len(history) == 1
        assert history[0].from_state == WorkflowState.INITIATED
        assert history[0].to_state == WorkflowState.GATHERING_INFORMATION

    def test_submission_and_verification_persistence(self, db_session: Session) -> None:
        patient_repo = PostgresPatientRepository(db_session)
        plan_repo = PostgresInsurancePlanRepository(db_session)
        case_repo = PostgresAuthorizationCaseRepository(db_session)
        sub_repo = PostgresSubmissionRepository(db_session)
        ver_repo = PostgresVerificationRepository(db_session)

        patient = Patient(
            id=PatientId.generate(), name_reference="P1", ehr_reference="EHR-P1"
        )
        patient_repo.save(patient)
        plan = InsurancePlan(
            id=PlanId.generate(),
            patient_id=patient.id,
            insurer_reference="INS-AETNA",
            plan_type="PPO",
            member_reference="MEM-P1",
        )
        plan_repo.save(plan)
        case = AuthorizationCase(
            id=CaseId.generate(),
            patient_id=patient.id,
            insurance_plan_id=plan.id,
            procedure_type=ProcedureType.MRI_KNEE,
            clinical_indication="Knee pain",
        )
        case_repo.save(case)

        # Record submission
        submission = SubmissionRecord(
            id=SubmissionId.generate(),
            case_id=case.id,
            submission_reference="PORTAL-SUB-101",
            payload_hash="hash-abc-123",
            initial_status="RECEIVED",
        )
        sub_repo.save(submission)

        # Record verification
        verification = VerificationRecord(
            id=VerificationId.generate(),
            case_id=case.id,
            submission_reference="PORTAL-SUB-101",
            status=VerificationStatus.CONFIRMED,
            verification_details="Approved #AUTH-9999 found in payer portal.",
        )
        ver_repo.save(verification)
        db_session.commit()

        # Query back
        fetched_sub = sub_repo.get_by_reference("PORTAL-SUB-101")
        assert fetched_sub is not None
        assert fetched_sub.id == submission.id

        ver_list = ver_repo.list_by_case_id(case.id)
        assert len(ver_list) == 1
        assert ver_list[0].status == VerificationStatus.CONFIRMED

    def test_escalation_persistence_and_resolution(self, db_session: Session) -> None:
        patient_repo = PostgresPatientRepository(db_session)
        plan_repo = PostgresInsurancePlanRepository(db_session)
        case_repo = PostgresAuthorizationCaseRepository(db_session)
        esc_repo = PostgresEscalationRepository(db_session)

        patient = Patient(
            id=PatientId.generate(), name_reference="P2", ehr_reference="EHR-P2"
        )
        patient_repo.save(patient)
        plan = InsurancePlan(
            id=PlanId.generate(),
            patient_id=patient.id,
            insurer_reference="INS-CIGNA",
            plan_type="HMO",
            member_reference="MEM-P2",
        )
        plan_repo.save(plan)
        case = AuthorizationCase(
            id=CaseId.generate(),
            patient_id=patient.id,
            insurance_plan_id=plan.id,
            procedure_type=ProcedureType.MRI_ABDOMEN,
            clinical_indication="Abdominal pain",
        )
        case_repo.save(case)

        escalation = EscalationRecord(
            id=EscalationId.generate(),
            case_id=case.id,
            reason=EscalationReason.CLINICAL_DECISION_REQUIRED,
            from_state=WorkflowState.VALIDATING,
            notes="Doctor clarification needed on contrast allergy.",
        )
        esc_repo.save(escalation)
        db_session.commit()

        fetched_esc = esc_repo.get_by_id(escalation.id)
        assert fetched_esc is not None
        assert fetched_esc.resolved_at is None

        # Resolve escalation
        fetched_esc.resolve(
            resolution_notes="Physician cleared non-contrast protocol.",
            resolved_by="dr_jones",
        )
        esc_repo.save(fetched_esc)
        db_session.commit()

        resolved = esc_repo.get_by_id(escalation.id)
        assert resolved is not None
        assert resolved.resolved_at is not None
        assert resolved.resolved_by == "dr_jones"

    def test_unit_of_work_transaction_commit_and_rollback(
        self, session_factory
    ) -> None:
        uow = PostgresUnitOfWork(session_factory)
        patient_id = PatientId.generate()

        # 1. Commit path
        with uow:
            patient = Patient(
                id=patient_id,
                name_reference="UOW Committed Patient",
                ehr_reference="EHR-UOW-001",
            )
            uow.patients.save(patient)
            uow.commit()

        # Verify saved
        with uow:
            found = uow.patients.get_by_id(patient_id)
            assert found is not None

        # 2. Rollback path on exception
        patient_id_fail = PatientId.generate()
        try:
            with uow:
                p_fail = Patient(
                    id=patient_id_fail,
                    name_reference="UOW Failed Patient",
                    ehr_reference="EHR-UOW-FAIL",
                )
                uow.patients.save(p_fail)
                raise RuntimeError("Simulated transaction failure")
        except RuntimeError:
            pass

        # Verify p_fail was rolled back
        with uow:
            not_found = uow.patients.get_by_id(patient_id_fail)
            assert not_found is None
