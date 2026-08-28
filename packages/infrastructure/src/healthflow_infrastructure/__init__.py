"""HealthFlow Infrastructure Layer.

PostgreSQL persistence adapters, SQLAlchemy 2.x ORM models, and repository implementations.

Ref: docs/architecture/ARCHITECTURE.md §2.5, §14
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

__all__ = [
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
    "SubmissionRecordModel",
    "VerificationRecordModel",
    "WorkflowTransitionModel",
    "create_db_engine",
    "create_session_factory",
    "session_scope",
]
