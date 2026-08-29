"""Unit tests for HealthFlow Agent Orchestration & Tool Registry.

Verifies agent initialization, Strands tool schema exposure, safe tool invocation,
and unauthorized tool rejection.

Ref: docs/architecture/ARCHITECTURE.md §2.6, §7
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


def _create_agent() -> HealthFlowAgent:
    tools = AgentTools(
        ehr_port=SyntheticEhrAdapter(SyntheticEhrSimulator()),
        payer_port=SyntheticPayerAdapter(SyntheticPayerSimulator()),
        document_store_port=SyntheticDocumentStoreAdapter(
            SyntheticDocumentStoreSimulator()
        ),
        gateway_port=SyntheticAuthorizationGatewayAdapter(
            SyntheticAuthorizationPortalSimulator()
        ),
        status_gateway_port=SyntheticAuthorizationStatusAdapter(
            SyntheticAuthorizationPortalSimulator()
        ),
        verification_port=SyntheticVerificationAdapter(
            SyntheticAuthorizationPortalSimulator()
        ),
    )
    return HealthFlowAgent(tools=tools, config=AgentConfig(max_iterations=10))


class TestHealthFlowAgentOrchestration:
    def test_agent_initialization_and_config(self) -> None:
        agent = _create_agent()
        assert agent.config.max_iterations == 10
        assert agent.config.temperature == 0.0
        assert "claude" in agent.config.bedrock_model_id.lower()

    def test_exactly_nine_tools_registered(self) -> None:
        agent = _create_agent()
        schemas = agent.get_strands_tool_definitions()
        assert len(schemas) == 9
        tool_names = {s["name"] for s in schemas}
        expected_names = {
            "get_patient_record",
            "get_insurance_plan",
            "get_authorization_requirements",
            "get_required_document",
            "validate_authorization_package",
            "submit_authorization_request",
            "get_authorization_status",
            "verify_authorization_outcome",
            "request_escalation",
        }
        assert tool_names == expected_names

    def test_unauthorized_tool_invocation_rejected(self) -> None:
        agent = _create_agent()
        result = agent.invoke_tool(
            "execute_arbitrary_sql", {"query": "SELECT * FROM cases"}
        )
        assert result["success"] is False
        assert result["error_code"] == "UNAUTHORIZED_TOOL"

    def test_tool_invocation_argument_mismatch_handled(self) -> None:
        agent = _create_agent()
        result = agent.invoke_tool("get_patient_record", {"invalid_arg": 123})
        assert result["success"] is False
        assert result["error_code"] == "INVALID_ARGUMENTS"

    def test_safe_tool_invocation(self) -> None:
        agent = _create_agent()
        result = agent.invoke_tool(
            "get_patient_record", {"patient_identifier": "pat_jenkins_001"}
        )
        assert result["success"] is True
        assert result["patient_id"] == "pat_jenkins_001"
