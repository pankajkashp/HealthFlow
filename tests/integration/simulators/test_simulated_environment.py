"""Cross-system integration tests for the Simulated Healthcare Environment.

Validates that all benchmark cases maintain consistent synthetic state across
the EHR, Payer, Document Store, and Authorization Portal.
Ref: docs/architecture/ARCHITECTURE.md §13
"""

import pytest
from healthflow_domain.external_models import PortalSubmissionPayload
from healthflow_infrastructure.simulators import (
    ALL_BENCHMARK_FIXTURES,
    SyntheticAuthorizationPortalSimulator,
    SyntheticDocumentStoreSimulator,
    SyntheticEhrSimulator,
    SyntheticPayerSimulator,
)


class TestSimulatedEnvironmentCaseConsistency:
    @pytest.mark.parametrize(
        "patient_id, fixture", list(ALL_BENCHMARK_FIXTURES.items())
    )
    def test_fixture_integrity_and_identifier_consistency(
        self, patient_id: str, fixture
    ) -> None:
        """Verify that every fixture maintains consistent cross-system identifiers."""
        assert fixture.patient.patient_id == patient_id
        assert fixture.coverage.patient_id == patient_id
        assert fixture.requirements.plan_id == fixture.coverage.plan_id
        assert fixture.patient.is_synthetic is True

        # Verify documents map to patient_id
        for doc_ref, doc in fixture.documents.items():
            assert doc.document_reference == doc_ref
            assert doc.metadata.patient_id == patient_id

    def test_case_1_success_e2e_cross_system_readiness(self) -> None:
        """Case 1 (Sarah Jenkins): All required data and docs exist, yielding approval."""
        ehr = SyntheticEhrSimulator()
        payer = SyntheticPayerSimulator()
        doc_store = SyntheticDocumentStoreSimulator()
        portal = SyntheticAuthorizationPortalSimulator()

        # 1. EHR lookup
        patient = ehr.get_patient("pat_jenkins_001")
        assert patient is not None
        assert patient.conservative_therapy_completed is True
        assert patient.conservative_therapy_duration_weeks >= 6

        # 2. Payer coverage & requirements lookup
        coverage = payer.get_coverage("pat_jenkins_001", "plan_bcbs_001")
        assert coverage is not None and coverage.is_active is True

        reqs = payer.get_requirements("plan_bcbs_001", "MRI_LUMBAR_SPINE")
        assert reqs is not None

        # 3. Document store retrieval for all required doc types
        gathered_doc_refs: list[str] = []
        for doc_type in reqs.required_document_types:
            for doc_ref in ["doc_ref_jenkins_001", "doc_ref_jenkins_002"]:
                meta = doc_store.get_document_metadata(doc_ref)
                if meta and meta.document_type == doc_type:
                    gathered_doc_refs.append(doc_ref)
                    break
        assert len(gathered_doc_refs) == len(reqs.required_document_types)

        # 4. Portal submission & authoritative determination
        payload = PortalSubmissionPayload(
            patient_id=patient.patient_id,
            plan_id=coverage.plan_id,
            procedure_type=reqs.procedure_type,
            clinical_indication=patient.clinical_notes_summary,
            document_references=gathered_doc_refs,
            requesting_physician="dr_alvarez",
        )
        ack = portal.submit(payload)
        assert ack.success is True
        assert ack.submission_reference is not None

        status = portal.get_status(ack.submission_reference)
        assert status is not None
        assert status.portal_status == "APPROVED"

        # 5. Independent verification confirms outcome
        ver = portal.verify_outcome_independently(ack.submission_reference, "APPROVED")
        assert ver.verified is True

    def test_case_2_missing_document_exposure(self) -> None:
        """Case 2 (Robert Martinez): Document store lacks required PT note."""
        doc_store = SyntheticDocumentStoreSimulator()
        payer = SyntheticPayerSimulator()

        reqs = payer.get_requirements("plan_aetna_002", "MRI_KNEE")
        assert reqs is not None
        assert "conservative_therapy_notes" in reqs.required_document_types

        # PT note is not present for Martinez
        assert doc_store.get_document_metadata("doc_ref_martinez_pt") is None

    def test_case_3_conflicting_info_detection(self) -> None:
        """Case 3 (Elena Rostova): Detects mismatch between EHR and policy."""
        ehr = SyntheticEhrSimulator()
        payer = SyntheticPayerSimulator()

        patient = ehr.get_patient("pat_rostova_003")
        coverage = payer.get_coverage("pat_rostova_003", "plan_cigna_003")
        assert patient is not None and coverage is not None
        assert "mismatch flagged" in coverage.coverage_notes.lower()

    def test_case_4_denial_exposure(self) -> None:
        """Case 4 (David Kim): Duration only 1 week vs minimum 6 weeks required."""
        ehr = SyntheticEhrSimulator()
        payer = SyntheticPayerSimulator()
        portal = SyntheticAuthorizationPortalSimulator()

        patient = ehr.get_patient("pat_kim_004")
        reqs = payer.get_requirements("plan_united_004", "MRI_LUMBAR_SPINE")
        assert patient is not None and reqs is not None
        assert (
            patient.conservative_therapy_duration_weeks
            < reqs.minimum_conservative_therapy_weeks
        )

        # Portal submission reflects denial
        payload = PortalSubmissionPayload(
            patient_id="pat_kim_004",
            plan_id="plan_united_004",
            procedure_type="MRI_LUMBAR_SPINE",
            clinical_indication=patient.clinical_notes_summary,
            document_references=[],
            requesting_physician="dr_pcp",
        )
        ack = portal.submit(payload)
        assert ack.submission_reference is not None
        status = portal.get_status(ack.submission_reference)
        assert status is not None
        assert status.portal_status == "DENIED"

    def test_case_5_service_unavailable_exposure(self) -> None:
        """Case 5 (Marcus Vance): Transient outage handled cleanly."""
        ehr = SyntheticEhrSimulator()
        portal = SyntheticAuthorizationPortalSimulator()

        # Marcus Vance is flagged with transient failure in fixture
        assert ehr.get_patient("pat_vance_005") is None

        payload = PortalSubmissionPayload(
            patient_id="pat_vance_005",
            plan_id="plan_humana_005",
            procedure_type="MRI_SHOULDER",
            clinical_indication="Shoulder pain",
            document_references=[],
            requesting_physician="dr_ortho",
        )
        ack = portal.submit(payload)
        assert ack.success is False
        assert ack.ack_status == "SUBMISSION_REJECTED"
