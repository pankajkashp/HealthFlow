"""LLM-driven workflow execution using a real Strands Agent tool-calling loop.

Unlike HealthFlowAgent.execute_workflow (a fixed deterministic script, kept unmodified for the
existing test suite and as an offline/CI-safe fallback — see AgentConfig.llm_provider), this module
lets Claude actually reason about which of the 9 approved tools to call and in what order.

The core HealthFlow principle is unchanged: the LLM decides *what to try next*; it never decides
*whether a resulting state transition is legal* or *whether the case is actually done*. Both of
those stay in deterministic code (state_sync.WorkflowStateSync, built on the unmodified domain state
machine and the unmodified verification-result contract) — this module only runs the reasoning loop
and feeds each completed tool call to that deterministic sync layer.

Ref: docs/phases/PHASE_06_WALKTHROUGH.md, decisions 1-2.
"""

from __future__ import annotations

from typing import Any

from healthflow_application import AgentTools
from healthflow_domain import WorkflowState

from healthflow_agent.agent import AgentExecutionTrace, ToolExecutionRecord
from healthflow_agent.config import AgentConfig
from healthflow_agent.model_factory import build_model
from healthflow_agent.prompts import HEALTHFLOW_SYSTEM_PROMPT
from healthflow_agent.state_sync import TransitionSink, WorkflowStateSync
from healthflow_agent.tool_adapters import build_tool_adapters


class LlmDrivenWorkflowRunner:
    """Runs the MRI prior-authorization workflow through a real Strands Agent LLM loop."""

    def __init__(
        self,
        tools: AgentTools,
        config: AgentConfig | None = None,
        current_state: WorkflowState = WorkflowState.INITIATED,
        on_transition: TransitionSink | None = None,
    ) -> None:
        self._tools = tools
        self._config = config or AgentConfig()
        self._sync = WorkflowStateSync(
            current_state=current_state, on_transition=on_transition
        )

    @property
    def current_state(self) -> WorkflowState:
        return self._sync.current_state

    def execute_workflow(
        self, goal: str, patient_identifier: str
    ) -> AgentExecutionTrace:
        """Run the LLM tool-calling loop and return the same trace shape as the scripted runner."""
        if self._config.llm_provider == "scripted":
            raise ValueError(
                "LlmDrivenWorkflowRunner requires LLM_PROVIDER to be 'anthropic' or 'bedrock'. "
                "Use HealthFlowAgent.execute_workflow for the scripted/offline path instead."
            )

        from strands import Agent

        trace = AgentExecutionTrace(goal=goal, patient_identifier=patient_identifier)

        def on_tool_call(
            name: str, args: dict[str, Any], result: dict[str, Any]
        ) -> None:
            trace.steps.append(
                ToolExecutionRecord(
                    tool_name=name,
                    arguments=args,
                    result=result,
                    success=bool(result.get("success", result.get("verified", False))),
                )
            )
            self._sync.apply(name, result)

        model = build_model(self._config)
        tool_fns = build_tool_adapters(self._tools, on_tool_call=on_tool_call)
        agent = Agent(
            model=model, tools=tool_fns, system_prompt=HEALTHFLOW_SYSTEM_PROMPT
        )

        prompt = (
            f"Goal: {goal}\n"
            f"Patient identifier: {patient_identifier}\n\n"
            "Execute this MRI prior-authorization workflow to completion using only your "
            "authorized tools, following the standard workflow pattern and safety rules in your "
            "system instructions."
        )
        result = agent(prompt)
        trace.final_response = _extract_text(result)
        self._finalize_status(trace)
        return trace

    def _finalize_status(self, trace: AgentExecutionTrace) -> None:
        for step in reversed(trace.steps):
            if step.tool_name == "verify_authorization_outcome":
                if (
                    step.result.get("verified")
                    and step.result.get("actual_status") == "APPROVED"
                ):
                    trace.is_verified = True
                    trace.status = "COMPLETED"
                else:
                    trace.status = "ESCALATED"
                return
            if step.tool_name == "request_escalation" and step.success:
                trace.status = "ESCALATED"
                return
        trace.status = "FAILED"
        # Safety net: if the LLM loop ended without escalating or verifying, force the case into
        # ESCALATED rather than leaving it silently stuck — the environment, not the LLM's silence,
        # decides the case needs a human.
        self._sync.force_escalate(
            "Agent run ended without reaching a verified or escalated outcome."
        )


def _extract_text(result: Any) -> str:
    """Best-effort extraction of the agent's final text response from a Strands AgentResult."""
    message = getattr(result, "message", None)
    if not isinstance(message, dict):
        return str(result)
    blocks = message.get("content", [])
    texts = [
        block.get("text", "")
        for block in blocks
        if isinstance(block, dict) and "text" in block
    ]
    return "\n".join(t for t in texts if t) or str(result)
