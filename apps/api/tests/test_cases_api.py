"""End-to-end tests for the case workflow API (Phase 6).

Runs the full HTTP path — create case, run the agent, read it back — against a real Postgres
(same DATABASE_URL convention as the existing integration suite) with LLM_PROVIDER left at its
default ("scripted"), so these tests are free, deterministic, and require no LLM credentials.
Covers both the standard success path and the false-success/DONE-principle escalation path
(pat_chen_006), since that's the core safety guarantee this project exists to demonstrate.
"""

import pytest
from fastapi.testclient import TestClient

from healthflow_api.main import app

pytestmark = pytest.mark.usefixtures("_seed_demo_data")

client = TestClient(app)


def test_list_patient_options_includes_all_six_benchmark_patients() -> None:
    response = client.get("/api/v1/cases/patients")
    assert response.status_code == 200
    patient_ids = {p["patient_id"] for p in response.json()}
    assert patient_ids == {
        "pat_jenkins_001",
        "pat_martinez_002",
        "pat_rostova_003",
        "pat_kim_004",
        "pat_vance_005",
        "pat_chen_006",
    }


def test_create_case_for_unknown_patient_returns_404() -> None:
    response = client.post("/api/v1/cases", json={"patient_id": "pat_does_not_exist"})
    assert response.status_code == 404


def test_get_unknown_case_returns_404() -> None:
    response = client.get("/api/v1/cases/case_does_not_exist")
    assert response.status_code == 404


def test_create_case_starts_in_initiated_state() -> None:
    response = client.post("/api/v1/cases", json={"patient_id": "pat_jenkins_001"})
    assert response.status_code == 201
    body = response.json()
    assert body["current_state"] == "INITIATED"
    assert body["patient_name"] == "Sarah Jenkins (Synthetic)"
    assert body["transitions"] == []


def test_run_case_reaches_verified_completion_for_success_scenario() -> None:
    created = client.post("/api/v1/cases", json={"patient_id": "pat_jenkins_001"}).json()
    case_id = created["case_id"]

    run_response = client.post(f"/api/v1/cases/{case_id}/run")
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["status"] == "COMPLETED"
    assert run_body["is_verified"] is True
    assert run_body["current_state"] == "COMPLETED"
    tool_names = [step["tool_name"] for step in run_body["steps"]]
    assert tool_names[-1] == "verify_authorization_outcome"

    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert detail["current_state"] == "COMPLETED"
    assert detail["transitions"][-1]["to_state"] == "COMPLETED"
    assert detail["transitions"][0]["from_state"] == "INITIATED"


def test_run_case_escalates_on_false_success_mismatch() -> None:
    """The DONE-principle test case: portal ack succeeds, but authoritative state is DENIED."""
    created = client.post("/api/v1/cases", json={"patient_id": "pat_chen_006"}).json()
    case_id = created["case_id"]

    run_response = client.post(f"/api/v1/cases/{case_id}/run")
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["status"] == "ESCALATED"
    assert run_body["is_verified"] is False
    assert run_body["current_state"] == "ESCALATED"

    submit_step = next(
        s for s in run_body["steps"] if s["tool_name"] == "submit_authorization_request"
    )
    assert submit_step["result"]["success"] is True  # the portal DID ack success...

    verify_step = next(
        s for s in run_body["steps"] if s["tool_name"] == "verify_authorization_outcome"
    )
    assert verify_step["result"]["verified"] is False  # ...but independent verification caught it

    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert detail["current_state"] == "ESCALATED"
    final_transition = detail["transitions"][-1]
    assert final_transition["to_state"] == "ESCALATED"
    assert "mismatch" in final_transition["reason"].lower()


def test_run_case_for_missing_document_scenario_escalates() -> None:
    created = client.post("/api/v1/cases", json={"patient_id": "pat_martinez_002"}).json()
    case_id = created["case_id"]

    run_response = client.post(f"/api/v1/cases/{case_id}/run")
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert run_body["status"] == "ESCALATED"

    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert detail["current_state"] == "ESCALATED"


def test_list_cases_includes_created_cases() -> None:
    created = client.post("/api/v1/cases", json={"patient_id": "pat_rostova_003"}).json()
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    case_ids = {c["case_id"] for c in response.json()}
    assert created["case_id"] in case_ids
