"""HealthFlow Infrastructure Layer.

PostgreSQL persistence adapters, SQLAlchemy 2.x ORM models, repository implementations,
and simulated external healthcare systems.

Ref: docs/architecture/ARCHITECTURE.md §2.5, §13, §14
"""

from healthflow_infrastructure.database import (
    Base,
    create_db_engine,
    create_session_factory,
    session_scope,
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
from healthflow_infrastructure.repositories import (
    PostgresAuditRepository,
    PostgresAuthorizationCaseRepository,
    PostgresEscalationRepository,
    PostgresInsurancePlanRepository,
    PostgresPatientRepository,
    PostgresSubmissionRepository,
    PostgresUnitOfWork,
    PostgresVerificationRepository,
    PostgresWorkflowStateRepository,
)
from healthflow_infrastructure.simulators import (
    ALL_BENCHMARK_FIXTURES,
    SimulatorScenario,
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

__all__ = [
    "ALL_BENCHMARK_FIXTURES",
    "AuditRecordModel",
    "AuthorizationCaseModel",
    "Base",
    "EscalationRecordModel",
    "InsurancePlanModel",
    "PatientModel",
    "PostgresAuditRepository",
    "PostgresAuthorizationCaseRepository",
    "PostgresEscalationRepository",
    "PostgresInsurancePlanRepository",
    "PostgresPatientRepository",
    "PostgresSubmissionRepository",
    "PostgresUnitOfWork",
    "PostgresVerificationRepository",
    "PostgresWorkflowStateRepository",
    "SimulatorScenario",
    "SubmissionRecordModel",
    "SyntheticAuthorizationGatewayAdapter",
    "SyntheticAuthorizationPortalSimulator",
    "SyntheticAuthorizationStatusAdapter",
    "SyntheticDocumentStoreAdapter",
    "SyntheticDocumentStoreSimulator",
    "SyntheticEhrAdapter",
    "SyntheticEhrSimulator",
    "SyntheticPayerAdapter",
    "SyntheticPayerSimulator",
    "SyntheticVerificationAdapter",
    "VerificationRecordModel",
    "WorkflowTransitionModel",
    "create_db_engine",
    "create_session_factory",
    "session_scope",
]
