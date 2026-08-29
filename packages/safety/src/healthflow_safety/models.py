"""HealthFlow Safety Layer Data Models.

Defines the core data structures and result contracts for deterministic safety controls,
permission checks, pre-action safety gates, retry decisions, and independent verification.

Ref: docs/architecture/ARCHITECTURE.md §8, §9, §20
Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-011, AD-012, AD-013
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FailureCategory(StrEnum):
    """AD-012 failure categories for agent operations."""

    SAFE_READ_RETRYABLE = "SAFE_READ_RETRYABLE"  # Category 1: Idempotent reads
    VERIFICATION_RETRYABLE = "VERIFICATION_RETRYABLE"  # Category 2: Verification reads
    SUBMISSION_WITH_PRECHECK = (
        "SUBMISSION_WITH_PRECHECK"  # Category 3: Writes needing pre-check
    )
    NON_RETRYABLE_DETERMINISTIC = (
        "NON_RETRYABLE_DETERMINISTIC"  # Category 4: Validation/gate/permission
    )


class UserRole(StrEnum):
    """Authenticated user/actor roles."""

    AGENT = "AGENT"
    CLINICAL_STAFF = "CLINICAL_STAFF"
    PHYSICIAN = "PHYSICIAN"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class SafetyViolation:
    """Individual safety invariant violation."""

    code: str
    message: str
    severity: str = "ERROR"  # ERROR | WARNING


@dataclass(frozen=True)
class InputValidationResult:
    """Result of deterministic, rule-based input sanitization and validation."""

    is_valid: bool
    sanitized_value: Any = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class PermissionCheckResult:
    """Result of deterministic action authorization against workflow state."""

    allowed: bool
    action: str
    current_state: str
    actor_role: str = UserRole.AGENT.value
    denial_reason: str | None = None


@dataclass(frozen=True)
class SafetyGateResult:
    """Outcome of a pre-action deterministic safety gate."""

    allowed: bool
    gate_name: str
    reason_code: str | None = None
    violations: list[SafetyViolation] = field(default_factory=list)


@dataclass(frozen=True)
class RetryDecision:
    """Deterministic retry determination per AD-012."""

    should_retry: bool
    category: FailureCategory
    attempt: int
    backoff_seconds: float
    requires_precheck: bool
    reason: str


@dataclass(frozen=True)
class VerificationDecision:
    """Outcome of independent verification against authoritative external state."""

    is_confirmed: bool
    actual_status: str
    decision: str  # CONFIRMED | NOT_CONFIRMED | MISMATCH_DETECTED | ERROR
    verification_source: str
    error_code: str | None = None
    details: str | None = None
