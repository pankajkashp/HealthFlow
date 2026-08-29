"""Deterministic Permission & Action Authorization Engine.

Enforces least-privilege action authorization based on workflow state and actor role.
The LLM cannot grant itself permissions; a model statement like "I am authorized"
has zero effect. Permission decisions are strictly determined by this engine.

Ref: docs/architecture/ARCHITECTURE.md §8.1, §8.2
Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-011, AD-013
Ref: docs/product/PRODUCT_REQUIREMENTS.md §11, §21
"""

from typing import Final

from healthflow_domain.enums import WorkflowState

from healthflow_safety.models import PermissionCheckResult, UserRole

# Terminal states where no further workflow actions are permitted
TERMINAL_STATES: Final[set[WorkflowState]] = {
    WorkflowState.COMPLETED,
    WorkflowState.DENIED,
    WorkflowState.FAILED,
}

# Permitted states per tool action
ACTION_STATE_PERMISSIONS: Final[dict[str, set[WorkflowState]]] = {
    "get_patient_record": {
        WorkflowState.INITIATED,
        WorkflowState.GATHERING_INFORMATION,
        WorkflowState.VALIDATING,
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.FOLLOW_UP_REQUIRED,
        WorkflowState.ESCALATED,
    },
    "get_insurance_plan": {
        WorkflowState.INITIATED,
        WorkflowState.GATHERING_INFORMATION,
        WorkflowState.VALIDATING,
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.FOLLOW_UP_REQUIRED,
        WorkflowState.ESCALATED,
    },
    "get_authorization_requirements": {
        WorkflowState.GATHERING_INFORMATION,
        WorkflowState.VALIDATING,
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.FOLLOW_UP_REQUIRED,
        WorkflowState.ESCALATED,
    },
    "get_required_document": {
        WorkflowState.GATHERING_INFORMATION,
        WorkflowState.VALIDATING,
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.FOLLOW_UP_REQUIRED,
        WorkflowState.ESCALATED,
    },
    "validate_authorization_package": {
        WorkflowState.GATHERING_INFORMATION,
        WorkflowState.VALIDATING,
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.FOLLOW_UP_REQUIRED,
        WorkflowState.ESCALATED,
    },
    # Crucial safety invariant: submit_authorization_request can ONLY be executed in PREPARING_SUBMISSION
    "submit_authorization_request": {
        WorkflowState.PREPARING_SUBMISSION,
    },
    "get_authorization_status": {
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.SUBMITTED,
        WorkflowState.MONITORING,
        WorkflowState.FOLLOW_UP_REQUIRED,
        WorkflowState.VERIFYING,
        WorkflowState.ESCALATED,
    },
    "verify_authorization_outcome": {
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.MONITORING,
        WorkflowState.VERIFYING,
        WorkflowState.ESCALATED,
    },
    "request_escalation": {
        WorkflowState.INITIATED,
        WorkflowState.GATHERING_INFORMATION,
        WorkflowState.VALIDATING,
        WorkflowState.PREPARING_SUBMISSION,
        WorkflowState.SUBMITTED,
        WorkflowState.MONITORING,
        WorkflowState.FOLLOW_UP_REQUIRED,
        WorkflowState.VERIFYING,
        WorkflowState.ESCALATED,
    },
}


def check_action_permission(
    action: str,
    current_state: WorkflowState | str,
    actor_role: UserRole | str = UserRole.AGENT,
) -> PermissionCheckResult:
    """Evaluate whether the given action is authorized in the current workflow state."""
    state_enum: WorkflowState
    if isinstance(current_state, WorkflowState):
        state_enum = current_state
    else:
        try:
            state_enum = WorkflowState(current_state)
        except ValueError:
            return PermissionCheckResult(
                allowed=False,
                action=action,
                current_state=str(current_state),
                actor_role=str(actor_role),
                denial_reason=f"Unknown workflow state '{current_state}'.",
            )

    role_str = actor_role.value if isinstance(actor_role, UserRole) else str(actor_role)

    # 1. Reject if state is terminal
    if state_enum in TERMINAL_STATES:
        return PermissionCheckResult(
            allowed=False,
            action=action,
            current_state=state_enum.value,
            actor_role=role_str,
            denial_reason=f"Action '{action}' prohibited in terminal state '{state_enum.value}'.",
        )

    # 2. Check if action is known
    if action not in ACTION_STATE_PERMISSIONS:
        return PermissionCheckResult(
            allowed=False,
            action=action,
            current_state=state_enum.value,
            actor_role=role_str,
            denial_reason=f"Unrecognized or unauthorized action '{action}'.",
        )

    # 3. Check if action is permitted in this specific workflow state
    permitted_states = ACTION_STATE_PERMISSIONS[action]
    if state_enum not in permitted_states:
        return PermissionCheckResult(
            allowed=False,
            action=action,
            current_state=state_enum.value,
            actor_role=role_str,
            denial_reason=(
                f"Action '{action}' is not permitted in state '{state_enum.value}'. "
                f"Permitted states: {[s.value for s in permitted_states]}."
            ),
        )

    return PermissionCheckResult(
        allowed=True,
        action=action,
        current_state=state_enum.value,
        actor_role=role_str,
    )
