"""Case routes — thin HTTP boundary that delegates entirely to CaseOrchestrator.

No business logic lives here (docs/architecture/ARCHITECTURE.md §16.7): every handler parses the
request, calls one orchestrator method, and returns its already-built response schema.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from healthflow_api.dependencies import CaseOrchestrator, get_case_orchestrator
from healthflow_api.schemas import (
    CaseDetail,
    CaseSummary,
    CreateCaseRequest,
    PatientOption,
    RunCaseResponse,
)

router = APIRouter(prefix="/cases", tags=["cases"])

OrchestratorDep = Annotated[CaseOrchestrator, Depends(get_case_orchestrator)]


@router.get("/patients", response_model=list[PatientOption])
def list_patient_options(orchestrator: OrchestratorDep) -> list[PatientOption]:
    """List the 6 synthetic benchmark patients available to start a demo case."""
    return orchestrator.list_patient_options()


@router.get("", response_model=list[CaseSummary])
def list_cases(orchestrator: OrchestratorDep) -> list[CaseSummary]:
    return orchestrator.list_cases()


@router.post("", response_model=CaseDetail, status_code=201)
def create_case(request: CreateCaseRequest, orchestrator: OrchestratorDep) -> CaseDetail:
    try:
        return orchestrator.create_case(request.patient_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, orchestrator: OrchestratorDep) -> CaseDetail:
    try:
        return orchestrator.get_case_detail(case_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.post("/{case_id}/run", response_model=RunCaseResponse)
def run_case(case_id: str, orchestrator: OrchestratorDep) -> RunCaseResponse:
    try:
        return orchestrator.run_case(case_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
