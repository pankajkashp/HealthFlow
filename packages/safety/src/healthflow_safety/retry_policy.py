"""AD-012 Retry & Failure Classification Engine.

Implements the exact four-category failure policy specified in AD-012.
Enforces that retries never bypass permission checks, safety gates, or independent verification.
Consequential write retries strictly require an authoritative status pre-check.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-012
Ref: docs/architecture/ARCHITECTURE.md §20
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §10, §21
"""

import math
from typing import Final

from healthflow_safety.models import FailureCategory, RetryDecision

# Category mappings per AD-012
CATEGORY_1_OPERATIONS: Final[set[str]] = {
    "get_patient_record",
    "get_insurance_plan",
    "get_authorization_requirements",
    "get_required_document",
    "get_authorization_status",
}

CATEGORY_2_OPERATIONS: Final[set[str]] = {
    "verify_authorization_outcome",
}

CATEGORY_3_OPERATIONS: Final[set[str]] = {
    "submit_authorization_request",
}

# Retry limits
MAX_READ_ATTEMPTS: Final[int] = 3  # 1 initial + 2 retries
MAX_VERIFICATION_ATTEMPTS: Final[int] = 3
MAX_SUBMISSION_RETRIES_AFTER_PRECHECK: Final[int] = 2

# Exponential backoff parameters
BASE_DELAY_SECONDS: Final[float] = 1.0
BACKOFF_MULTIPLIER: Final[float] = 2.0
MAX_DELAY_SECONDS: Final[float] = 30.0


def classify_operation_failure(
    operation_name: str,
    error_code: str | None = None,
    is_transient: bool = True,
) -> FailureCategory:
    """Classify an operation failure into one of the four AD-012 categories."""
    # Deterministic failures are always Category 4
    deterministic_prefixes = (
        "VALIDATION",
        "PERMISSION",
        "SAFETY_GATE",
        "INVALID",
        "MALFORMED",
        "INJECTION",
        "UNSUPPORTED",
    )
    if error_code and any(error_code.startswith(p) for p in deterministic_prefixes):
        return FailureCategory.NON_RETRYABLE_DETERMINISTIC

    if not is_transient:
        return FailureCategory.NON_RETRYABLE_DETERMINISTIC

    if operation_name in CATEGORY_1_OPERATIONS:
        return FailureCategory.SAFE_READ_RETRYABLE
    elif operation_name in CATEGORY_2_OPERATIONS:
        return FailureCategory.VERIFICATION_RETRYABLE
    elif operation_name in CATEGORY_3_OPERATIONS:
        return FailureCategory.SUBMISSION_WITH_PRECHECK

    return FailureCategory.NON_RETRYABLE_DETERMINISTIC


def calculate_backoff_delay(attempt: int) -> float:
    """Calculate exponential backoff delay for the given retry attempt (1-indexed)."""
    delay = BASE_DELAY_SECONDS * math.pow(BACKOFF_MULTIPLIER, max(0, attempt - 1))
    return min(delay, MAX_DELAY_SECONDS)


def evaluate_retry_decision(
    operation_name: str,
    current_attempt: int,
    error_code: str | None = None,
    is_transient: bool = True,
    has_completed_precheck: bool = False,
    precheck_prior_submission_exists: bool = False,
) -> RetryDecision:
    """Evaluate whether an operation is permitted to retry per AD-012 rules."""
    category = classify_operation_failure(operation_name, error_code, is_transient)

    # --------------------------------------------------------------------------
    # Category 4: Deterministic failures are NEVER retryable
    # --------------------------------------------------------------------------
    if category == FailureCategory.NON_RETRYABLE_DETERMINISTIC:
        return RetryDecision(
            should_retry=False,
            category=category,
            attempt=current_attempt,
            backoff_seconds=0.0,
            requires_precheck=False,
            reason=f"Deterministic failure '{error_code}' is non-retryable. Requires data correction or escalation.",
        )

    # --------------------------------------------------------------------------
    # Category 1: Safe read operations
    # --------------------------------------------------------------------------
    if category == FailureCategory.SAFE_READ_RETRYABLE:
        if current_attempt < MAX_READ_ATTEMPTS:
            backoff = calculate_backoff_delay(current_attempt)
            return RetryDecision(
                should_retry=True,
                category=category,
                attempt=current_attempt + 1,
                backoff_seconds=backoff,
                requires_precheck=False,
                reason=f"Transient read failure; retry attempt {current_attempt + 1}/{MAX_READ_ATTEMPTS} scheduled.",
            )
        else:
            return RetryDecision(
                should_retry=False,
                category=category,
                attempt=current_attempt,
                backoff_seconds=0.0,
                requires_precheck=False,
                reason=f"Read operation exhausted maximum retry attempts ({MAX_READ_ATTEMPTS}). Escalation required.",
            )

    # --------------------------------------------------------------------------
    # Category 2: Verification operations
    # --------------------------------------------------------------------------
    if category == FailureCategory.VERIFICATION_RETRYABLE:
        if current_attempt < MAX_VERIFICATION_ATTEMPTS:
            backoff = calculate_backoff_delay(current_attempt)
            return RetryDecision(
                should_retry=True,
                category=category,
                attempt=current_attempt + 1,
                backoff_seconds=backoff,
                requires_precheck=False,
                reason=f"Transient verification query failure; retry attempt {current_attempt + 1}/{MAX_VERIFICATION_ATTEMPTS}.",
            )
        else:
            return RetryDecision(
                should_retry=False,
                category=category,
                attempt=current_attempt,
                backoff_seconds=0.0,
                requires_precheck=False,
                reason=f"Verification exhausted maximum retry attempts ({MAX_VERIFICATION_ATTEMPTS}). Outcome NOT CONFIRMED; escalation required.",
            )

    # --------------------------------------------------------------------------
    # Category 3: Submissions (Write Operation)
    # --------------------------------------------------------------------------
    if category == FailureCategory.SUBMISSION_WITH_PRECHECK:
        # Mandatory invariant: Pre-check is required before ANY submission retry
        if not has_completed_precheck:
            return RetryDecision(
                should_retry=False,
                category=category,
                attempt=current_attempt,
                backoff_seconds=0.0,
                requires_precheck=True,
                reason="Direct submission retry prohibited. Status pre-check required to avoid duplicate submission.",
            )

        if precheck_prior_submission_exists:
            return RetryDecision(
                should_retry=False,
                category=category,
                attempt=current_attempt,
                backoff_seconds=0.0,
                requires_precheck=False,
                reason="Pre-check confirmed prior submission was already received. Duplicate submission halted.",
            )

        # Pre-check confirmed no prior submission exists -> retry permitted with safety gate re-evaluation
        if current_attempt <= MAX_SUBMISSION_RETRIES_AFTER_PRECHECK:
            backoff = calculate_backoff_delay(current_attempt)
            return RetryDecision(
                should_retry=True,
                category=category,
                attempt=current_attempt + 1,
                backoff_seconds=backoff,
                requires_precheck=False,
                reason=f"Pre-check confirmed absence of prior submission. Re-submission attempt {current_attempt + 1} permitted with safety gate re-evaluation.",
            )
        else:
            return RetryDecision(
                should_retry=False,
                category=category,
                attempt=current_attempt,
                backoff_seconds=0.0,
                requires_precheck=False,
                reason="Maximum re-submission attempts exhausted. Escalation required.",
            )

    return RetryDecision(
        should_retry=False,
        category=FailureCategory.NON_RETRYABLE_DETERMINISTIC,
        attempt=current_attempt,
        backoff_seconds=0.0,
        requires_precheck=False,
        reason="Operation unretryable.",
    )
