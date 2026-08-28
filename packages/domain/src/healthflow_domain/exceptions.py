"""HealthFlow Domain Exceptions.

Hierarchy of domain errors representing rule, invariant, and transition violations.
All domain exceptions inherit from DomainError.

Ref: docs/architecture/ARCHITECTURE.md §2.4
"""


class DomainError(Exception):
    """Base exception for all domain-level errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidWorkflowTransitionError(DomainError):
    """Raised when an illegal workflow state transition is attempted."""

    def __init__(
        self,
        from_state: str,
        to_state: str,
        reason: str = "Transition not permitted by transition matrix.",
    ) -> None:
        message = f"Invalid workflow state transition from {from_state} to {to_state}: {reason}"
        super().__init__(message)
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason


class InvariantViolationError(DomainError):
    """Raised when a business invariant is violated."""


class DomainValidationError(DomainError):
    """Raised when domain entity data fails deterministic validation."""


class EntityNotFoundError(DomainError):
    """Raised when a requested domain entity cannot be found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        message = f"{entity_type} with ID '{entity_id}' not found."
        super().__init__(message)
        self.entity_type = entity_type
        self.entity_id = entity_id


class DataBoundaryViolationError(DomainError):
    """Raised when non-synthetic healthcare data or PHI is detected."""
