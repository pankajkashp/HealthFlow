"""Integration tests for Synthetic EHR Simulator & Adapter.

Verifies patient retrieval, clinical history, fault injection, and EhrPort compliance.
Ref: docs/architecture/ARCHITECTURE.md §6.1, §13
"""

from healthflow_domain import EhrPort, PatientId
from healthflow_domain.external_models import EhrPatientRecord
from healthflow_infrastructure.simulators import (
    SyntheticEhrAdapter,
    SyntheticEhrSimulator,
)


class TestSyntheticEhr:
    def test_get_valid_patient_record(self) -> None:
        sim = SyntheticEhrSimulator()
        patient = sim.get_patient("pat_jenkins_001")
        assert patient is not None
        assert patient.patient_id == "pat_jenkins_001"
        assert patient.is_synthetic is True
        assert "Sarah Jenkins" in patient.name_reference
        assert patient.conservative_therapy_completed is True
        assert patient.conservative_therapy_duration_weeks == 8

    def test_get_nonexistent_patient_returns_none(self) -> None:
        sim = SyntheticEhrSimulator()
        assert sim.get_patient("pat_nonexistent_999") is None

    def test_clinical_history_retrieval(self) -> None:
        sim = SyntheticEhrSimulator()
        history = sim.get_clinical_history("pat_jenkins_001")
        assert len(history) >= 2
        assert any("physical therapy" in h for h in history)

    def test_simulated_ehr_downtime(self) -> None:
        sim = SyntheticEhrSimulator()
        sim.set_availability(False)
        assert sim.get_patient("pat_jenkins_001") is None
        assert sim.get_clinical_history("pat_jenkins_001") == []

        sim.set_availability(True)
        assert sim.get_patient("pat_jenkins_001") is not None

    def test_dynamic_patient_registration(self) -> None:
        sim = SyntheticEhrSimulator()
        custom_patient = EhrPatientRecord(
            patient_id="pat_custom_100",
            name_reference="Synthetic Custom",
            ehr_reference="EHR-CUSTOM-100",
            clinical_notes_summary="L4-L5 disc protrusion.",
            active_diagnoses=["M51.26"],
            conservative_therapy_completed=True,
            conservative_therapy_duration_weeks=6,
            is_synthetic=True,
        )
        sim.register_patient(custom_patient)
        fetched = sim.get_patient("pat_custom_100")
        assert fetched is not None
        assert fetched.patient_id == "pat_custom_100"

    def test_ehr_adapter_implements_port(self) -> None:
        sim = SyntheticEhrSimulator()
        adapter: EhrPort = SyntheticEhrAdapter(sim)

        record = adapter.get_patient_record(PatientId("pat_jenkins_001"))
        assert record is not None
        assert record.patient_id == "pat_jenkins_001"

        history = adapter.get_clinical_history(PatientId("pat_jenkins_001"))
        assert len(history) >= 2
