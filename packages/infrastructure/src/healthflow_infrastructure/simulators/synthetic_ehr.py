"""Synthetic Electronic Health Record (EHR) Simulator.

Simulates an external hospital EHR system storing synthetic patient records,
diagnoses, and clinical encounter notes. Supports deterministic fault injection.

Ref: docs/architecture/ARCHITECTURE.md §6.1, §13
"""

from healthflow_domain.external_models import EhrPatientRecord

from healthflow_infrastructure.simulators.models import (
    ALL_BENCHMARK_FIXTURES,
    SyntheticCaseFixture,
)


class SyntheticEhrSimulator:
    """In-memory deterministic simulator for external Electronic Health Record systems."""

    def __init__(self, fixtures: dict[str, SyntheticCaseFixture] | None = None) -> None:
        self._fixtures = (
            fixtures if fixtures is not None else dict(ALL_BENCHMARK_FIXTURES)
        )
        self._is_available: bool = True
        self._override_patients: dict[str, EhrPatientRecord] = {}

    def set_availability(self, available: bool) -> None:
        """Simulate EHR system maintenance, network partition, or downtime."""
        self._is_available = available

    def register_patient(
        self, record: EhrPatientRecord, history: list[str] | None = None
    ) -> None:
        """Register an arbitrary synthetic patient into the simulator."""
        self._override_patients[record.patient_id] = record

    def get_patient(self, patient_id: str) -> EhrPatientRecord | None:
        """Retrieve synthetic patient record by ID.

        Returns None if system is unavailable or patient does not exist.
        """
        if not self._is_available:
            return None

        # Check explicit overrides
        if patient_id in self._override_patients:
            return self._override_patients[patient_id]

        # Check fixture dataset
        fixture = self._fixtures.get(patient_id)
        if fixture is None:
            return None

        # If the scenario is explicitly SERVICE_UNAVAILABLE, simulate outage
        if fixture.is_transient_failure:
            return None

        return fixture.patient

    def get_clinical_history(self, patient_id: str) -> list[str]:
        """Retrieve clinical encounter history for the given patient."""
        if not self._is_available:
            return []

        fixture = self._fixtures.get(patient_id)
        if fixture is None or fixture.is_transient_failure:
            return []

        return list(fixture.clinical_history)
