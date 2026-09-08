"""API response/request models.

All API responses are serialized Pydantic models — raw domain or SQLAlchemy types never appear
here (docs/architecture/ARCHITECTURE.md §16.3).
"""

from __future__ import annotations

from pydantic import BaseModel


class PatientOption(BaseModel):
    """A selectable synthetic benchmark patient for the demo 'new case' picker."""

    patient_id: str
    name: str
    scenario: str
    procedure_type: str


class CaseSummary(BaseModel):
    case_id: str
    patient_id: str
    patient_name: str
    procedure_type: str
    current_state: str
    created_at: str
    updated_at: str


class WorkflowTransitionOut(BaseModel):
    from_state: str
    to_state: str
    reason: str
    actor: str
    transitioned_at: str


class CaseDetail(CaseSummary):
    clinical_indication: str
    priority: str
    transitions: list[WorkflowTransitionOut]


class ToolCallStepOut(BaseModel):
    tool_name: str
    arguments: dict[str, object]
    result: dict[str, object]
    success: bool


class RunCaseResponse(BaseModel):
    case_id: str
    status: str
    is_verified: bool
    final_response: str
    current_state: str
    steps: list[ToolCallStepOut]


class CreateCaseRequest(BaseModel):
    patient_id: str


class ErrorResponse(BaseModel):
    error_code: str
    error_message: str
