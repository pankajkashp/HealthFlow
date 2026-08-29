"""Independent Outcome Verification Engine.

Evaluates independent verification results against authoritative external state.
Enforces the core DONE principle (PRS §7):
"The agent cannot say DONE. The environment has to prove DONE."

A submission acknowledgment (e.g. RECEIVED) is NOT evidence of completion.
Only an independent VerificationDecision with is_confirmed=True permits case completion.

Ref: docs/architecture/ARCHITECTURE.md §8.1, §9.1
Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-004, AD-013
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §12
"""

from typing import Any

from healthflow_safety.models import VerificationDecision


def evaluate_verification_outcome(
    expected_status: str,
    external_verification_result: Any,
) -> VerificationDecision:
    """Evaluate whether an independent verification result confirms final workflow completion."""
    clean_expected = expected_status.strip().upper()

    if external_verification_result is None:
        return VerificationDecision(
            is_confirmed=False,
            actual_status="UNAVAILABLE",
            decision="ERROR",
            verification_source="unknown",
            error_code="VERIFICATION_PROVIDER_UNAVAILABLE",
            details="External verification provider was unreachable or returned empty response.",
        )

    verified = getattr(external_verification_result, "verified", False)
    actual_status = getattr(
        external_verification_result, "actual_status", "UNKNOWN"
    ).upper()
    source = getattr(
        external_verification_result, "verification_source", "external_portal"
    )
    details = getattr(external_verification_result, "details", None)

    # Outcome is still pending determination in portal
    if actual_status in {"PENDING", "RECEIVED", "UNKNOWN"}:
        return VerificationDecision(
            is_confirmed=False,
            actual_status=actual_status,
            decision="NOT_CONFIRMED",
            verification_source=source,
            error_code="OUTCOME_PENDING",
            details=f"Authorization determination is pending in authoritative portal ({actual_status}).",
        )

    # Additional info required
    if actual_status == "ADDITIONAL_INFO_REQUIRED":
        return VerificationDecision(
            is_confirmed=False,
            actual_status=actual_status,
            decision="NOT_CONFIRMED",
            verification_source=source,
            error_code="ADDITIONAL_INFO_REQUIRED",
            details="Payer portal requires additional clinical information.",
        )

    # Mismatch between expected status and actual authoritative status (e.g. FALSE_SUCCESS scenario)
    if not verified or clean_expected != actual_status:
        return VerificationDecision(
            is_confirmed=False,
            actual_status=actual_status,
            decision="MISMATCH_DETECTED",
            verification_source=source,
            error_code="VERIFICATION_MISMATCH",
            details=(
                f"Authoritative state mismatch: expected '{clean_expected}', "
                f"but authoritative external state is '{actual_status}'."
            ),
        )

    # Outcome confirmed
    return VerificationDecision(
        is_confirmed=True,
        actual_status=actual_status,
        decision="CONFIRMED",
        verification_source=source,
        error_code=None,
        details=details
        or f"Authoritative external status confirmed as '{actual_status}'.",
    )
