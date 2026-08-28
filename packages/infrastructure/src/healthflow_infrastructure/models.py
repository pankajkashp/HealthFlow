"""HealthFlow Infrastructure SQLAlchemy 2.x Persistence Models.

Declarative ORM models representing the authoritative PostgreSQL schema for HealthFlow.
These models are internal to the infrastructure layer and MUST NOT leak into the
domain or application layers.

Ref: docs/architecture/ARCHITECTURE.md §14
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from healthflow_infrastructure.database import Base


class PatientModel(Base):
    """PostgreSQL table 'patients'."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    ehr_reference: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    insurance_plans: Mapped[list["InsurancePlanModel"]] = relationship(
        "InsurancePlanModel", back_populates="patient", cascade="all, delete-orphan"
    )
    cases: Mapped[list["AuthorizationCaseModel"]] = relationship(
        "AuthorizationCaseModel", back_populates="patient"
    )


class InsurancePlanModel(Base):
    """PostgreSQL table 'insurance_plans'."""

    __tablename__ = "insurance_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insurer_reference: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    plan_type: Mapped[str] = mapped_column(String(100), nullable=False)
    member_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    patient: Mapped["PatientModel"] = relationship(
        "PatientModel", back_populates="insurance_plans"
    )
    cases: Mapped[list["AuthorizationCaseModel"]] = relationship(
        "AuthorizationCaseModel", back_populates="insurance_plan"
    )


class AuthorizationCaseModel(Base):
    """PostgreSQL table 'authorization_cases'."""

    __tablename__ = "authorization_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    insurance_plan_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("insurance_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    procedure_type: Mapped[str] = mapped_column(String(100), nullable=False)
    clinical_indication: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="ROUTINE")
    current_state: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, default="INITIATED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    patient: Mapped["PatientModel"] = relationship(
        "PatientModel", back_populates="cases"
    )
    insurance_plan: Mapped["InsurancePlanModel"] = relationship(
        "InsurancePlanModel", back_populates="cases"
    )
    transitions: Mapped[list["WorkflowTransitionModel"]] = relationship(
        "WorkflowTransitionModel", back_populates="case", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["SubmissionRecordModel"]] = relationship(
        "SubmissionRecordModel", back_populates="case", cascade="all, delete-orphan"
    )
    verifications: Mapped[list["VerificationRecordModel"]] = relationship(
        "VerificationRecordModel", back_populates="case", cascade="all, delete-orphan"
    )
    escalations: Mapped[list["EscalationRecordModel"]] = relationship(
        "EscalationRecordModel", back_populates="case", cascade="all, delete-orphan"
    )
    audits: Mapped[list["AuditRecordModel"]] = relationship(
        "AuditRecordModel", back_populates="case"
    )


class WorkflowTransitionModel(Base):
    """PostgreSQL table 'workflow_transitions'."""

    __tablename__ = "workflow_transitions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("authorization_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[str] = mapped_column(String(50), nullable=False)
    to_state: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    case: Mapped["AuthorizationCaseModel"] = relationship(
        "AuthorizationCaseModel", back_populates="transitions"
    )


class SubmissionRecordModel(Base):
    """PostgreSQL table 'submission_records'."""

    __tablename__ = "submission_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("authorization_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_reference: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    initial_status: Mapped[str] = mapped_column(String(100), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    case: Mapped["AuthorizationCaseModel"] = relationship(
        "AuthorizationCaseModel", back_populates="submissions"
    )


class VerificationRecordModel(Base):
    """PostgreSQL table 'verification_records'."""

    __tablename__ = "verification_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("authorization_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_reference: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    verification_details: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    case: Mapped["AuthorizationCaseModel"] = relationship(
        "AuthorizationCaseModel", back_populates="verifications"
    )


class EscalationRecordModel(Base):
    """PostgreSQL table 'escalation_records'."""

    __tablename__ = "escalation_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("authorization_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    from_state: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    case: Mapped["AuthorizationCaseModel"] = relationship(
        "AuthorizationCaseModel", back_populates="escalations"
    )


class AuditRecordModel(Base):
    """PostgreSQL table 'audit_records'."""

    __tablename__ = "audit_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    case_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("authorization_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    case: Mapped["AuthorizationCaseModel | None"] = relationship(
        "AuthorizationCaseModel", back_populates="audits"
    )


# Additional Compound Indexes for Common Queries
Index(
    "idx_cases_patient_state",
    AuthorizationCaseModel.patient_id,
    AuthorizationCaseModel.current_state,
)
Index(
    "idx_transitions_case_date",
    WorkflowTransitionModel.case_id,
    WorkflowTransitionModel.transitioned_at,
)
Index("idx_audits_case_date", AuditRecordModel.case_id, AuditRecordModel.timestamp)
