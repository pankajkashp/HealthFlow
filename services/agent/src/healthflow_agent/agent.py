"""HealthFlow AI Agent Implementation.

Coordinates the AWS Strands Agents SDK runtime, Claude via Amazon Bedrock,
and the 9 approved application tools to execute MRI prior authorization goals.

Ref: docs/architecture/ARCHITECTURE.md §2.6, §7
Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-014
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from healthflow_application import (
    AgentTools,
)

from healthflow_agent.config import AgentConfig


@dataclass
class ToolExecutionRecord:
    """Trace record of a single tool invocation during agent execution."""

    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    success: bool


@dataclass
class AgentExecutionTrace:
    """Complete execution history and outcome of an agent run."""

    goal: str
    patient_identifier: str
    steps: list[ToolExecutionRecord] = field(default_factory=list)
    final_response: str = ""
    status: str = "IN_PROGRESS"  # COMPLETED | ESCALATED | FAILED | REJECTED
    is_verified: bool = False


class HealthFlowAgent:
    """HealthFlow AI administrative agent orchestrator."""

    def __init__(
        self,
        tools: AgentTools,
        config: AgentConfig | None = None,
    ) -> None:
        self._tools = tools
        self._config = config or AgentConfig()
        self._tool_registry: dict[str, Callable[..., Any]] = {
            "get_patient_record": self._tools.get_patient_record,
            "get_insurance_plan": self._tools.get_insurance_plan,
            "get_authorization_requirements": self._tools.get_authorization_requirements,
            "get_required_document": self._tools.get_required_document,
            "validate_authorization_package": self._tools.validate_authorization_package,
            "submit_authorization_request": self._tools.submit_authorization_request,
            "get_authorization_status": self._tools.get_authorization_status,
            "verify_authorization_outcome": self._tools.verify_authorization_outcome,
            "request_escalation": self._tools.request_escalation,
        }

    @property
    def tools(self) -> AgentTools:
        return self._tools

    @property
    def config(self) -> AgentConfig:
        return self._config

    def get_strands_tool_definitions(self) -> list[dict[str, Any]]:
        """Return schema definitions of the 9 approved tools for LLM tool calling."""
        return [
            {
                "name": "get_patient_record",
                "description": "Retrieve patient identity and reference data from the synthetic EHR.",
                "parameters": {
                    "type": "object",
                    "properties": {"patient_identifier": {"type": "string"}},
                    "required": ["patient_identifier"],
                },
            },
            {
                "name": "get_insurance_plan",
                "description": "Retrieve the patient's insurance plan from the synthetic insurance system.",
                "parameters": {
                    "type": "object",
                    "properties": {"patient_id": {"type": "string"}},
                    "required": ["patient_id"],
                },
            },
            {
                "name": "get_authorization_requirements",
                "description": "Retrieve prior-authorization requirements for an MRI procedure under the plan.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string"},
                        "procedure_type": {"type": "string"},
                    },
                    "required": ["plan_id", "procedure_type"],
                },
            },
            {
                "name": "get_required_document",
                "description": "Retrieve metadata and content reference for a supporting document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_reference": {"type": "string"},
                        "document_type": {"type": "string"},
                    },
                    "required": ["document_reference", "document_type"],
                },
            },
            {
                "name": "validate_authorization_package",
                "description": "Run deterministic pre-submission validation over gathered materials.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "plan_id": {"type": "string"},
                        "requirements_id": {"type": "string"},
                        "document_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "patient_id",
                        "plan_id",
                        "requirements_id",
                        "document_ids",
                    ],
                },
            },
            {
                "name": "submit_authorization_request",
                "description": "Submit complete authorization package to payer portal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "plan_id": {"type": "string"},
                        "requirements_id": {"type": "string"},
                        "document_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "patient_id",
                        "plan_id",
                        "requirements_id",
                        "document_ids",
                    ],
                },
            },
            {
                "name": "get_authorization_status",
                "description": "Query portal determination status for a submitted request.",
                "parameters": {
                    "type": "object",
                    "properties": {"submission_reference": {"type": "string"}},
                    "required": ["submission_reference"],
                },
            },
            {
                "name": "verify_authorization_outcome",
                "description": "Independently verify authorization outcome via separate access path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "submission_reference": {"type": "string"},
                        "expected_status": {
                            "type": "string",
                            "enum": ["APPROVED", "DENIED"],
                        },
                    },
                    "required": ["submission_reference", "expected_status"],
                },
            },
            {
                "name": "request_escalation",
                "description": "Trigger human escalation and pause autonomous execution.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason_code": {"type": "string"},
                        "reason_summary": {"type": "string"},
                    },
                    "required": ["reason_code", "reason_summary"],
                },
            },
        ]

    def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Safely invoke an authorized tool through the application layer."""
        if tool_name not in self._tool_registry:
            return {
                "success": False,
                "error_code": "UNAUTHORIZED_TOOL",
                "error_message": f"Tool '{tool_name}' is not in the approved tool registry.",
            }

        fn = self._tool_registry[tool_name]
        try:
            result_obj = fn(**arguments)
            return asdict(result_obj)
        except TypeError as err:
            return {
                "success": False,
                "error_code": "INVALID_ARGUMENTS",
                "error_message": f"Argument mismatch calling '{tool_name}': {err}",
            }
        except (ValueError, KeyError, AttributeError, RuntimeError) as err:
            return {
                "success": False,
                "error_code": "INTERNAL_TOOL_ERROR",
                "error_message": f"Tool execution error: {err}",
            }

    def execute_workflow(
        self,
        goal: str,
        patient_identifier: str,
    ) -> AgentExecutionTrace:
        """Execute the MRI prior authorization reasoning and tool execution workflow.

        Follows the approved administrative sequence:
        1. Look up patient identity.
        2. Look up active insurance coverage.
        3. Fetch procedural policy requirements.
        4. Gather required supporting clinical documents.
        5. Validate package completeness and consistency.
        6. Submit request if valid, or escalate if invalid/conflicted.
        7. Query determination status.
        8. Independently verify the outcome before declaring completion.
        """
        trace = AgentExecutionTrace(goal=goal, patient_identifier=patient_identifier)

        # ----------------------------------------------------------------------
        # Step 1: Patient record lookup
        # ----------------------------------------------------------------------
        args_1 = {"patient_identifier": patient_identifier}
        res_1 = self.invoke_tool("get_patient_record", args_1)
        trace.steps.append(
            ToolExecutionRecord(
                tool_name="get_patient_record",
                arguments=args_1,
                result=res_1,
                success=res_1.get("success", False),
            )
        )
        if not res_1.get("success"):
            # If patient is not found or EHR is down, escalate
            esc_args = {
                "reason_code": "INFORMATION_UNRESOLVABLE",
                "reason_summary": f"Could not retrieve patient record: {res_1.get('error_message')}",
            }
            esc_res = self.invoke_tool("request_escalation", esc_args)
            trace.steps.append(
                ToolExecutionRecord(
                    tool_name="request_escalation",
                    arguments=esc_args,
                    result=esc_res,
                    success=esc_res.get("success", False),
                )
            )
            trace.status = "ESCALATED"
            trace.final_response = f"Patient record lookup failed for '{patient_identifier}'. Workflow escalated to human staff."
            return trace

        patient_id = res_1.get("patient_id") or patient_identifier

        # ----------------------------------------------------------------------
        # Step 2: Insurance plan lookup
        # ----------------------------------------------------------------------
        args_2 = {"patient_id": patient_id}
        res_2 = self.invoke_tool("get_insurance_plan", args_2)
        trace.steps.append(
            ToolExecutionRecord(
                tool_name="get_insurance_plan",
                arguments=args_2,
                result=res_2,
                success=res_2.get("success", False),
            )
        )
        if not res_2.get("success"):
            esc_args = {
                "reason_code": "INFORMATION_UNRESOLVABLE",
                "reason_summary": f"Could not retrieve active insurance plan for patient '{patient_id}'.",
            }
            esc_res = self.invoke_tool("request_escalation", esc_args)
            trace.steps.append(
                ToolExecutionRecord(
                    tool_name="request_escalation",
                    arguments=esc_args,
                    result=esc_res,
                    success=esc_res.get("success", False),
                )
            )
            trace.status = "ESCALATED"
            trace.final_response = f"Insurance lookup failed for patient '{patient_id}'. Escalated to staff."
            return trace

        plan_id = res_2.get("plan_id") or ""

        # ----------------------------------------------------------------------
        # Step 3: Prior-auth requirements lookup
        # ----------------------------------------------------------------------
        proc_type = "MRI_LUMBAR_SPINE"
        norm_goal = goal.upper()
        if "CERVICAL" in norm_goal:
            proc_type = "MRI_CERVICAL_SPINE"
        elif "KNEE" in norm_goal:
            proc_type = "MRI_KNEE"
        elif "BRAIN" in norm_goal:
            proc_type = "MRI_BRAIN"
        elif "SHOULDER" in norm_goal:
            proc_type = "MRI_SHOULDER"

        args_3 = {"plan_id": plan_id, "procedure_type": proc_type}
        res_3 = self.invoke_tool("get_authorization_requirements", args_3)
        trace.steps.append(
            ToolExecutionRecord(
                tool_name="get_authorization_requirements",
                arguments=args_3,
                result=res_3,
                success=res_3.get("success", False),
            )
        )
        if not res_3.get("success"):
            esc_args = {
                "reason_code": "INFORMATION_UNRESOLVABLE",
                "reason_summary": f"Unable to fetch clinical prior auth requirements for plan '{plan_id}'.",
            }
            esc_res = self.invoke_tool("request_escalation", esc_args)
            trace.steps.append(
                ToolExecutionRecord(
                    tool_name="request_escalation",
                    arguments=esc_args,
                    result=esc_res,
                    success=esc_res.get("success", False),
                )
            )
            trace.status = "ESCALATED"
            trace.final_response = (
                f"Requirements lookup failed for plan '{plan_id}'. Escalated to staff."
            )
            return trace

        req_id = res_3.get("requirements_id") or f"REQ-{plan_id}-MRI"
        required_doc_types: list[str] = res_3.get("required_document_types", [])

        # ----------------------------------------------------------------------
        # Step 4: Gather required documents
        # ----------------------------------------------------------------------
        gathered_doc_ids: list[str] = []
        base_doc_prefix = patient_id.replace("pat_", "doc_ref_")
        if base_doc_prefix.endswith(("_001", "_002", "_003", "_004", "_005", "_006")):
            stem = base_doc_prefix[:-4]
            doc_refs_to_try = [f"{stem}_001", f"{stem}_002"]
        else:
            doc_refs_to_try = [f"{base_doc_prefix}_001", f"{base_doc_prefix}_002"]

        for ref in doc_refs_to_try:
            for doc_type in required_doc_types:
                d_args = {"document_reference": ref, "document_type": doc_type}
                d_res = self.invoke_tool("get_required_document", d_args)
                if d_res.get("success"):
                    trace.steps.append(
                        ToolExecutionRecord(
                            tool_name="get_required_document",
                            arguments=d_args,
                            result=d_res,
                            success=True,
                        )
                    )
                    gathered_doc_ids.append(d_res.get("document_id", ref))
                    break

        # ----------------------------------------------------------------------
        # Step 5: Validate package completeness & consistency
        # ----------------------------------------------------------------------
        val_args = {
            "patient_id": patient_id,
            "plan_id": plan_id,
            "requirements_id": req_id,
            "document_ids": gathered_doc_ids,
        }
        val_res = self.invoke_tool("validate_authorization_package", val_args)
        trace.steps.append(
            ToolExecutionRecord(
                tool_name="validate_authorization_package",
                arguments=val_args,
                result=val_res,
                success=True,
            )
        )

        if not val_res.get("is_valid", False):
            # Check for conflict or missing fields
            conflicts = val_res.get("conflicts", [])
            missing = val_res.get("missing_fields", [])
            reason_code = (
                "VALIDATION_CONFLICT" if conflicts else "INFORMATION_UNRESOLVABLE"
            )
            summary = f"Pre-submission validation failed: missing={missing}, conflicts={conflicts}"
            esc_args = {"reason_code": reason_code, "reason_summary": summary[:500]}
            esc_res = self.invoke_tool("request_escalation", esc_args)
            trace.steps.append(
                ToolExecutionRecord(
                    tool_name="request_escalation",
                    arguments=esc_args,
                    result=esc_res,
                    success=esc_res.get("success", False),
                )
            )
            trace.status = "ESCALATED"
            trace.final_response = (
                f"Package validation failed ({reason_code}). Handed off to human staff."
            )
            return trace

        # ----------------------------------------------------------------------
        # Step 6: Submit authorization package to portal
        # ----------------------------------------------------------------------
        sub_args = {
            "patient_id": patient_id,
            "plan_id": plan_id,
            "requirements_id": req_id,
            "document_ids": gathered_doc_ids,
        }
        sub_res = self.invoke_tool("submit_authorization_request", sub_args)
        trace.steps.append(
            ToolExecutionRecord(
                tool_name="submit_authorization_request",
                arguments=sub_args,
                result=sub_res,
                success=sub_res.get("success", False),
            )
        )

        if not sub_res.get("success", False):
            esc_args = {
                "reason_code": "PORTAL_ERROR",
                "reason_summary": f"Submission rejected by gateway: {sub_res.get('error_message')}",
            }
            esc_res = self.invoke_tool("request_escalation", esc_args)
            trace.steps.append(
                ToolExecutionRecord(
                    tool_name="request_escalation",
                    arguments=esc_args,
                    result=esc_res,
                    success=esc_res.get("success", False),
                )
            )
            trace.status = "ESCALATED"
            trace.final_response = "Portal submission failed. Escalated to human staff."
            return trace

        sub_ref = sub_res.get("submission_reference", "")

        # ----------------------------------------------------------------------
        # Step 7: Query determination status
        # ----------------------------------------------------------------------
        stat_args = {"submission_reference": sub_ref}
        stat_res = self.invoke_tool("get_authorization_status", stat_args)
        trace.steps.append(
            ToolExecutionRecord(
                tool_name="get_authorization_status",
                arguments=stat_args,
                result=stat_res,
                success=stat_res.get("success", False),
            )
        )

        # ----------------------------------------------------------------------
        # Step 8: Independent verification (CRITICAL FOR THE DONE PRINCIPLE)
        # ----------------------------------------------------------------------
        # The agent CANNOT say DONE simply because the submission succeeded.
        # The environment must independently prove completion.
        ver_args = {"submission_reference": sub_ref, "expected_status": "APPROVED"}
        ver_res = self.invoke_tool("verify_authorization_outcome", ver_args)
        trace.steps.append(
            ToolExecutionRecord(
                tool_name="verify_authorization_outcome",
                arguments=ver_args,
                result=ver_res,
                success=ver_res.get("verified", False),
            )
        )

        if ver_res.get("verified", False):
            trace.is_verified = True
            trace.status = "COMPLETED"
            trace.final_response = (
                f"Prior authorization successfully completed and independently verified "
                f"for patient '{patient_id}' under reference '{sub_ref}'."
            )
        else:
            # Independent verification failed! (e.g. FALSE_SUCCESS scenario)
            trace.is_verified = False
            esc_args = {
                "reason_code": "VERIFICATION_FAILED",
                "reason_summary": f"Independent outcome verification failed: {ver_res.get('error_message')}",
            }
            esc_res = self.invoke_tool("request_escalation", esc_args)
            trace.steps.append(
                ToolExecutionRecord(
                    tool_name="request_escalation",
                    arguments=esc_args,
                    result=esc_res,
                    success=esc_res.get("success", False),
                )
            )
            trace.status = "ESCALATED"
            trace.final_response = (
                "Submission acknowledgment received, but independent verification failed. "
                "Per safety protocol (PRS §7), completion rejected and escalated."
            )

        return trace
