"""AD-012 Retry Policy & Failure Classification Test Suite.

Verifies that the 4 failure categories, exponential backoff, status pre-checks,
and strict non-bypass invariants defined in AD-012 are deterministically enforced.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-012
Ref: docs/architecture/ARCHITECTURE.md §20
Ref: docs/product/PRODUCT_REQUIREMENTS.md §7, §10, §21
"""

import pytest
from healthflow_safety import (
    FailureCategory,
    classify_operation_failure,
    evaluate_retry_decision,
)
from healthflow_safety.retry_policy import (
    MAX_READ_ATTEMPTS,
    MAX_SUBMISSION_RETRIES_AFTER_PRECHECK,
    MAX_VERIFICATION_ATTEMPTS,
    calculate_backoff_delay,
)


class TestFailureClassification:
    """Verifies that all operations are correctly classified into the 4 AD-012 categories."""

    @pytest.mark.parametrize(
        "read_op",
        [
            "get_patient_record",
            "get_insurance_plan",
            "get_authorization_requirements",
            "get_required_document",
            "get_authorization_status",
        ],
    )
    def test_category_1_safe_read_classification(self, read_op: str) -> None:
        cat = classify_operation_failure(read_op, error_code=None, is_transient=True)
        assert cat == FailureCategory.SAFE_READ_RETRYABLE

    def test_category_2_verification_read_classification(self) -> None:
        cat = classify_operation_failure(
            "verify_authorization_outcome", error_code=None, is_transient=True
        )
        assert cat == FailureCategory.VERIFICATION_RETRYABLE

    def test_category_3_submission_classification(self) -> None:
        cat = classify_operation_failure(
            "submit_authorization_request", error_code=None, is_transient=True
        )
        assert cat == FailureCategory.SUBMISSION_WITH_PRECHECK

    @pytest.mark.parametrize(
        "deterministic_code",
        [
            "VALIDATION_FAILED",
            "PERMISSION_DENIED",
            "SAFETY_GATE_FAILED",
            "INVALID_IDENTIFIER",
            "MALFORMED_IDENTIFIER",
            "INJECTION_ATTEMPT_DETECTED",
            "UNSUPPORTED_PROCEDURE",
        ],
    )
    def test_category_4_deterministic_failure_classification(
        self, deterministic_code: str
    ) -> None:
        cat = classify_operation_failure(
            "get_patient_record",
            error_code=deterministic_code,
            is_transient=True,
        )
        assert cat == FailureCategory.NON_RETRYABLE_DETERMINISTIC


class TestExponentialBackoffCalculation:
    """Verifies exponential backoff with delay caps."""

    def test_initial_retry_delay(self) -> None:
        # Attempt 1 -> 1.0s
        assert calculate_backoff_delay(1) == 1.0

    def test_second_retry_delay(self) -> None:
        # Attempt 2 -> 2.0s
        assert calculate_backoff_delay(2) == 2.0

    def test_third_retry_delay(self) -> None:
        # Attempt 3 -> 4.0s
        assert calculate_backoff_delay(3) == 4.0

    def test_maximum_delay_cap(self) -> None:
        # Delays must never exceed 30.0s
        assert calculate_backoff_delay(10) == 30.0


class TestCategory1ReadRetries:
    """Verifies safe read retries up to maximum 3 attempts."""

    def test_read_retry_allowed_under_limit(self) -> None:
        dec = evaluate_retry_decision(
            "get_patient_record",
            current_attempt=1,
            is_transient=True,
        )
        assert dec.should_retry is True
        assert dec.attempt == 2
        assert dec.backoff_seconds == 1.0
        assert dec.requires_precheck is False

    def test_read_retry_exhaustion(self) -> None:
        dec = evaluate_retry_decision(
            "get_patient_record",
            current_attempt=MAX_READ_ATTEMPTS,
            is_transient=True,
        )
        assert dec.should_retry is False
        assert "exhausted maximum retry attempts" in dec.reason.lower()


class TestCategory2VerificationRetries:
    """Verifies verification read retries up to maximum 3 attempts."""

    def test_verification_retry_allowed(self) -> None:
        dec = evaluate_retry_decision(
            "verify_authorization_outcome",
            current_attempt=1,
            is_transient=True,
        )
        assert dec.should_retry is True
        assert dec.attempt == 2
        assert dec.category == FailureCategory.VERIFICATION_RETRYABLE

    def test_verification_retry_exhaustion(self) -> None:
        dec = evaluate_retry_decision(
            "verify_authorization_outcome",
            current_attempt=MAX_VERIFICATION_ATTEMPTS,
            is_transient=True,
        )
        assert dec.should_retry is False
        assert "not confirmed" in dec.reason.lower()


class TestCategory3SubmissionPreCheckRetries:
    """Verifies that consequential writes strictly require pre-checks to prevent duplicates."""

    def test_direct_submission_retry_denied_without_precheck(self) -> None:
        dec = evaluate_retry_decision(
            "submit_authorization_request",
            current_attempt=1,
            has_completed_precheck=False,  # NO PRECHECK
        )
        assert dec.should_retry is False
        assert dec.requires_precheck is True
        assert "status pre-check required" in dec.reason.lower()

    def test_submission_retry_halted_if_prior_submission_exists(self) -> None:
        dec = evaluate_retry_decision(
            "submit_authorization_request",
            current_attempt=1,
            has_completed_precheck=True,
            precheck_prior_submission_exists=True,  # ALREADY RECEIVED
        )
        assert dec.should_retry is False
        assert "duplicate submission halted" in dec.reason.lower()

    def test_submission_retry_permitted_if_prior_submission_absent(self) -> None:
        dec = evaluate_retry_decision(
            "submit_authorization_request",
            current_attempt=1,
            has_completed_precheck=True,
            precheck_prior_submission_exists=False,  # NO PRIOR SUBMISSION
        )
        assert dec.should_retry is True
        assert dec.attempt == 2
        assert "re-evaluation" in dec.reason.lower()

    def test_submission_retry_exhaustion(self) -> None:
        dec = evaluate_retry_decision(
            "submit_authorization_request",
            current_attempt=MAX_SUBMISSION_RETRIES_AFTER_PRECHECK + 1,
            has_completed_precheck=True,
            precheck_prior_submission_exists=False,
        )
        assert dec.should_retry is False
        assert "maximum re-submission attempts exhausted" in dec.reason.lower()


class TestCategory4NonRetryableFailures:
    """Verifies that validation, permission, and safety gate failures are NEVER retried."""

    @pytest.mark.parametrize(
        "error_code",
        [
            "VALIDATION_FAILED",
            "PERMISSION_DENIED",
            "SAFETY_GATE_FAILED",
            "INVALID_IDENTIFIER",
        ],
    )
    def test_deterministic_failures_never_retried(self, error_code: str) -> None:
        dec = evaluate_retry_decision(
            "submit_authorization_request",
            current_attempt=1,
            error_code=error_code,
        )
        assert dec.should_retry is False
        assert dec.category == FailureCategory.NON_RETRYABLE_DETERMINISTIC
        assert "non-retryable" in dec.reason.lower()
