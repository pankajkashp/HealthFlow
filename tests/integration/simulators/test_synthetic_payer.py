"""Integration tests for Synthetic Payer Simulator & Adapter.

Verifies coverage lookup, procedural requirements, fault injection, and PayerPort compliance.
Ref: docs/architecture/ARCHITECTURE.md §6.2, §6.3, §13
"""

from healthflow_domain import PatientId, PayerPort, PlanId, ProcedureType
from healthflow_domain.external_models import (
    PayerCoverageRecord,
)
from healthflow_infrastructure.simulators import (
    SyntheticPayerAdapter,
    SyntheticPayerSimulator,
)


class TestSyntheticPayer:
    def test_get_valid_coverage(self) -> None:
        sim = SyntheticPayerSimulator()
        coverage = sim.get_coverage("pat_jenkins_001", "plan_bcbs_001")
        assert coverage is not None
        assert coverage.is_active is True
        assert coverage.in_network is True
        assert coverage.requires_prior_authorization is True
        assert "Blue Cross" in coverage.insurer_name

    def test_get_nonexistent_coverage_returns_none(self) -> None:
        sim = SyntheticPayerSimulator()
        assert sim.get_coverage("pat_jenkins_001", "plan_nonexistent_999") is None
        assert sim.get_coverage("pat_unknown_999", "plan_bcbs_001") is None

    def test_get_prior_auth_requirements(self) -> None:
        sim = SyntheticPayerSimulator()
        reqs = sim.get_requirements("plan_bcbs_001", "MRI_LUMBAR_SPINE")
        assert reqs is not None
        assert reqs.plan_id == "plan_bcbs_001"
        assert reqs.procedure_type == "MRI_LUMBAR_SPINE"
        assert "physician_referral" in reqs.required_document_types
        assert "conservative_therapy_notes" in reqs.required_document_types
        assert reqs.minimum_conservative_therapy_weeks == 6
        assert reqs.requires_specialist_referral is True

    def test_simulated_payer_downtime(self) -> None:
        sim = SyntheticPayerSimulator()
        sim.set_availability(False)
        assert sim.get_coverage("pat_jenkins_001", "plan_bcbs_001") is None
        assert sim.get_requirements("plan_bcbs_001", "MRI_LUMBAR_SPINE") is None

        sim.set_availability(True)
        assert sim.get_coverage("pat_jenkins_001", "plan_bcbs_001") is not None

    def test_dynamic_coverage_registration(self) -> None:
        sim = SyntheticPayerSimulator()
        custom_cov = PayerCoverageRecord(
            plan_id="plan_custom_77",
            patient_id="pat_custom_77",
            insurer_name="Custom Payer",
            is_active=True,
            in_network=False,
            requires_prior_authorization=True,
            coverage_notes="Out-of-network benefits apply.",
        )
        sim.register_coverage(custom_cov)
        fetched = sim.get_coverage("pat_custom_77", "plan_custom_77")
        assert fetched is not None
        assert fetched.in_network is False

    def test_payer_adapter_implements_port(self) -> None:
        sim = SyntheticPayerSimulator()
        adapter: PayerPort = SyntheticPayerAdapter(sim)

        cov = adapter.get_coverage_status(
            PatientId("pat_jenkins_001"), PlanId("plan_bcbs_001")
        )
        assert cov is not None
        assert cov.is_active is True

        reqs = adapter.get_prior_auth_requirements(
            PlanId("plan_bcbs_001"), ProcedureType.MRI_LUMBAR_SPINE
        )
        assert reqs is not None
        assert reqs.procedure_type == "MRI_LUMBAR_SPINE"
