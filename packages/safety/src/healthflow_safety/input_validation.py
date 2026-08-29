"""Deterministic Input Validation & Sanitization Engine.

Enforces strict, rule-based validation on all agent inputs and tool arguments.
The LLM cannot bypass these rules. Any malicious, empty, malformed, or injection
patterns are deterministically rejected with structured InputValidationResult.

Ref: docs/architecture/ARCHITECTURE.md §8.1
Ref: docs/product/PRODUCT_REQUIREMENTS.md §8, §21
"""

import re
from typing import Final

from healthflow_safety.models import InputValidationResult

# Safe identifier pattern: alphanumeric, hyphen, underscore only
SAFE_IDENTIFIER_REGEX: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]+$")

# Prohibited injection patterns (SQL, script, traversal)
PROHIBITED_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"--"),
    re.compile(r";"),
    re.compile(r"/\*"),
    re.compile(r"\.\./"),
    re.compile(r"<[^>]*>"),
    re.compile(r"\b(DROP|DELETE|TRUNCATE|INSERT|UPDATE|UNION|SELECT)\b", re.IGNORECASE),
]

ALLOWED_PROCEDURE_PREFIX: Final[str] = "MRI"

ALLOWED_ESCALATION_REASONS: Final[set[str]] = {
    "VALIDATION_CONFLICT",
    "VERIFICATION_FAILED",
    "SAFETY_GATE_FAILED",
    "INFORMATION_UNRESOLVABLE",
    "PERMISSION_EXCEEDED",
    "PORTAL_ERROR",
    "UNSUPPORTED_PROCEDURE",
    "RETRIES_EXHAUSTED",
}


def _check_injection_patterns(text: str) -> str | None:
    """Check text for hostile injection sequences."""
    for pattern in PROHIBITED_PATTERNS:
        if pattern.search(text):
            return (
                f"Prohibited injection pattern detected matching '{pattern.pattern}'."
            )
    return None


def validate_patient_identifier(identifier: str) -> InputValidationResult:
    """Validate patient identifier format and safety."""
    if not identifier or not identifier.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_IDENTIFIER",
            error_message="Patient identifier must not be empty.",
        )

    clean = identifier.strip()
    if len(clean) > 64:
        return InputValidationResult(
            is_valid=False,
            error_code="IDENTIFIER_TOO_LONG",
            error_message="Patient identifier exceeds maximum length of 64 characters.",
        )

    injection_err = _check_injection_patterns(clean)
    if injection_err:
        return InputValidationResult(
            is_valid=False,
            error_code="INJECTION_ATTEMPT_DETECTED",
            error_message=injection_err,
        )

    if not SAFE_IDENTIFIER_REGEX.match(clean):
        return InputValidationResult(
            is_valid=False,
            error_code="MALFORMED_IDENTIFIER",
            error_message="Patient identifier contains invalid characters. Only alphanumeric, '-' and '_' allowed.",
        )

    return InputValidationResult(is_valid=True, sanitized_value=clean)


def validate_plan_identifier(plan_id: str) -> InputValidationResult:
    """Validate insurance plan identifier format and safety."""
    if not plan_id or not plan_id.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_PLAN_ID",
            error_message="Plan identifier must not be empty.",
        )

    clean = plan_id.strip()
    if len(clean) > 64:
        return InputValidationResult(
            is_valid=False,
            error_code="PLAN_ID_TOO_LONG",
            error_message="Plan identifier exceeds maximum length of 64 characters.",
        )

    injection_err = _check_injection_patterns(clean)
    if injection_err:
        return InputValidationResult(
            is_valid=False,
            error_code="INJECTION_ATTEMPT_DETECTED",
            error_message=injection_err,
        )

    if not SAFE_IDENTIFIER_REGEX.match(clean):
        return InputValidationResult(
            is_valid=False,
            error_code="MALFORMED_PLAN_ID",
            error_message="Plan identifier contains invalid characters.",
        )

    return InputValidationResult(is_valid=True, sanitized_value=clean)


def validate_procedure_type(procedure_type: str) -> InputValidationResult:
    """Validate procedure type matches MRI scope."""
    if not procedure_type or not procedure_type.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_PROCEDURE_TYPE",
            error_message="Procedure type must not be empty.",
        )

    clean = procedure_type.strip().upper()
    if not clean.startswith(ALLOWED_PROCEDURE_PREFIX):
        return InputValidationResult(
            is_valid=False,
            error_code="UNSUPPORTED_PROCEDURE",
            error_message=f"Only procedure types starting with '{ALLOWED_PROCEDURE_PREFIX}' are supported in MVP.",
        )

    injection_err = _check_injection_patterns(clean)
    if injection_err:
        return InputValidationResult(
            is_valid=False,
            error_code="INJECTION_ATTEMPT_DETECTED",
            error_message=injection_err,
        )

    return InputValidationResult(is_valid=True, sanitized_value=clean)


def validate_document_reference(
    document_reference: str, document_type: str
) -> InputValidationResult:
    """Validate document reference and expected type."""
    if not document_reference or not document_reference.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_DOCUMENT_REF",
            error_message="Document reference must not be empty.",
        )

    clean_ref = document_reference.strip()
    clean_type = document_type.strip() if document_type else ""

    injection_err = _check_injection_patterns(clean_ref) or _check_injection_patterns(
        clean_type
    )
    if injection_err:
        return InputValidationResult(
            is_valid=False,
            error_code="INJECTION_ATTEMPT_DETECTED",
            error_message=injection_err,
        )

    return InputValidationResult(
        is_valid=True,
        sanitized_value={"reference": clean_ref, "type": clean_type},
    )


def validate_submission_inputs(
    patient_id: str,
    plan_id: str,
    requirements_id: str,
    document_ids: list[str],
) -> InputValidationResult:
    """Validate submission inputs prior to safety gate execution."""
    p_val = validate_patient_identifier(patient_id)
    if not p_val.is_valid:
        return p_val

    pl_val = validate_plan_identifier(plan_id)
    if not pl_val.is_valid:
        return pl_val

    if not requirements_id or not requirements_id.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_REQUIREMENTS_ID",
            error_message="Requirements ID must not be empty.",
        )

    if not document_ids:
        return InputValidationResult(
            is_valid=False,
            error_code="EMPTY_DOCUMENT_LIST",
            error_message="Document IDs list cannot be empty for submission.",
        )

    for doc_id in document_ids:
        if not doc_id or not isinstance(doc_id, str) or not doc_id.strip():
            return InputValidationResult(
                is_valid=False,
                error_code="MALFORMED_DOCUMENT_ID",
                error_message="Encountered empty or non-string document ID.",
            )
        injection_err = _check_injection_patterns(doc_id)
        if injection_err:
            return InputValidationResult(
                is_valid=False,
                error_code="INJECTION_ATTEMPT_DETECTED",
                error_message=injection_err,
            )

    return InputValidationResult(
        is_valid=True,
        sanitized_value={
            "patient_id": p_val.sanitized_value,
            "plan_id": pl_val.sanitized_value,
            "requirements_id": requirements_id.strip(),
            "document_ids": [d.strip() for d in document_ids],
        },
    )


def validate_verification_inputs(
    submission_reference: str, expected_status: str
) -> InputValidationResult:
    """Validate inputs for independent outcome verification."""
    if not submission_reference or not submission_reference.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_SUBMISSION_REF",
            error_message="Submission reference must not be empty.",
        )

    clean_ref = submission_reference.strip()
    injection_err = _check_injection_patterns(clean_ref)
    if injection_err:
        return InputValidationResult(
            is_valid=False,
            error_code="INJECTION_ATTEMPT_DETECTED",
            error_message=injection_err,
        )

    if not expected_status or not expected_status.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_EXPECTED_STATUS",
            error_message="Expected status must not be empty.",
        )

    clean_status = expected_status.strip().upper()
    if clean_status not in {"APPROVED", "DENIED"}:
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_EXPECTED_STATUS",
            error_message="Expected status must be either 'APPROVED' or 'DENIED'.",
        )

    return InputValidationResult(
        is_valid=True,
        sanitized_value={
            "submission_reference": clean_ref,
            "expected_status": clean_status,
        },
    )


def validate_escalation_inputs(
    reason_code: str, reason_summary: str
) -> InputValidationResult:
    """Validate human escalation arguments."""
    if not reason_code or not reason_code.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_REASON_CODE",
            error_message="Escalation reason code must not be empty.",
        )

    clean_code = reason_code.strip().upper()
    if clean_code not in ALLOWED_ESCALATION_REASONS:
        return InputValidationResult(
            is_valid=False,
            error_code="INVALID_REASON_CODE",
            error_message=f"Reason code must be one of: {sorted(ALLOWED_ESCALATION_REASONS)}.",
        )

    if not reason_summary or not reason_summary.strip():
        return InputValidationResult(
            is_valid=False,
            error_code="EMPTY_REASON_SUMMARY",
            error_message="Reason summary must not be empty.",
        )

    clean_summary = reason_summary.strip()
    if len(clean_summary) > 500:
        return InputValidationResult(
            is_valid=False,
            error_code="REASON_SUMMARY_TOO_LONG",
            error_message="Reason summary must not exceed 500 characters.",
        )

    injection_err = _check_injection_patterns(clean_summary)
    if injection_err:
        return InputValidationResult(
            is_valid=False,
            error_code="INJECTION_ATTEMPT_DETECTED",
            error_message=injection_err,
        )

    return InputValidationResult(
        is_valid=True,
        sanitized_value={"reason_code": clean_code, "reason_summary": clean_summary},
    )
