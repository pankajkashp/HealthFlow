"""HealthFlow Safety Layer.

This package implements deterministic input validation, permission checks,
pre-action safety gates, retry & failure classification, and independent verification evaluation.
Safety controls are implemented in code, NOT in LLM prompts.

Architecture position: Safety layer.
Allowed dependencies: Domain layer (packages/domain), Shared layer (packages/shared), Pydantic.
Prohibited: Safety controls must never be bypassed by any other layer.

Ref: docs/architecture/ARCHITECTURE.md §2.7, §8
Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-011, AD-012, AD-013
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §8, §10, §11, §16, §21
"""

from healthflow_safety.escalation_boundaries import (
    MANDATORY_ESCALATION_CODES,
    format_escalation_envelope,
    is_escalation_mandatory,
)
from healthflow_safety.input_validation import (
    ALLOWED_ESCALATION_REASONS,
    ALLOWED_PROCEDURE_PREFIX,
    validate_document_reference,
    validate_escalation_inputs,
    validate_patient_identifier,
    validate_plan_identifier,
    validate_procedure_type,
    validate_submission_inputs,
    validate_verification_inputs,
)
from healthflow_safety.models import (
    FailureCategory,
    InputValidationResult,
    PermissionCheckResult,
    RetryDecision,
    SafetyGateResult,
    SafetyViolation,
    UserRole,
    VerificationDecision,
)
from healthflow_safety.permissions import (
    ACTION_STATE_PERMISSIONS,
    TERMINAL_STATES,
    check_action_permission,
)
from healthflow_safety.retry_policy import (
    classify_operation_failure,
    evaluate_retry_decision,
)
from healthflow_safety.safety_gates import (
    evaluate_pre_submission_safety_gate,
)
from healthflow_safety.verification_engine import (
    evaluate_verification_outcome,
)

__all__ = [
    "ACTION_STATE_PERMISSIONS",
    "ALLOWED_ESCALATION_REASONS",
    "ALLOWED_PROCEDURE_PREFIX",
    "MANDATORY_ESCALATION_CODES",
    "TERMINAL_STATES",
    "FailureCategory",
    "InputValidationResult",
    "PermissionCheckResult",
    "RetryDecision",
    "SafetyGateResult",
    "SafetyViolation",
    "UserRole",
    "VerificationDecision",
    "check_action_permission",
    "classify_operation_failure",
    "evaluate_pre_submission_safety_gate",
    "evaluate_retry_decision",
    "evaluate_verification_outcome",
    "format_escalation_envelope",
    "is_escalation_mandatory",
    "validate_document_reference",
    "validate_escalation_inputs",
    "validate_patient_identifier",
    "validate_plan_identifier",
    "validate_procedure_type",
    "validate_submission_inputs",
    "validate_verification_inputs",
]
