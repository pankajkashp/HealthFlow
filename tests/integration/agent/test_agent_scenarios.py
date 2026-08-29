"""Integration tests for HealthFlow Agent across all 6 Benchmark Scenarios.

Verifies end-to-end agent reasoning and tool usage against the Phase 3
simulated healthcare systems, with special focus on the FALSE_SUCCESS boundary
and the DONE principle (PRS §7).

Ref: docs/architecture/ARCHITECTURE.md §2.6, §7, §13
Ref: docs/product/PRODUCT_REQUIREMENTS.md §6, §7, §12
"""

from healthflow_agent import AgentConfig, HealthFlowAgent
from healthflow_application import AgentTools
from healthflow_infrastructure.simulators import (
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


def _build_agent_with_simulators() -> tuple[
    HealthFlowAgent, SyntheticAuthorizationPortalSimulator
]:
    ehr = SyntheticEhrSimulator()
    payer = SyntheticPayerSimulator()
    docs = SyntheticDocumentStoreSimulator()
    portal = SyntheticAuthorizationPortalSimulator()

    tools = AgentTools(
        ehr_port=SyntheticEhrAdapter(ehr),
        payer_port=SyntheticPayerAdapter(payer),
        document_store_port=SyntheticDocumentStoreAdapter(docs),
        gateway_port=SyntheticAuthorizationGatewayAdapter(portal),
        status_gateway_port=SyntheticAuthorizationStatusAdapter(portal),
        verification_port=SyntheticVerificationAdapter(portal),
    )
    agent = HealthFlowAgent(tools=tools, config=AgentConfig())
    return agent, portal


class TestAgentBenchmarkScenarios:
    def test_scenario_1_success_e2e_verified(self) -> None:
        """Case 1 (Sarah Jenkins): Standard happy path for MRI Lumbar Spine.

        Agent gathers patient, coverage, requirements, documents, validates,
        submits, queries status, and independently verifies outcome -> COMPLETED.
        """
        agent, _ = _build_agent_with_simulators()
        trace = agent.execute_workflow(
            goal="Obtain prior authorization for MRI Lumbar Spine",
            patient_identifier="pat_jenkins_001",
        )

        assert trace.status == "COMPLETED"
        assert trace.is_verified is True
        assert "independently verified" in trace.final_response

        # Check tool execution trace sequence
        tool_names = [step.tool_name for step in trace.steps]
        assert "get_patient_record" in tool_names
        assert "get_insurance_plan" in tool_names
        assert "get_authorization_requirements" in tool_names
        assert "get_required_document" in tool_names
        assert "validate_authorization_package" in tool_names
        assert "submit_authorization_request" in tool_names
        assert "get_authorization_status" in tool_names
        assert "verify_authorization_outcome" in tool_names

    def test_scenario_2_missing_document_escalated(self) -> None:
        """Case 2 (Robert Martinez): Missing physical therapy note.

        Package validation fails and agent escalates to human reviewer.
        """
        agent, _ = _build_agent_with_simulators()
        trace = agent.execute_workflow(
            goal="Obtain prior authorization for MRI Knee",
            patient_identifier="pat_martinez_002",
        )

        assert trace.status == "ESCALATED"
        assert trace.is_verified is False
        tool_names = [step.tool_name for step in trace.steps]
        assert "request_escalation" in tool_names
        # Never submitted invalid package
        assert "submit_authorization_request" not in tool_names

    def test_scenario_3_conflicting_info_escalated(self) -> None:
        """Case 3 (Elena Rostova): Conflicting clinical notes and member profile.

        Package validation detects conflict and triggers escalation.
        """
        agent, _ = _build_agent_with_simulators()
        trace = agent.execute_workflow(
            goal="Obtain prior authorization for MRI Brain",
            patient_identifier="pat_rostova_003",
        )

        assert trace.status == "ESCALATED"
        assert trace.is_verified is False
        tool_names = [step.tool_name for step in trace.steps]
        assert "request_escalation" in tool_names
        assert "submit_authorization_request" not in tool_names

    def test_scenario_4_payer_denial(self) -> None:
        """Case 4 (David Kim): Insufficient conservative therapy.

        Portal determination returns DENIED; agent status is REJECTED.
        """
        agent, _ = _build_agent_with_simulators()
        trace = agent.execute_workflow(
            goal="Obtain prior authorization for MRI Lumbar Spine",
            patient_identifier="pat_kim_004",
        )

        # In case 4, conservative therapy duration is 1 week (vs required 6 weeks)
        # Validation or portal adjudication rejects
        assert trace.status in {"REJECTED", "ESCALATED"}
        assert trace.is_verified is False

    def test_scenario_5_service_unavailable_escalated(self) -> None:
        """Case 5 (Marcus Vance): System downtime.

        Agent handles unavailability without crashing and escalates.
        """
        agent, _ = _build_agent_with_simulators()
        trace = agent.execute_workflow(
            goal="Obtain prior authorization for MRI Shoulder",
            patient_identifier="pat_vance_005",
        )

        assert trace.status == "ESCALATED"
        assert trace.is_verified is False

    def test_scenario_6_false_success_intercepted_by_done_principle(self) -> None:
        """Case 6 (Olivia Chen): Critical FALSE_SUCCESS test.

        Gateway responds with ACK ("RECEIVED"), but authoritative external state is DENIED.
        The agent performs independent verification, detects the failure, and REFUSES
        to claim completion. It transitions to ESCALATED with VERIFICATION_FAILED.
        """
        agent, _ = _build_agent_with_simulators()
        trace = agent.execute_workflow(
            goal="Obtain prior authorization for MRI Cervical Spine",
            patient_identifier="pat_chen_006",
        )

        # The agent must NOT claim COMPLETED!
        assert trace.status == "ESCALATED"
        assert trace.is_verified is False
        assert "independent verification failed" in trace.final_response

        # Verify that verify_authorization_outcome was executed and failed
        ver_steps = [
            s for s in trace.steps if s.tool_name == "verify_authorization_outcome"
        ]
        assert len(ver_steps) == 1
        assert ver_steps[0].result["verified"] is False
        assert ver_steps[0].result["actual_status"] == "DENIED"

        # Verify that escalation was requested with VERIFICATION_FAILED
        esc_steps = [s for s in trace.steps if s.tool_name == "request_escalation"]
        assert len(esc_steps) == 1
        assert esc_steps[0].arguments["reason_code"] == "VERIFICATION_FAILED"
