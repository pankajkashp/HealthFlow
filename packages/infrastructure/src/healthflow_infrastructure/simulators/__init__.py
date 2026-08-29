"""Simulated Healthcare Systems & Adapters.

Provides synthetic Electronic Health Record, Payer, Document Store,
and Prior-Authorization Portal simulators, along with their Clean Architecture adapters.

Ref: docs/architecture/ARCHITECTURE.md §6, §13
"""

from healthflow_infrastructure.simulators.adapters import (
    SyntheticAuthorizationGatewayAdapter,
    SyntheticAuthorizationStatusAdapter,
    SyntheticDocumentStoreAdapter,
    SyntheticEhrAdapter,
    SyntheticPayerAdapter,
    SyntheticVerificationAdapter,
)
from healthflow_infrastructure.simulators.models import (
    ALL_BENCHMARK_FIXTURES,
    FIXTURE_CASE_1_SUCCESS,
    FIXTURE_CASE_2_MISSING_DOC,
    FIXTURE_CASE_3_CONFLICT,
    FIXTURE_CASE_4_DENIAL,
    FIXTURE_CASE_5_UNAVAILABLE,
    FIXTURE_CASE_6_FALSE_SUCCESS,
    SimulatorScenario,
    SyntheticCaseFixture,
)
from healthflow_infrastructure.simulators.synthetic_authorization_portal import (
    SyntheticAuthorizationPortalSimulator,
)
from healthflow_infrastructure.simulators.synthetic_document_store import (
    SyntheticDocumentStoreSimulator,
)
from healthflow_infrastructure.simulators.synthetic_ehr import (
    SyntheticEhrSimulator,
)
from healthflow_infrastructure.simulators.synthetic_payer import (
    SyntheticPayerSimulator,
)

__all__ = [
    "ALL_BENCHMARK_FIXTURES",
    "FIXTURE_CASE_1_SUCCESS",
    "FIXTURE_CASE_2_MISSING_DOC",
    "FIXTURE_CASE_3_CONFLICT",
    "FIXTURE_CASE_4_DENIAL",
    "FIXTURE_CASE_5_UNAVAILABLE",
    "FIXTURE_CASE_6_FALSE_SUCCESS",
    "SimulatorScenario",
    "SyntheticAuthorizationGatewayAdapter",
    "SyntheticAuthorizationPortalSimulator",
    "SyntheticAuthorizationStatusAdapter",
    "SyntheticCaseFixture",
    "SyntheticDocumentStoreAdapter",
    "SyntheticDocumentStoreSimulator",
    "SyntheticEhrAdapter",
    "SyntheticEhrSimulator",
    "SyntheticPayerAdapter",
    "SyntheticPayerSimulator",
    "SyntheticVerificationAdapter",
]
