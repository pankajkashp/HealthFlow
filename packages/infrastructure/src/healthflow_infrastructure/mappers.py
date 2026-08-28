"""HealthFlow Domain <-> ORM Model Mappers.

Bidirectional mapping between pure domain entities and SQLAlchemy ORM models.
Isolates the domain from database concerns and prevents ORM leakage.

Ref: docs/architecture/ARCHITECTURE.md §14.3
"""

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
from healthflow_domain.enums import (
    AuditEventType,
    CasePriority,
    EscalationReason,
    ProcedureType,
    VerificationStatus,
    WorkflowState,
)
from healthflow_domain.identifiers import (
    AuditId,
    CaseId,
    EscalationId,
    PatientId,
    PlanId,
    SubmissionId,
    TransitionId,
    VerificationId,
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


def patient_to_model(entity: Patient) -> PatientModel:
    return PatientModel(
        id=str(entity.id),
        name_reference=entity.name_reference,
        ehr_reference=entity.ehr_reference,
        is_synthetic=entity.is_synthetic,
        created_at=entity.created_at,
    )


def model_to_patient(model: PatientModel) -> Patient:
    return Patient(
        id=PatientId(model.id),
        name_reference=model.name_reference,
        ehr_reference=model.ehr_reference,
        is_synthetic=model.is_synthetic,
        created_at=model.created_at,
    )


def insurance_plan_to_model(entity: InsurancePlan) -> InsurancePlanModel:
    return InsurancePlanModel(
        id=str(entity.id),
        patient_id=str(entity.patient_id),
        insurer_reference=entity.insurer_reference,
        plan_type=entity.plan_type,
        member_reference=entity.member_reference,
        created_at=entity.created_at,
    )


def model_to_insurance_plan(model: InsurancePlanModel) -> InsurancePlan:
    return InsurancePlan(
        id=PlanId(model.id),
        patient_id=PatientId(model.patient_id),
        insurer_reference=model.insurer_reference,
        plan_type=model.plan_type,
        member_reference=model.member_reference,
        created_at=model.created_at,
    )


def case_to_model(entity: AuthorizationCase) -> AuthorizationCaseModel:
    return AuthorizationCaseModel(
        id=str(entity.id),
        patient_id=str(entity.patient_id),
        insurance_plan_id=str(entity.insurance_plan_id),
        procedure_type=entity.procedure_type.value,
        clinical_indication=entity.clinical_indication,
        priority=entity.priority.value,
        current_state=entity.current_state.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def model_to_case(model: AuthorizationCaseModel) -> AuthorizationCase:
    return AuthorizationCase(
        id=CaseId(model.id),
        patient_id=PatientId(model.patient_id),
        insurance_plan_id=PlanId(model.insurance_plan_id),
        procedure_type=ProcedureType(model.procedure_type),
        clinical_indication=model.clinical_indication,
        priority=CasePriority(model.priority),
        current_state=WorkflowState(model.current_state),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def transition_to_model(entity: WorkflowTransition) -> WorkflowTransitionModel:
    return WorkflowTransitionModel(
        id=str(entity.id),
        case_id=str(entity.case_id),
        from_state=entity.from_state.value,
        to_state=entity.to_state.value,
        reason=entity.reason,
        actor=entity.actor,
        transitioned_at=entity.transitioned_at,
    )


def model_to_transition(model: WorkflowTransitionModel) -> WorkflowTransition:
    return WorkflowTransition(
        id=TransitionId(model.id),
        case_id=CaseId(model.case_id),
        from_state=WorkflowState(model.from_state),
        to_state=WorkflowState(model.to_state),
        reason=model.reason,
        actor=model.actor,
        transitioned_at=model.transitioned_at,
    )


def submission_to_model(entity: SubmissionRecord) -> SubmissionRecordModel:
    return SubmissionRecordModel(
        id=str(entity.id),
        case_id=str(entity.case_id),
        submission_reference=entity.submission_reference,
        payload_hash=entity.payload_hash,
        initial_status=entity.initial_status,
        submitted_at=entity.submitted_at,
    )


def model_to_submission(model: SubmissionRecordModel) -> SubmissionRecord:
    return SubmissionRecord(
        id=SubmissionId(model.id),
        case_id=CaseId(model.case_id),
        submission_reference=model.submission_reference,
        payload_hash=model.payload_hash,
        initial_status=model.initial_status,
        submitted_at=model.submitted_at,
    )


def verification_to_model(entity: VerificationRecord) -> VerificationRecordModel:
    return VerificationRecordModel(
        id=str(entity.id),
        case_id=str(entity.case_id),
        submission_reference=entity.submission_reference,
        status=entity.status.value,
        verification_details=entity.verification_details,
        verified_at=entity.verified_at,
    )


def model_to_verification(model: VerificationRecordModel) -> VerificationRecord:
    return VerificationRecord(
        id=VerificationId(model.id),
        case_id=CaseId(model.case_id),
        submission_reference=model.submission_reference,
        status=VerificationStatus(model.status),
        verification_details=model.verification_details,
        verified_at=model.verified_at,
    )


def escalation_to_model(entity: EscalationRecord) -> EscalationRecordModel:
    return EscalationRecordModel(
        id=str(entity.id),
        case_id=str(entity.case_id),
        reason=entity.reason.value,
        from_state=entity.from_state.value,
        notes=entity.notes,
        escalated_at=entity.escalated_at,
        resolved_at=entity.resolved_at,
        resolution_notes=entity.resolution_notes,
        resolved_by=entity.resolved_by,
    )


def model_to_escalation(model: EscalationRecordModel) -> EscalationRecord:
    return EscalationRecord(
        id=EscalationId(model.id),
        case_id=CaseId(model.case_id),
        reason=EscalationReason(model.reason),
        from_state=WorkflowState(model.from_state),
        notes=model.notes,
        escalated_at=model.escalated_at,
        resolved_at=model.resolved_at,
        resolution_notes=model.resolution_notes,
        resolved_by=model.resolved_by,
    )


def audit_to_model(entity: AuditRecord) -> AuditRecordModel:
    return AuditRecordModel(
        id=str(entity.id),
        event_type=entity.event_type.value,
        case_id=str(entity.case_id) if entity.case_id else None,
        details=entity.details,
        actor=entity.actor,
        timestamp=entity.timestamp,
    )


def model_to_audit(model: AuditRecordModel) -> AuditRecord:
    return AuditRecord(
        id=AuditId(model.id),
        event_type=AuditEventType(model.event_type),
        case_id=CaseId(model.case_id) if model.case_id else None,
        details=model.details,
        actor=model.actor,
        timestamp=model.timestamp,
    )
