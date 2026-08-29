"""Human Escalation Decision Boundary Engine.

Defines the deterministic criteria under which autonomous execution must be paused
and control transferred to human clinical/administrative staff.
The LLM cannot bypass safety gates by refusing to escalate, nor can it escalate for unapproved reasons.

Ref: docs/architecture/ARCHITECTURE.md §8.1, §10
Ref: docs/product/PRODUCT_REQUIREMENTS.md §10, §21
"""

from typing import Any, Final

MANDATORY_ESCALATION_CODES: Final[set[str]] = {
    "VALIDATION_CONFLICT",
    "VERIFICATION_FAILED",
    "SAFETY_GATE_FAILED",
    "INFORMATION_UNRESOLVABLE",
    "PERMISSION_EXCEEDED",
    "PORTAL_ERROR",
    "UNSUPPORTED_PROCEDURE",
    "RETRIES_EXHAUSTED",
    "CLINICAL_DATA_CONFLICT",
}


def is_escalation_mandatory(
    reason_code: str,
    context: dict[str, Any] | None = None,
) -> bool:
    """Determine whether an error condition strictly requires human escalation."""
    clean_code = reason_code.strip().upper()
    return clean_code in MANDATORY_ESCALATION_CODES


def format_escalation_envelope(
    case_id: str,
    reason_code: str,
    reason_summary: str,
    actor: str = "safety_engine",
) -> dict[str, Any]:
    """Format structured escalation payload for human staff intervention."""
    return {
        "case_id": case_id,
        "reason_code": reason_code.strip().upper(),
        "reason_summary": reason_summary.strip()[:500],
        "escalated_by": actor,
        "requires_human_review": True,
        "is_resumable": True,
    }
