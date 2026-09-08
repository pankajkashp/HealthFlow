"""Strands @tool adapters wrapping the 9 approved AgentTools methods.

AgentTools (packages/application, locked by AD-014) is never modified here — these are thin
standalone functions that call it and translate its frozen-dataclass results into plain dicts for
Strands tool-calling. All safety, permission, retry, and verification enforcement AgentTools already
performs is unchanged; this module only gives the LLM a real handle to call it.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-014
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from healthflow_application import AgentTools

ToolCallObserver = Callable[[str, dict[str, Any], dict[str, Any]], None]


def build_tool_adapters(
    tools: AgentTools,
    on_tool_call: ToolCallObserver | None = None,
) -> list[Any]:
    """Build the 9 Strands-callable tool functions bound to a specific AgentTools instance.

    on_tool_call, if given, is invoked with (tool_name, arguments, result) after every tool call
    completes — this is the deterministic hook used to persist workflow-state progression as the
    LLM works, independent of whatever the LLM's own reasoning claims.
    """
    from strands import tool

    def _record(
        name: str, args: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        if on_tool_call is not None:
            on_tool_call(name, args, result)
        return result

    @tool
    def get_patient_record(patient_identifier: str) -> dict[str, Any]:
        """Retrieve patient identity and reference data from the synthetic EHR.

        Args:
            patient_identifier: The synthetic patient identifier, e.g. "pat_jenkins_001".
        """
        args = {"patient_identifier": patient_identifier}
        return _record(
            "get_patient_record", args, asdict(tools.get_patient_record(**args))
        )

    @tool
    def get_insurance_plan(patient_id: str) -> dict[str, Any]:
        """Retrieve the patient's active insurance plan from the synthetic payer system.

        Args:
            patient_id: The patient identifier returned by get_patient_record.
        """
        args = {"patient_id": patient_id}
        return _record(
            "get_insurance_plan", args, asdict(tools.get_insurance_plan(**args))
        )

    @tool
    def get_authorization_requirements(
        plan_id: str, procedure_type: str
    ) -> dict[str, Any]:
        """Retrieve prior-authorization requirements for an MRI procedure under the plan.

        Args:
            plan_id: The insurance plan identifier.
            procedure_type: The MRI procedure type, e.g. MRI_LUMBAR_SPINE, MRI_KNEE, MRI_BRAIN,
                MRI_SHOULDER, MRI_CERVICAL_SPINE, MRI_ABDOMEN, MRI_PELVIS.
        """
        args = {"plan_id": plan_id, "procedure_type": procedure_type}
        return _record(
            "get_authorization_requirements",
            args,
            asdict(tools.get_authorization_requirements(**args)),
        )

    @tool
    def get_required_document(
        document_reference: str, document_type: str
    ) -> dict[str, Any]:
        """Retrieve metadata and a content reference for a supporting clinical document.

        Args:
            document_reference: The document reference identifier to look up.
            document_type: The type of supporting document required.
        """
        args = {
            "document_reference": document_reference,
            "document_type": document_type,
        }
        return _record(
            "get_required_document", args, asdict(tools.get_required_document(**args))
        )

    @tool
    def validate_authorization_package(
        patient_id: str,
        plan_id: str,
        requirements_id: str,
        document_ids: list[str],
    ) -> dict[str, Any]:
        """Run deterministic pre-submission validation over the gathered authorization materials.

        Always call this before submit_authorization_request.

        Args:
            patient_id: The patient identifier.
            plan_id: The insurance plan identifier.
            requirements_id: The requirements identifier from get_authorization_requirements.
            document_ids: The list of document identifiers gathered so far.
        """
        args: dict[str, Any] = {
            "patient_id": patient_id,
            "plan_id": plan_id,
            "requirements_id": requirements_id,
            "document_ids": document_ids,
        }
        result = tools.validate_authorization_package(
            patient_id, plan_id, requirements_id, document_ids
        )
        return _record("validate_authorization_package", args, asdict(result))

    @tool
    def submit_authorization_request(
        patient_id: str,
        plan_id: str,
        requirements_id: str,
        document_ids: list[str],
        is_retry: bool = False,
        prior_submission_reference: str | None = None,
    ) -> dict[str, Any]:
        """Submit the complete authorization package to the payer portal.

        Only call this after validate_authorization_package reports is_valid=true.

        Args:
            patient_id: The patient identifier.
            plan_id: The insurance plan identifier.
            requirements_id: The requirements identifier.
            document_ids: The list of gathered document identifiers.
            is_retry: Whether this is a retry of a prior submission attempt.
            prior_submission_reference: The reference of the prior attempt; required if is_retry.
        """
        args: dict[str, Any] = {
            "patient_id": patient_id,
            "plan_id": plan_id,
            "requirements_id": requirements_id,
            "document_ids": document_ids,
            "is_retry": is_retry,
            "prior_submission_reference": prior_submission_reference,
        }
        result = tools.submit_authorization_request(
            patient_id,
            plan_id,
            requirements_id,
            document_ids,
            is_retry=is_retry,
            prior_submission_reference=prior_submission_reference,
        )
        return _record("submit_authorization_request", args, asdict(result))

    @tool
    def get_authorization_status(submission_reference: str) -> dict[str, Any]:
        """Query the payer portal's current determination status for a submitted request.

        Args:
            submission_reference: The submission reference returned by submit_authorization_request.
        """
        args = {"submission_reference": submission_reference}
        return _record(
            "get_authorization_status",
            args,
            asdict(tools.get_authorization_status(**args)),
        )

    @tool
    def verify_authorization_outcome(
        submission_reference: str, expected_status: str
    ) -> dict[str, Any]:
        """Independently verify the authorization outcome via a separate authoritative access path.

        This is the DONE-principle check (PRS §7): a submission acknowledgment is never proof of
        approval. Always call this before treating a case as complete.

        Args:
            submission_reference: The submission reference to verify.
            expected_status: The status you expect confirmed — "APPROVED" or "DENIED".
        """
        args = {
            "submission_reference": submission_reference,
            "expected_status": expected_status,
        }
        return _record(
            "verify_authorization_outcome",
            args,
            asdict(tools.verify_authorization_outcome(**args)),
        )

    @tool
    def request_escalation(reason_code: str, reason_summary: str) -> dict[str, Any]:
        """Escalate this case to human staff and pause autonomous execution.

        Call this whenever information is unresolvable, validation conflicts, verification fails,
        or you are not confident the workflow can safely continue.

        Args:
            reason_code: One of VALIDATION_CONFLICT, VERIFICATION_FAILED, SAFETY_GATE_FAILED,
                INFORMATION_UNRESOLVABLE, PERMISSION_EXCEEDED, PORTAL_ERROR, UNSUPPORTED_PROCEDURE,
                RETRIES_EXHAUSTED.
            reason_summary: A short human-readable explanation.
        """
        args = {"reason_code": reason_code, "reason_summary": reason_summary}
        return _record(
            "request_escalation", args, asdict(tools.request_escalation(**args))
        )

    return [
        get_patient_record,
        get_insurance_plan,
        get_authorization_requirements,
        get_required_document,
        validate_authorization_package,
        submit_authorization_request,
        get_authorization_status,
        verify_authorization_outcome,
        request_escalation,
    ]
