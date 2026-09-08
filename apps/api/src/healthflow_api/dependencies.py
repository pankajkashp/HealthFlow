"""Composition root for the HealthFlow API.

Decision 3 (docs/phases/PHASE_06_WALKTHROUGH.md): docs/architecture/ARCHITECTURE.md §4.1 prohibits
apps/api from depending on packages/domain or packages/infrastructure directly. Taken literally,
nothing could ever construct a database session or the synthetic-environment adapters for a real
request. This module is the one, narrow, documented exception: it is the only file in apps/api that
imports those layers, to wire concrete adapters into the application-layer services. Route handlers
(routes/cases.py) never import domain or infrastructure — they only call CaseOrchestrator methods,
which already return API schema objects (schemas.py), and contain no business logic of their own.
"""

from __future__ import annotations

from functools import lru_cache

from healthflow_agent import (
    AgentConfig,
    HealthFlowAgent,
    LlmDrivenWorkflowRunner,
    WorkflowStateSync,
)
from healthflow_application import (
    AgentTools,
    CreateAuthorizationCaseService,
    TransitionWorkflowStateService,
)
from healthflow_domain.entities import AuthorizationCase
from healthflow_domain.enums import ProcedureType, VerificationStatus, WorkflowState
from healthflow_domain.exceptions import EntityNotFoundError
from healthflow_domain.identifiers import CaseId, PatientId, PlanId
from healthflow_infrastructure.database import create_db_engine, create_session_factory
from healthflow_infrastructure.repositories import PostgresUnitOfWork
from healthflow_infrastructure.simulators import (
    ALL_BENCHMARK_FIXTURES,
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

from healthflow_api.schemas import (
    CaseDetail,
    CaseSummary,
    PatientOption,
    RunCaseResponse,
    ToolCallStepOut,
    WorkflowTransitionOut,
)

# --- Process-wide synthetic environment ---------------------------------------------------
# The simulated EHR/payer/document-store/portal are a shared, long-running backend (mirroring
# how a real external system would be shared, not per-request state) — a single portal instance
# holds submission state that get_authorization_status/verify_authorization_outcome both read.
_ehr_simulator = SyntheticEhrSimulator()
_payer_simulator = SyntheticPayerSimulator()
_document_simulator = SyntheticDocumentStoreSimulator()
_portal_simulator = SyntheticAuthorizationPortalSimulator()


@lru_cache
def _session_factory():  # type: ignore[no-untyped-def]
    engine = create_db_engine()
    return create_session_factory(engine)


def _new_uow() -> PostgresUnitOfWork:
    return PostgresUnitOfWork(_session_factory())


@lru_cache
def get_agent_config() -> AgentConfig:
    return AgentConfig()


def _build_agent_tools() -> AgentTools:
    return AgentTools(
        ehr_port=SyntheticEhrAdapter(_ehr_simulator),
        payer_port=SyntheticPayerAdapter(_payer_simulator),
        document_store_port=SyntheticDocumentStoreAdapter(_document_simulator),
        gateway_port=SyntheticAuthorizationGatewayAdapter(_portal_simulator),
        status_gateway_port=SyntheticAuthorizationStatusAdapter(_portal_simulator),
        verification_port=SyntheticVerificationAdapter(_portal_simulator),
        workflow_state=WorkflowState.PREPARING_SUBMISSION,
    )


def _case_to_summary(case: AuthorizationCase, patient_name: str) -> CaseSummary:
    return CaseSummary(
        case_id=str(case.id),
        patient_id=str(case.patient_id),
        patient_name=patient_name,
        procedure_type=case.procedure_type.value,
        current_state=case.current_state.value,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
    )


class CaseOrchestrator:
    """The only place that ties the LLM agent, the domain state machine, and Postgres together."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def list_patient_options(self) -> list[PatientOption]:
        return [
            PatientOption(
                patient_id=patient_id,
                name=fixture.patient.name_reference,
                scenario=fixture.scenario.value,
                procedure_type=fixture.requirements.procedure_type,
            )
            for patient_id, fixture in ALL_BENCHMARK_FIXTURES.items()
        ]

    def list_cases(self) -> list[CaseSummary]:
        uow = _new_uow()
        with uow:
            cases = uow.cases.list_all(limit=50)
            summaries = []
            for case in cases:
                patient = uow.patients.get_by_id(case.patient_id)
                summaries.append(
                    _case_to_summary(
                        case, patient.name_reference if patient else str(case.patient_id)
                    )
                )
            return summaries

    def create_case(self, patient_id: str) -> CaseDetail:
        fixture = ALL_BENCHMARK_FIXTURES.get(patient_id)
        if fixture is None:
            raise LookupError(f"Unknown demo patient_id: {patient_id!r}")

        service = CreateAuthorizationCaseService(_new_uow())
        try:
            case = service.execute(
                patient_id=PatientId(patient_id),
                insurance_plan_id=PlanId(fixture.coverage.plan_id),
                procedure_type=ProcedureType(fixture.requirements.procedure_type),
                clinical_indication=fixture.patient.clinical_notes_summary,
            )
        except EntityNotFoundError as err:
            raise LookupError(
                f"{err}. Run scripts/seed_demo_data.py to seed benchmark patients first."
            ) from err
        return self.get_case_detail(str(case.id))

    def get_case_detail(self, case_id: str) -> CaseDetail:
        uow = _new_uow()
        with uow:
            case = uow.cases.get_by_id(CaseId(case_id))
            if case is None:
                raise LookupError(f"Unknown case_id: {case_id!r}")
            patient = uow.patients.get_by_id(case.patient_id)
            transitions = uow.workflow_states.list_by_case_id(case.id)

        summary = _case_to_summary(
            case, patient.name_reference if patient else str(case.patient_id)
        )
        return CaseDetail(
            **summary.model_dump(),
            clinical_indication=case.clinical_indication,
            priority=case.priority.value,
            transitions=[
                WorkflowTransitionOut(
                    from_state=t.from_state.value,
                    to_state=t.to_state.value,
                    reason=t.reason,
                    actor=t.actor,
                    transitioned_at=t.transitioned_at.isoformat(),
                )
                for t in transitions
            ],
        )

    def run_case(self, case_id: str) -> RunCaseResponse:
        uow = _new_uow()
        with uow:
            case = uow.cases.get_by_id(CaseId(case_id))
        if case is None:
            raise LookupError(f"Unknown case_id: {case_id!r}")

        patient_identifier = str(case.patient_id)
        fixture = ALL_BENCHMARK_FIXTURES.get(patient_identifier)
        procedure_display = (
            fixture.requirements.procedure_type.replace("_", " ").title()
            if fixture
            else case.procedure_type.value.replace("_", " ").title()
        )
        goal = f"Obtain prior authorization for {procedure_display}"

        def persist_transition(
            to_state: WorkflowState, verification_status: VerificationStatus | None, reason: str
        ) -> None:
            TransitionWorkflowStateService(_new_uow()).execute(
                case_id=case.id,
                to_state=to_state,
                verification_status=verification_status,
                actor="agent",
                reason=reason,
            )

        tools = _build_agent_tools()

        if self._config.llm_provider == "scripted":
            trace = HealthFlowAgent(tools=tools, config=self._config).execute_workflow(
                goal=goal, patient_identifier=patient_identifier
            )
            sync = WorkflowStateSync(
                current_state=case.current_state, on_transition=persist_transition
            )
            final_state = sync.replay(trace.steps)
        else:
            runner = LlmDrivenWorkflowRunner(
                tools=tools,
                config=self._config,
                current_state=case.current_state,
                on_transition=persist_transition,
            )
            trace = runner.execute_workflow(goal=goal, patient_identifier=patient_identifier)
            final_state = runner.current_state

        return RunCaseResponse(
            case_id=case_id,
            status=trace.status,
            is_verified=trace.is_verified,
            final_response=trace.final_response,
            current_state=final_state.value,
            steps=[
                ToolCallStepOut(
                    tool_name=s.tool_name,
                    arguments=s.arguments,
                    result=s.result,
                    success=s.success,
                )
                for s in trace.steps
            ],
        )


@lru_cache
def get_case_orchestrator() -> CaseOrchestrator:
    return CaseOrchestrator(get_agent_config())
