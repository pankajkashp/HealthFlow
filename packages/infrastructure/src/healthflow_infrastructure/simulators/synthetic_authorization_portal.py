"""Synthetic Prior-Authorization Payer Portal Simulator.

Simulates an external electronic prior-authorization web portal / clearinghouse.
Maintains authoritative external state, supports asynchronous status queries,
and implements the critical FALSE_SUCCESS scenario for independent verification.

Ref: docs/architecture/ARCHITECTURE.md §6.5, §6.6, §6.7, §13
Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-004
"""

import uuid
from datetime import datetime, timezone

from healthflow_domain.external_models import (
    ExternalVerificationResult,
    PortalStatusRecord,
    PortalSubmissionAck,
    PortalSubmissionPayload,
)

from healthflow_infrastructure.simulators.models import (
    ALL_BENCHMARK_FIXTURES,
    SyntheticCaseFixture,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SyntheticAuthorizationPortalSimulator:
    """In-memory deterministic simulator for external prior-authorization portals."""

    def __init__(self, fixtures: dict[str, SyntheticCaseFixture] | None = None) -> None:
        self._fixtures = (
            fixtures if fixtures is not None else dict(ALL_BENCHMARK_FIXTURES)
        )
        self._is_available: bool = True
        # Authoritative external portal state registry: submission_ref -> PortalStatusRecord
        self._authoritative_state: dict[str, PortalStatusRecord] = {}

    def set_availability(self, available: bool) -> None:
        """Simulate portal downtime or gateway timeout."""
        self._is_available = available

    def set_authoritative_status(
        self, submission_reference: str, status_record: PortalStatusRecord
    ) -> None:
        """Explicitly set or mutate the authoritative external state for a submission."""
        self._authoritative_state[submission_reference] = status_record

    def submit(self, payload: PortalSubmissionPayload) -> PortalSubmissionAck:
        """Receive electronic submission package from HealthFlow.

        Returns an immediate acknowledgment (submission reference and acknowledgment status).
        """
        if not self._is_available:
            return PortalSubmissionAck(
                success=False,
                submission_reference=None,
                ack_status="GATEWAY_TIMEOUT",
                error_code="ERR_PORTAL_UNAVAILABLE",
                error_message="Simulated payer portal is currently unreachable.",
            )

        fixture = self._fixtures.get(payload.patient_id)

        # 1. Check if the scenario dictates an immediate gateway failure
        if fixture and not fixture.simulated_ack_success:
            return PortalSubmissionAck(
                success=False,
                submission_reference=None,
                ack_status="SUBMISSION_REJECTED",
                error_code="ERR_PORTAL_REJECT",
                error_message="Payer portal rejected submission package at gateway.",
            )

        # 2. Generate submission reference
        sub_ref = (
            fixture.simulated_ack_reference
            if (fixture and fixture.simulated_ack_reference)
            else f"AUTH-SUB-{uuid.uuid4().hex[:8].upper()}"
        )

        # 3. Determine authoritative backend decision
        # Notice: In the FALSE_SUCCESS scenario, the gateway reports success and issues
        # an acknowledgment ("RECEIVED"), but the authoritative backend sets state to DENIED!
        initial_decision = fixture.initial_portal_decision if fixture else "APPROVED"

        status_record = PortalStatusRecord(
            submission_reference=sub_ref,
            portal_status=initial_decision,
            status_message=f"Portal determination: {initial_decision}",
            determination_date=_now_iso(),
            additional_info_requested=(
                ["conservative_therapy_notes"]
                if initial_decision == "ADDITIONAL_INFO_REQUIRED"
                else None
            ),
        )
        self._authoritative_state[sub_ref] = status_record

        return PortalSubmissionAck(
            success=True,
            submission_reference=sub_ref,
            ack_status="RECEIVED",
            received_timestamp=_now_iso(),
        )

    def get_status(self, submission_reference: str) -> PortalStatusRecord | None:
        """Query the portal for current authorization determination status."""
        if not self._is_available:
            return None

        return self._authoritative_state.get(submission_reference)

    def verify_outcome_independently(
        self, submission_reference: str, expected_status: str
    ) -> ExternalVerificationResult:
        """Perform an independent verification check against authoritative portal state.

        This uses a separate logical query path as required by AD-004.
        """
        if not self._is_available:
            return ExternalVerificationResult(
                verified=False,
                submission_reference=submission_reference,
                expected_status=expected_status,
                actual_status="UNAVAILABLE",
                verification_source="synthetic_portal_authoritative_adjudication_db",
                details="Verification endpoint unreachable.",
                verified_at=_now_iso(),
            )

        record = self._authoritative_state.get(submission_reference)
        if record is None:
            return ExternalVerificationResult(
                verified=False,
                submission_reference=submission_reference,
                expected_status=expected_status,
                actual_status="NOT_FOUND",
                verification_source="synthetic_portal_authoritative_adjudication_db",
                details=f"No record found in authoritative database for reference '{submission_reference}'.",
                verified_at=_now_iso(),
            )

        is_verified = record.portal_status == expected_status
        details = (
            f"Authoritative external status confirmed as '{record.portal_status}'."
            if is_verified
            else f"MISMATCH DETECTED: Expected '{expected_status}', but authoritative state is '{record.portal_status}'."
        )

        return ExternalVerificationResult(
            verified=is_verified,
            submission_reference=submission_reference,
            expected_status=expected_status,
            actual_status=record.portal_status,
            verification_source="synthetic_portal_authoritative_adjudication_db",
            details=details,
            verified_at=_now_iso(),
        )
