"""Deterministic mapping from a completed tool call to a workflow-state transition.

Shared by both agent execution paths: LlmDrivenWorkflowRunner applies this live, tool call by tool
call, as the real LLM works; the API's orchestration layer applies it as a post-hoc replay over a
completed HealthFlowAgent.execute_workflow trace (the scripted/offline path, kept unmodified — see
decision 2 in docs/phases/PHASE_06_WALKTHROUGH.md). Either way, this — not the LLM, not the script —
is what decides whether a resulting state transition is legal, using the exact domain transition
graph (packages/domain, unmodified).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from healthflow_domain import VerificationStatus, WorkflowState
from healthflow_domain.workflow_state import ALLOWED_TRANSITIONS

from healthflow_agent.agent import ToolExecutionRecord

# (to_state, verification_status_for_this_hop, reason)
TransitionSink = Callable[[WorkflowState, "VerificationStatus | None", str], None]


@dataclass
class _TargetState:
    state: WorkflowState
    verification_status: VerificationStatus | None = None
    reason: str = ""


def find_transition_path(
    start: WorkflowState, target: WorkflowState
) -> list[WorkflowState]:
    """Shortest sequence of legal single-hop transitions from start to target (exclusive of start)."""
    if start == target:
        return []
    queue: deque[list[WorkflowState]] = deque([[start]])
    seen = {start}
    while queue:
        path = queue.popleft()
        for nxt in ALLOWED_TRANSITIONS.get(path[-1], frozenset()):
            if nxt in seen:
                continue
            if nxt == target:
                return [*path[1:], nxt]
            # ESCALATED is reachable from nearly every state, which makes it a false "shortcut" for
            # BFS toward any other target (e.g. GATHERING_INFORMATION -> ESCALATED ->
            # PREPARING_SUBMISSION is graph-legal but semantically wrong). Only ever traverse
            # ESCALATED when it is itself the target, never as a pass-through.
            if nxt == WorkflowState.ESCALATED:
                continue
            seen.add(nxt)
            queue.append([*path, nxt])
    raise ValueError(f"No legal transition path from {start.value} to {target.value}.")


def target_for_tool_result(
    tool_name: str, result: dict[str, Any]
) -> _TargetState | None:
    """Map a completed tool call to the deterministic workflow-state progression it implies.

    Returns None when the tool call doesn't itself imply a state change.
    """
    if tool_name == "get_patient_record" and result.get("success"):
        return _TargetState(
            WorkflowState.GATHERING_INFORMATION, reason="Patient record retrieved."
        )

    if tool_name == "validate_authorization_package" and result.get("is_valid"):
        return _TargetState(
            WorkflowState.PREPARING_SUBMISSION,
            reason="Authorization package validated.",
        )

    if tool_name == "submit_authorization_request" and result.get("success"):
        return _TargetState(
            WorkflowState.MONITORING,
            reason=f"Submitted, reference={result.get('submission_reference')}.",
        )

    if tool_name == "get_authorization_status" and result.get("success"):
        return _TargetState(WorkflowState.VERIFYING, reason="Portal status retrieved.")

    if tool_name == "verify_authorization_outcome":
        actual_status = result.get("actual_status")
        if result.get("verified") and actual_status == "APPROVED":
            return _TargetState(
                WorkflowState.COMPLETED,
                verification_status=VerificationStatus.CONFIRMED,
                reason="Independently verified APPROVED.",
            )
        if result.get("verified") and actual_status == "DENIED":
            return _TargetState(
                WorkflowState.DENIED,
                verification_status=VerificationStatus.CONFIRMED,
                reason="Independently verified DENIED.",
            )
        return _TargetState(
            WorkflowState.ESCALATED,
            verification_status=VerificationStatus.NOT_CONFIRMED,
            reason=f"Independent verification did not confirm expected outcome: "
            f"{result.get('error_message', 'mismatch detected.')}",
        )

    if tool_name == "request_escalation" and result.get("success"):
        return _TargetState(
            WorkflowState.ESCALATED,
            reason=result.get("error_message") or "Agent requested human escalation.",
        )

    return None


class WorkflowStateSync:
    """Tracks a case's persisted workflow state and walks it forward as tool calls complete."""

    def __init__(
        self,
        current_state: WorkflowState = WorkflowState.INITIATED,
        on_transition: TransitionSink | None = None,
    ) -> None:
        self.current_state = current_state
        self._on_transition = on_transition

    def apply(self, tool_name: str, result: dict[str, Any]) -> None:
        """Advance (and persist, via on_transition) the state implied by one completed tool call."""
        target = target_for_tool_result(tool_name, result)
        if target is None:
            return
        try:
            path = find_transition_path(self.current_state, target.state)
        except ValueError:
            return
        for hop in path:
            is_final_hop = hop == path[-1]
            if self._on_transition is not None:
                self._on_transition(
                    hop,
                    target.verification_status if is_final_hop else None,
                    target.reason
                    if is_final_hop
                    else f"Progressing toward {target.state.value}.",
                )
            self.current_state = hop

    def force_escalate(self, reason: str) -> None:
        """Safety net: force the case to ESCALATED if a run ends without reaching a clear outcome."""
        try:
            path = find_transition_path(self.current_state, WorkflowState.ESCALATED)
        except ValueError:
            return
        for hop in path:
            if self._on_transition is not None:
                self._on_transition(hop, None, reason)
            self.current_state = hop

    def replay(self, steps: Iterable[ToolExecutionRecord]) -> WorkflowState:
        """Apply a completed trace's steps in order (the scripted/offline post-hoc path)."""
        for step in steps:
            self.apply(step.tool_name, step.result)
        return self.current_state
