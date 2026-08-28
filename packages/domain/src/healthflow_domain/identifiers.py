"""HealthFlow Domain Identifiers.

Strongly-typed value objects representing entity identifiers across the domain.
Prevents primitive obsession and identifier cross-assignment errors.

Ref: docs/architecture/ARCHITECTURE.md §5
"""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class PatientId:
    """Strongly-typed identifier for a Patient."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("PatientId cannot be empty.")

    @classmethod
    def generate(cls) -> "PatientId":
        return cls(f"pat_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PlanId:
    """Strongly-typed identifier for an InsurancePlan."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("PlanId cannot be empty.")

    @classmethod
    def generate(cls) -> "PlanId":
        return cls(f"plan_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CaseId:
    """Strongly-typed identifier for an AuthorizationCase."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("CaseId cannot be empty.")

    @classmethod
    def generate(cls) -> "CaseId":
        return cls(f"case_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SubmissionId:
    """Strongly-typed identifier for a SubmissionRecord."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("SubmissionId cannot be empty.")

    @classmethod
    def generate(cls) -> "SubmissionId":
        return cls(f"sub_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class VerificationId:
    """Strongly-typed identifier for a VerificationRecord."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("VerificationId cannot be empty.")

    @classmethod
    def generate(cls) -> "VerificationId":
        return cls(f"ver_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class EscalationId:
    """Strongly-typed identifier for an EscalationRecord."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("EscalationId cannot be empty.")

    @classmethod
    def generate(cls) -> "EscalationId":
        return cls(f"esc_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TransitionId:
    """Strongly-typed identifier for a WorkflowTransition."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("TransitionId cannot be empty.")

    @classmethod
    def generate(cls) -> "TransitionId":
        return cls(f"trn_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AuditId:
    """Strongly-typed identifier for an AuditRecord."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("AuditId cannot be empty.")

    @classmethod
    def generate(cls) -> "AuditId":
        return cls(f"aud_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        return self.value
