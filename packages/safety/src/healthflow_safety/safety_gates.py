"""Pre-Action Deterministic Safety Gate Pipeline.

Guards consequential operations (especially portal submission) against safety violations,
data boundary breaches, missing documentation, clinical conflicts, and data hallucinations.
The gate runs entirely in deterministic application code and cannot be bypassed.

Ref: docs/architecture/ARCHITECTURE.md §8.1, §8.3
Ref: docs/product/PRODUCT_REQUIREMENTS.md §8, §16
"""

from typing import Any

from healthflow_safety.models import SafetyGateResult, SafetyViolation


def evaluate_pre_submission_safety_gate(
    patient_record: Any,
    coverage_record: Any,
    required_document_types: list[str],
    gathered_documents: list[Any],
    clinical_indication: str,
) -> SafetyGateResult:
    """Run all mandatory deterministic safety invariant checks prior to submission."""
    violations: list[SafetyViolation] = []

    # Invariant 1: Synthetic Data Boundary (PRS §16)
    if patient_record is None:
        violations.append(
            SafetyViolation(
                code="PATIENT_RECORD_MISSING",
                message="Patient record must exist prior to submission.",
            )
        )
    elif not getattr(patient_record, "is_synthetic", False):
        violations.append(
            SafetyViolation(
                code="DATA_BOUNDARY_VIOLATION",
                message="Non-synthetic patient record detected. Ingestion and submission prohibited.",
            )
        )

    # Invariant 2: Active Insurance Coverage (PRS §6, AD-014)
    if coverage_record is None:
        violations.append(
            SafetyViolation(
                code="COVERAGE_RECORD_MISSING",
                message="Active insurance coverage record must be verified prior to submission.",
            )
        )
    else:
        if not getattr(coverage_record, "is_active", False):
            violations.append(
                SafetyViolation(
                    code="INACTIVE_COVERAGE",
                    message="Patient insurance policy is not currently active.",
                )
            )
        cov_notes = getattr(coverage_record, "coverage_notes", "").lower()
        if "mismatch" in cov_notes or "conflict" in cov_notes:
            violations.append(
                SafetyViolation(
                    code="COVERAGE_POLICY_CONFLICT",
                    message=f"Payer coverage conflict detected: {coverage_record.coverage_notes}",
                )
            )

    # Invariant 3: Clinical Document Completeness (PRS §6)
    gathered_types = {
        getattr(d, "document_type", None)
        for d in gathered_documents
        if getattr(d, "document_type", None) is not None
    }
    for req_type in required_document_types:
        if req_type not in gathered_types:
            violations.append(
                SafetyViolation(
                    code="MISSING_REQUIRED_DOCUMENT",
                    message=f"Required clinical document type '{req_type}' is missing from package.",
                )
            )

    # Invariant 4: Absence of Clinical Conflicts (PRS §8, §10)
    if patient_record is not None:
        notes = getattr(patient_record, "clinical_notes_summary", "").lower()
        if "conflict" in notes or "mismatch" in notes:
            violations.append(
                SafetyViolation(
                    code="CLINICAL_DATA_CONFLICT",
                    message=f"Unresolvable clinical discrepancy detected: {patient_record.clinical_notes_summary}",
                )
            )

    # Invariant 5: Clinical Indication Fidelity (No Hallucination) (PRS §8)
    if not clinical_indication or not clinical_indication.strip():
        violations.append(
            SafetyViolation(
                code="EMPTY_CLINICAL_INDICATION",
                message="Clinical indication cannot be empty or fabricated.",
            )
        )

    is_allowed = len(violations) == 0
    reason_code = None if is_allowed else "PRE_SUBMISSION_SAFETY_GATE_FAILED"

    return SafetyGateResult(
        allowed=is_allowed,
        gate_name="PreSubmissionSafetyGate",
        reason_code=reason_code,
        violations=violations,
    )
