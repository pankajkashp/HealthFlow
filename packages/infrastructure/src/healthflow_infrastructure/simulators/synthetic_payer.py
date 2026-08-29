"""Synthetic Payer & Insurance System Simulator.

Simulates an external health plan / insurance payer system providing
coverage verification and procedural prior-authorization requirements.

Ref: docs/architecture/ARCHITECTURE.md §6.2, §6.3, §13
"""

from healthflow_domain.external_models import (
    PayerCoverageRecord,
    ProcedureRequirements,
)

from healthflow_infrastructure.simulators.models import (
    ALL_BENCHMARK_FIXTURES,
    SyntheticCaseFixture,
)


class SyntheticPayerSimulator:
    """In-memory deterministic simulator for external insurance payer systems."""

    def __init__(self, fixtures: dict[str, SyntheticCaseFixture] | None = None) -> None:
        self._fixtures = (
            fixtures if fixtures is not None else dict(ALL_BENCHMARK_FIXTURES)
        )
        self._is_available: bool = True
        self._override_coverages: dict[str, PayerCoverageRecord] = {}
        self._override_requirements: dict[str, ProcedureRequirements] = {}

    def set_availability(self, available: bool) -> None:
        """Simulate payer API downtime or network timeout."""
        self._is_available = available

    def register_coverage(self, coverage: PayerCoverageRecord) -> None:
        """Register custom coverage record for testing."""
        key = f"{coverage.patient_id}:{coverage.plan_id}"
        self._override_coverages[key] = coverage

    def register_requirements(self, requirements: ProcedureRequirements) -> None:
        """Register custom prior authorization requirements for testing."""
        key = f"{requirements.plan_id}:{requirements.procedure_type}"
        self._override_requirements[key] = requirements

    def get_coverage(self, patient_id: str, plan_id: str) -> PayerCoverageRecord | None:
        """Check coverage and eligibility for patient under specified plan."""
        if not self._is_available:
            return None

        # Check explicit overrides
        override_key = f"{patient_id}:{plan_id}"
        if override_key in self._override_coverages:
            return self._override_coverages[override_key]

        # Check fixture dataset
        fixture = self._fixtures.get(patient_id)
        if fixture is None or fixture.coverage.plan_id != plan_id:
            return None

        if fixture.is_transient_failure:
            return None

        return fixture.coverage

    def get_requirements(
        self, plan_id: str, procedure_type: str
    ) -> ProcedureRequirements | None:
        """Retrieve procedural prior authorization requirements."""
        if not self._is_available:
            return None

        override_key = f"{plan_id}:{procedure_type}"
        if override_key in self._override_requirements:
            return self._override_requirements[override_key]

        for fixture in self._fixtures.values():
            if (
                fixture.requirements.plan_id == plan_id
                and fixture.requirements.procedure_type == procedure_type
            ):
                if fixture.is_transient_failure:
                    return None
                return fixture.requirements

        return None
