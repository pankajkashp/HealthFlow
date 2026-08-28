"""HealthFlow Application Services.

Use-case orchestrators for authorization cases and workflow transitions.
These services depend exclusively on domain entities and repository protocols (Ports).
They have ZERO dependencies on infrastructure implementations (SQLAlchemy, PostgreSQL, etc.).

Ref: docs/architecture/ARCHITECTURE.md §2.3, §4.5
"""

from healthflow_domain.entities import (
    AuditRecord,
    AuthorizationCase,
    WorkflowTransition,
)
from healthflow_domain.enums import (
    AuditEventType,
    CasePriority,
    ProcedureType,
    VerificationStatus,
    WorkflowState,
)
from healthflow_domain.exceptions import EntityNotFoundError
from healthflow_domain.identifiers import (
    AuditId,
    CaseId,
    PatientId,
    PlanId,
)
from healthflow_domain.ports import UnitOfWork


class CreateAuthorizationCaseService:
    """Use-case service for creating a new MRI prior-authorization case."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        patient_id: PatientId,
        insurance_plan_id: PlanId,
        procedure_type: ProcedureType,
        clinical_indication: str,
        priority: CasePriority = CasePriority.ROUTINE,
        actor: str = "system",
    ) -> AuthorizationCase:
        """Create and persist a new authorization case in INITIATED state."""
        with self._uow:
            # Verify patient exists
            patient = self._uow.patients.get_by_id(patient_id)
            if not patient:
                raise EntityNotFoundError("Patient", str(patient_id))

            # Verify plan exists
            plan = self._uow.insurance_plans.get_by_id(insurance_plan_id)
            if not plan:
                raise EntityNotFoundError("InsurancePlan", str(insurance_plan_id))

            case = AuthorizationCase(
                id=CaseId.generate(),
                patient_id=patient_id,
                insurance_plan_id=insurance_plan_id,
                procedure_type=procedure_type,
                clinical_indication=clinical_indication,
                priority=priority,
                current_state=WorkflowState.INITIATED,
            )
            self._uow.cases.save(case)

            # Record audit event
            audit = AuditRecord(
                id=AuditId.generate(),
                event_type=AuditEventType.CASE_CREATED,
                case_id=case.id,
                details={
                    "procedure_type": procedure_type.value,
                    "priority": priority.value,
                    "initial_state": WorkflowState.INITIATED.value,
                },
                actor=actor,
            )
            self._uow.audits.record_event(audit)

            self._uow.commit()
            return case


class TransitionWorkflowStateService:
    """Use-case service for transitioning an authorization case's workflow state."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        case_id: CaseId,
        to_state: WorkflowState,
        verification_status: VerificationStatus | None = None,
        actor: str = "system",
        reason: str = "",
    ) -> WorkflowTransition:
        """Transition an authorization case to a target state adhering to all domain rules."""
        with self._uow:
            case = self._uow.cases.get_by_id(case_id)
            if not case:
                raise EntityNotFoundError("AuthorizationCase", str(case_id))

            # Domain entity performs state machine validation and state mutation
            transition = case.transition_to(
                to_state=to_state,
                verification_status=verification_status,
                actor=actor,
                reason=reason,
            )

            # Persist updated case and new transition record
            self._uow.cases.save(case)
            self._uow.workflow_states.record_transition(transition)

            # Record audit event
            audit = AuditRecord(
                id=AuditId.generate(),
                event_type=AuditEventType.STATE_TRANSITION,
                case_id=case.id,
                details={
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "reason": transition.reason,
                },
                actor=actor,
            )
            self._uow.audits.record_event(audit)

            self._uow.commit()
            return transition
