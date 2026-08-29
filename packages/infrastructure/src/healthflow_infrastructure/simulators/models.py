"""Simulated Healthcare Environment Data Models & Fixtures.

Defines simulator scenarios and authoritative synthetic benchmark fixtures
representing consistent patient cases across EHR, Payer, Document Store, and Portal.

Ref: docs/architecture/ARCHITECTURE.md §13
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from healthflow_domain.external_models import (
    DocumentContent,
    DocumentMetadata,
    EhrPatientRecord,
    PayerCoverageRecord,
    ProcedureRequirements,
)


class SimulatorScenario(StrEnum):
    """Benchmark test scenarios supported by the simulated healthcare environment."""

    SUCCESS = "SUCCESS"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    CONFLICTING_INFO = "CONFLICTING_INFO"
    PAYER_DENIAL = "PAYER_DENIAL"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    FALSE_SUCCESS = "FALSE_SUCCESS"


@dataclass
class SyntheticCaseFixture:
    """A coherent synthetic patient case represented across all simulated systems."""

    case_key: str
    scenario: SimulatorScenario
    patient: EhrPatientRecord
    clinical_history: list[str]
    coverage: PayerCoverageRecord
    requirements: ProcedureRequirements
    documents: dict[str, DocumentContent]
    initial_portal_decision: str  # "APPROVED", "DENIED", "PENDING", "REJECTED"
    expected_verified_status: str  # "APPROVED", "DENIED", "NOT_FOUND"
    simulated_ack_success: bool = True
    simulated_ack_reference: str = ""
    is_transient_failure: bool = False


# ==============================================================================
# 6 Authoritative Benchmark Synthetic Cases
# ==============================================================================

# --- Case 1: Standard Success (Sarah Jenkins) ---
_DOC_JENKINS_REFERRAL = DocumentContent(
    document_reference="doc_ref_jenkins_001",
    document_type="physician_referral",
    text_content="Referral for MRI Lumbar Spine. Indications: L5-S1 radiculopathy, persistent for 10 weeks.",
    metadata=DocumentMetadata(
        document_reference="doc_ref_jenkins_001",
        document_type="physician_referral",
        patient_id="pat_jenkins_001",
        created_date="2026-08-01",
        author_reference="dr_alvarez_ortho",
        file_format="PDF",
        content_hash="hash_jenkins_ref_001",
    ),
)
_DOC_JENKINS_PT = DocumentContent(
    document_reference="doc_ref_jenkins_002",
    document_type="conservative_therapy_notes",
    text_content="Physical Therapy Completion Report: 8 weeks of supervised lumbar physical therapy completed.",
    metadata=DocumentMetadata(
        document_reference="doc_ref_jenkins_002",
        document_type="conservative_therapy_notes",
        patient_id="pat_jenkins_001",
        created_date="2026-08-15",
        author_reference="apex_physical_therapy",
        file_format="PDF",
        content_hash="hash_jenkins_pt_002",
    ),
)

FIXTURE_CASE_1_SUCCESS: Final[SyntheticCaseFixture] = SyntheticCaseFixture(
    case_key="SYN-CASE-001-SUCCESS",
    scenario=SimulatorScenario.SUCCESS,
    patient=EhrPatientRecord(
        patient_id="pat_jenkins_001",
        name_reference="Sarah Jenkins (Synthetic)",
        ehr_reference="EHR-SYN-1001",
        clinical_notes_summary="Chronic lumbar radiculopathy, pain radiating down left leg for 10 weeks.",
        active_diagnoses=[
            "M54.16 - Radiculopathy, lumbar region",
            "M51.26 - Intervertebral disc disorder",
        ],
        conservative_therapy_completed=True,
        conservative_therapy_duration_weeks=8,
        is_synthetic=True,
    ),
    clinical_history=[
        "2026-06-01: Initial encounter with primary care physician for low back pain.",
        "2026-06-15: Initiated course of physical therapy (8 weeks).",
        "2026-08-15: Completed physical therapy with refractory symptoms.",
    ],
    coverage=PayerCoverageRecord(
        plan_id="plan_bcbs_001",
        patient_id="pat_jenkins_001",
        insurer_name="Blue Cross Blue Shield (Synthetic)",
        is_active=True,
        in_network=True,
        requires_prior_authorization=True,
        coverage_notes="Prior authorization required for advanced diagnostic imaging.",
    ),
    requirements=ProcedureRequirements(
        plan_id="plan_bcbs_001",
        procedure_type="MRI_LUMBAR_SPINE",
        required_document_types=["physician_referral", "conservative_therapy_notes"],
        required_clinical_fields=[
            "radiculopathy_duration_weeks",
            "neurological_exam_findings",
        ],
        minimum_conservative_therapy_weeks=6,
        requires_specialist_referral=True,
    ),
    documents={
        "doc_ref_jenkins_001": _DOC_JENKINS_REFERRAL,
        "doc_ref_jenkins_002": _DOC_JENKINS_PT,
    },
    initial_portal_decision="APPROVED",
    expected_verified_status="APPROVED",
    simulated_ack_success=True,
    simulated_ack_reference="AUTH-ACK-JENKINS-001",
)

# --- Case 2: Missing Document (Robert Martinez) ---
_DOC_MARTINEZ_REFERRAL = DocumentContent(
    document_reference="doc_ref_martinez_001",
    document_type="physician_referral",
    text_content="Referral for MRI Right Knee. Suspected medial meniscus tear.",
    metadata=DocumentMetadata(
        document_reference="doc_ref_martinez_001",
        document_type="physician_referral",
        patient_id="pat_martinez_002",
        created_date="2026-08-10",
        author_reference="dr_patel_sports_med",
        file_format="PDF",
        content_hash="hash_martinez_ref_001",
    ),
)

FIXTURE_CASE_2_MISSING_DOC: Final[SyntheticCaseFixture] = SyntheticCaseFixture(
    case_key="SYN-CASE-002-MISSING-DOC",
    scenario=SimulatorScenario.MISSING_DOCUMENT,
    patient=EhrPatientRecord(
        patient_id="pat_martinez_002",
        name_reference="Robert Martinez (Synthetic)",
        ehr_reference="EHR-SYN-1002",
        clinical_notes_summary="Acute right knee joint pain following sports injury.",
        active_diagnoses=[
            "M23.22 - Derangement of meniscus due to old tear or injury, right knee"
        ],
        conservative_therapy_completed=False,
        conservative_therapy_duration_weeks=0,
        is_synthetic=True,
    ),
    clinical_history=["2026-08-05: Sports clinic encounter for knee swelling."],
    coverage=PayerCoverageRecord(
        plan_id="plan_aetna_002",
        patient_id="pat_martinez_002",
        insurer_name="Aetna (Synthetic)",
        is_active=True,
        in_network=True,
        requires_prior_authorization=True,
        coverage_notes="Requires physical therapy records or orthopedic consult.",
    ),
    requirements=ProcedureRequirements(
        plan_id="plan_aetna_002",
        procedure_type="MRI_KNEE",
        required_document_types=["physician_referral", "conservative_therapy_notes"],
        required_clinical_fields=["injury_mechanism", "weight_bearing_status"],
        minimum_conservative_therapy_weeks=4,
        requires_specialist_referral=True,
    ),
    documents={
        # conservative_therapy_notes is intentionally absent from document store
        "doc_ref_martinez_001": _DOC_MARTINEZ_REFERRAL,
    },
    initial_portal_decision="ADDITIONAL_INFO_REQUIRED",
    expected_verified_status="ADDITIONAL_INFO_REQUIRED",
    simulated_ack_success=True,
    simulated_ack_reference="AUTH-ACK-MARTINEZ-002",
)

# --- Case 3: Conflicting Information (Elena Rostova) ---
_DOC_ROSTOVA_REFERRAL = DocumentContent(
    document_reference="doc_ref_rostova_001",
    document_type="physician_referral",
    text_content="Referral indicates patient member ID MEM-ROSTOVA-999 and severe transient neurological deficit.",
    metadata=DocumentMetadata(
        document_reference="doc_ref_rostova_001",
        document_type="physician_referral",
        patient_id="pat_rostova_003",
        created_date="2026-08-12",
        author_reference="dr_smith_neuro",
        file_format="PDF",
        content_hash="hash_rostova_ref_001",
    ),
)

FIXTURE_CASE_3_CONFLICT: Final[SyntheticCaseFixture] = SyntheticCaseFixture(
    case_key="SYN-CASE-003-CONFLICT",
    scenario=SimulatorScenario.CONFLICTING_INFO,
    patient=EhrPatientRecord(
        patient_id="pat_rostova_003",
        name_reference="Elena Rostova (Synthetic)",
        ehr_reference="EHR-SYN-1003",
        clinical_notes_summary="Tension headaches responding to NSAIDs. Member ID in EHR: MEM-ROSTOVA-111.",
        active_diagnoses=["G44.209 - Tension-type headache, unspecified"],
        conservative_therapy_completed=True,
        conservative_therapy_duration_weeks=12,
        is_synthetic=True,
    ),
    clinical_history=["2026-07-10: Routine follow-up for chronic tension headache."],
    coverage=PayerCoverageRecord(
        plan_id="plan_cigna_003",
        patient_id="pat_rostova_003",
        insurer_name="Cigna (Synthetic)",
        is_active=True,
        in_network=True,
        requires_prior_authorization=True,
        coverage_notes="Member ID mismatch flagged between EHR and policy profile.",
    ),
    requirements=ProcedureRequirements(
        plan_id="plan_cigna_003",
        procedure_type="MRI_BRAIN",
        required_document_types=["physician_referral"],
        required_clinical_fields=["headache_frequency", "focal_neurologic_deficit"],
        minimum_conservative_therapy_weeks=0,
        requires_specialist_referral=True,
    ),
    documents={
        "doc_ref_rostova_001": _DOC_ROSTOVA_REFERRAL,
    },
    initial_portal_decision="DENIED",
    expected_verified_status="DENIED",
    simulated_ack_success=True,
    simulated_ack_reference="AUTH-ACK-ROSTOVA-003",
)

# --- Case 4: Payer Denial / Ineligible (David Kim) ---
FIXTURE_CASE_4_DENIAL: Final[SyntheticCaseFixture] = SyntheticCaseFixture(
    case_key="SYN-CASE-004-DENIAL",
    scenario=SimulatorScenario.PAYER_DENIAL,
    patient=EhrPatientRecord(
        patient_id="pat_kim_004",
        name_reference="David Kim (Synthetic)",
        ehr_reference="EHR-SYN-1004",
        clinical_notes_summary="Low back strain, symptom duration only 10 days.",
        active_diagnoses=["S39.012A - Strain of muscle of lower back"],
        conservative_therapy_completed=False,
        conservative_therapy_duration_weeks=1,
        is_synthetic=True,
    ),
    clinical_history=["2026-08-18: Acute back strain after lifting heavy object."],
    coverage=PayerCoverageRecord(
        plan_id="plan_united_004",
        patient_id="pat_kim_004",
        insurer_name="UnitedHealthcare (Synthetic)",
        is_active=True,
        in_network=True,
        requires_prior_authorization=True,
        coverage_notes="Clinical policy requires minimum 6 weeks conservative therapy prior to lumbar MRI.",
    ),
    requirements=ProcedureRequirements(
        plan_id="plan_united_004",
        procedure_type="MRI_LUMBAR_SPINE",
        required_document_types=["conservative_therapy_notes"],
        required_clinical_fields=["duration_weeks"],
        minimum_conservative_therapy_weeks=6,
        requires_specialist_referral=False,
    ),
    documents={},
    initial_portal_decision="DENIED",
    expected_verified_status="DENIED",
    simulated_ack_success=True,
    simulated_ack_reference="AUTH-ACK-KIM-004",
)

# --- Case 5: Service Unavailable (Marcus Vance) ---
FIXTURE_CASE_5_UNAVAILABLE: Final[SyntheticCaseFixture] = SyntheticCaseFixture(
    case_key="SYN-CASE-005-UNAVAILABLE",
    scenario=SimulatorScenario.SERVICE_UNAVAILABLE,
    patient=EhrPatientRecord(
        patient_id="pat_vance_005",
        name_reference="Marcus Vance (Synthetic)",
        ehr_reference="EHR-SYN-1005",
        clinical_notes_summary="Right shoulder rotator cuff impingement.",
        active_diagnoses=[
            "M75.101 - Unspecified rotator cuff tear or rupture of right shoulder"
        ],
        conservative_therapy_completed=True,
        conservative_therapy_duration_weeks=6,
        is_synthetic=True,
    ),
    clinical_history=["2026-08-01: Orthopedic visit."],
    coverage=PayerCoverageRecord(
        plan_id="plan_humana_005",
        patient_id="pat_vance_005",
        insurer_name="Humana (Synthetic)",
        is_active=True,
        in_network=True,
        requires_prior_authorization=True,
        coverage_notes="System gateway under maintenance.",
    ),
    requirements=ProcedureRequirements(
        plan_id="plan_humana_005",
        procedure_type="MRI_SHOULDER",
        required_document_types=["physician_referral"],
        required_clinical_fields=["range_of_motion"],
        minimum_conservative_therapy_weeks=4,
        requires_specialist_referral=False,
    ),
    documents={},
    initial_portal_decision="ERROR",
    expected_verified_status="ERROR",
    simulated_ack_success=False,
    simulated_ack_reference="",
    is_transient_failure=True,
)

# --- Case 6: FALSE-SUCCESS SCENARIO (Olivia Chen) ---
# CRITICAL FOR DONE PRINCIPLE:
# Portal submission endpoint returns apparent success with reference 'AUTH-ACK-CHEN-006',
# BUT the authoritative portal state database shows REJECTED (e.g. backend validation failure).
FIXTURE_CASE_6_FALSE_SUCCESS: Final[SyntheticCaseFixture] = SyntheticCaseFixture(
    case_key="SYN-CASE-006-FALSE-SUCCESS",
    scenario=SimulatorScenario.FALSE_SUCCESS,
    patient=EhrPatientRecord(
        patient_id="pat_chen_006",
        name_reference="Olivia Chen (Synthetic)",
        ehr_reference="EHR-SYN-1006",
        clinical_notes_summary="Cervical spine stenosis with radiating upper extremity numbness.",
        active_diagnoses=["M48.02 - Spinal stenosis, cervical region"],
        conservative_therapy_completed=True,
        conservative_therapy_duration_weeks=8,
        is_synthetic=True,
    ),
    clinical_history=["2026-07-20: Cervical spine evaluation."],
    coverage=PayerCoverageRecord(
        plan_id="plan_kaiser_006",
        patient_id="pat_chen_006",
        insurer_name="Kaiser Permanente (Synthetic)",
        is_active=True,
        in_network=True,
        requires_prior_authorization=True,
        coverage_notes="Portal ingest service returns OK, but backend adjudication rejects immediately.",
    ),
    requirements=ProcedureRequirements(
        plan_id="plan_kaiser_006",
        procedure_type="MRI_CERVICAL_SPINE",
        required_document_types=["physician_referral"],
        required_clinical_fields=["neurological_deficit"],
        minimum_conservative_therapy_weeks=6,
        requires_specialist_referral=True,
    ),
    documents={
        "doc_ref_chen_001": DocumentContent(
            document_reference="doc_ref_chen_001",
            document_type="physician_referral",
            text_content="Referral for cervical MRI.",
            metadata=DocumentMetadata(
                document_reference="doc_ref_chen_001",
                document_type="physician_referral",
                patient_id="pat_chen_006",
                created_date="2026-08-01",
                author_reference="dr_lee",
                file_format="PDF",
                content_hash="hash_chen_001",
            ),
        )
    },
    # Gateway returns apparent success!
    simulated_ack_success=True,
    simulated_ack_reference="AUTH-ACK-CHEN-006",
    # But authoritative portal backend holds DENIED / NOT_CONFIRMED!
    initial_portal_decision="DENIED",
    expected_verified_status="DENIED",
)

ALL_BENCHMARK_FIXTURES: Final[dict[str, SyntheticCaseFixture]] = {
    "pat_jenkins_001": FIXTURE_CASE_1_SUCCESS,
    "pat_martinez_002": FIXTURE_CASE_2_MISSING_DOC,
    "pat_rostova_003": FIXTURE_CASE_3_CONFLICT,
    "pat_kim_004": FIXTURE_CASE_4_DENIAL,
    "pat_vance_005": FIXTURE_CASE_5_UNAVAILABLE,
    "pat_chen_006": FIXTURE_CASE_6_FALSE_SUCCESS,
}
