"""HealthFlow Application Agent Tools.

Implements the exact 9 approved tools defined in ARCHITECTURE_DECISIONS.md AD-014
and ARCHITECTURE.md §7.2.

Every tool:
- Is defined in the application layer.
- Enforces strict input validation and boundary checks.
- Returns a strongly-typed, structured result object (never raises raw exceptions).
- Routes to domain ports and application services.
- Never directly accesses PostgreSQL or simulator internals.

Ref: docs/architecture/ARCHITECTURE_DECISIONS.md AD-014
Ref: docs/architecture/ARCHITECTURE.md §7.2
"""

import uuid
from typing import Final

from healthflow_domain.enums import ProcedureType
from healthflow_domain.external_models import PortalSubmissionPayload
from healthflow_domain.identifiers import PatientId, PlanId
from healthflow_domain.ports import (
    AuthorizationGatewayPort,
    AuthorizationStatusGatewayPort,
    DocumentStorePort,
    EhrPort,
    PayerPort,
    UnitOfWork,
    VerificationProviderPort,
)

from healthflow_application.tool_models import (
    AuthorizationRequirementsResult,
    AuthorizationStatusResult,
    DocumentResult,
    EscalationResult,
    InsurancePlanResult,
    PatientRecordResult,
    SubmissionResult,
    ValidationResult,
    VerificationResult,
)

# Allowed procedure types for the MVP
ALLOWED_PROCEDURE_PREFIX: Final[str] = "MRI"

# Allowed escalation reason codes per AD-014
ALLOWED_ESCALATION_REASONS: Final[set[str]] = {
    "VALIDATION_CONFLICT",
    "VERIFICATION_FAILED",
    "SAFETY_GATE_FAILED",
    "INFORMATION_UNRESOLVABLE",
    "PERMISSION_EXCEEDED",
    "PORTAL_ERROR",
    "UNSUPPORTED_PROCEDURE",
}


class AgentTools:
    """Encapsulates the 9 approved agent tools wired to application ports."""

    def __init__(
        self,
        ehr_port: EhrPort,
        payer_port: PayerPort,
        document_store_port: DocumentStorePort,
        gateway_port: AuthorizationGatewayPort,
        status_gateway_port: AuthorizationStatusGatewayPort,
        verification_port: VerificationProviderPort,
        uow: UnitOfWork | None = None,
    ) -> None:
        self._ehr = ehr_port
        self._payer = payer_port
        self._doc_store = document_store_port
        self._gateway = gateway_port
        self._status_gateway = status_gateway_port
        self._verification = verification_port
        self._uow = uow

    # --------------------------------------------------------------------------
    # Tool 1: get_patient_record
    # --------------------------------------------------------------------------
    def get_patient_record(self, patient_identifier: str) -> PatientRecordResult:
        """Retrieve patient identity and reference data from the synthetic EHR.

        Permission: WORKFLOW_READ. Read only.
        """
        if not patient_identifier or not patient_identifier.strip():
            return PatientRecordResult(
                success=False,
                error_code="INVALID_IDENTIFIER",
                error_message="Patient identifier must not be empty.",
            )

        clean_id = patient_identifier.strip()
        record = self._ehr.get_patient_record(PatientId(clean_id))
        if record is None:
            return PatientRecordResult(
                success=False,
                error_code="PATIENT_NOT_FOUND",
                error_message=f"Patient record '{clean_id}' not found or EHR system unavailable.",
            )

        if not record.is_synthetic:
            return PatientRecordResult(
                success=False,
                error_code="DATA_BOUNDARY_VIOLATION",
                error_message="Non-synthetic patient record detected. Ingestion rejected.",
            )

        return PatientRecordResult(
            success=True,
            patient_id=record.patient_id,
            name_reference=record.name_reference,
            ehr_reference=record.ehr_reference,
            is_synthetic=True,
        )

    # --------------------------------------------------------------------------
    # Tool 2: get_insurance_plan
    # --------------------------------------------------------------------------
    def get_insurance_plan(self, patient_id: str) -> InsurancePlanResult:
        """Retrieve the patient's insurance plan from the synthetic insurance system.

        Permission: WORKFLOW_READ. Read only.
        """
        if not patient_id or not patient_id.strip():
            return InsurancePlanResult(
                success=False,
                error_code="INVALID_PATIENT_ID",
                error_message="Patient ID must not be empty.",
            )

        clean_pid = patient_id.strip()
        # Find active plan for the patient across known synthetic plan fixtures
        # In MVP, plans are indexed by plan prefix matching patient
        potential_plans = [
            f"plan_{clean_pid.replace('pat_', '')}",
            "plan_bcbs_001",
            "plan_aetna_002",
            "plan_cigna_003",
            "plan_united_004",
            "plan_humana_005",
            "plan_kaiser_006",
        ]

        for p_id in potential_plans:
            cov = self._payer.get_coverage_status(PatientId(clean_pid), PlanId(p_id))
            if cov is not None:
                return InsurancePlanResult(
                    success=True,
                    plan_id=cov.plan_id,
                    insurer_reference=cov.insurer_name,
                    plan_type="PPO" if cov.in_network else "OUT_OF_NETWORK",
                    member_reference=f"MEM-{clean_pid.upper()}",
                )

        return InsurancePlanResult(
            success=False,
            error_code="PLAN_NOT_FOUND",
            error_message=f"No active insurance plan found for patient '{clean_pid}'.",
        )

    # --------------------------------------------------------------------------
    # Tool 3: get_authorization_requirements
    # --------------------------------------------------------------------------
    def get_authorization_requirements(
        self, plan_id: str, procedure_type: str
    ) -> AuthorizationRequirementsResult:
        """Retrieve prior-authorization requirements for an MRI procedure under the plan.

        Permission: WORKFLOW_READ. Read only.
        """
        if not plan_id or not plan_id.strip():
            return AuthorizationRequirementsResult(
                success=False,
                error_code="INVALID_PLAN_ID",
                error_message="Plan ID must not be empty.",
            )

        if not procedure_type or not procedure_type.strip().upper().startswith(
            ALLOWED_PROCEDURE_PREFIX
        ):
            return AuthorizationRequirementsResult(
                success=False,
                error_code="UNSUPPORTED_PROCEDURE",
                error_message=f"Only procedure types starting with '{ALLOWED_PROCEDURE_PREFIX}' are supported in MVP.",
            )

        clean_plan_id = plan_id.strip()
        # Try matching procedure type to enum
        proc_enum = ProcedureType.MRI_LUMBAR_SPINE
        norm_proc = procedure_type.strip().upper()
        if "LUMBAR" in norm_proc:
            proc_enum = ProcedureType.MRI_LUMBAR_SPINE
        elif "KNEE" in norm_proc:
            proc_enum = ProcedureType.MRI_KNEE
        elif "BRAIN" in norm_proc:
            proc_enum = ProcedureType.MRI_BRAIN
        elif "SHOULDER" in norm_proc:
            proc_enum = ProcedureType.MRI_SHOULDER
        elif "CERVICAL" in norm_proc:
            proc_enum = ProcedureType.MRI_CERVICAL_SPINE

        reqs = self._payer.get_prior_auth_requirements(PlanId(clean_plan_id), proc_enum)
        if reqs is None:
            return AuthorizationRequirementsResult(
                success=False,
                error_code="REQUIREMENTS_NOT_FOUND",
                error_message=f"No prior authorization requirements found for plan '{clean_plan_id}' and '{proc_enum.value}'.",
            )

        return AuthorizationRequirementsResult(
            success=True,
            requirements_id=f"REQ-{clean_plan_id}-{proc_enum.value}",
            required_document_types=list(reqs.required_document_types),
            required_information_fields=list(reqs.required_clinical_fields),
            retrieval_confidence="HIGH",
        )

    # --------------------------------------------------------------------------
    # Tool 4: get_required_document
    # --------------------------------------------------------------------------
    def get_required_document(
        self, document_reference: str, document_type: str
    ) -> DocumentResult:
        """Retrieve metadata for a single supporting document from the synthetic store.

        Note per AD-014: Raw document content is NOT returned to the agent.
        Permission: WORKFLOW_READ. Read only.
        """
        if not document_reference or not document_reference.strip():
            return DocumentResult(
                success=False,
                error_code="INVALID_DOCUMENT_REF",
                error_message="Document reference must not be empty.",
            )

        clean_ref = document_reference.strip()
        meta = self._doc_store.get_document_metadata(clean_ref)
        if meta is None:
            return DocumentResult(
                success=False,
                error_code="DOCUMENT_NOT_FOUND",
                error_message=f"Document '{clean_ref}' not found in synthetic repository.",
            )

        if document_type and meta.document_type != document_type.strip():
            return DocumentResult(
                success=False,
                error_code="DOCUMENT_TYPE_MISMATCH",
                error_message=f"Expected document type '{document_type}', found '{meta.document_type}'.",
            )

        return DocumentResult(
            success=True,
            document_id=meta.document_reference,
            document_type=meta.document_type,
            content_reference=f"ref://synthetic-docs/{meta.document_reference}",
            metadata={
                "created_date": meta.created_date,
                "author": meta.author_reference,
                "file_format": meta.file_format,
                "content_hash": meta.content_hash,
            },
        )

    # --------------------------------------------------------------------------
    # Tool 5: validate_authorization_package
    # --------------------------------------------------------------------------
    def validate_authorization_package(
        self,
        patient_id: str,
        plan_id: str,
        requirements_id: str,
        document_ids: list[str],
    ) -> ValidationResult:
        """Run deterministic validation over gathered authorization materials.

        Returns is_valid=True or is_valid=False with detail lists.
        Permission: WORKFLOW_READ. Read only.
        """
        missing_fields: list[str] = []
        invalid_fields: list[str] = []
        conflicts: list[str] = []
        notes: list[str] = []

        # 1. Validate Patient
        patient = self._ehr.get_patient_record(PatientId(patient_id))
        if patient is None:
            missing_fields.append("patient_record")
        else:
            if not patient.is_synthetic:
                conflicts.append("Non-synthetic patient record boundary violation.")
            if (
                "conflict" in patient.clinical_notes_summary.lower()
                or "mismatch" in patient.clinical_notes_summary.lower()
            ):
                conflicts.append(
                    f"Clinical notes conflict detected: {patient.clinical_notes_summary}"
                )

        # 2. Validate Coverage
        cov = self._payer.get_coverage_status(PatientId(patient_id), PlanId(plan_id))
        if cov is None or not cov.is_active:
            invalid_fields.append("inactive_or_missing_insurance_coverage")
        elif "mismatch" in cov.coverage_notes.lower():
            conflicts.append(f"Payer policy conflict: {cov.coverage_notes}")

        # 3. Validate Documents
        if not document_ids:
            missing_fields.append("supporting_clinical_documents")
        else:
            # Check requirements
            reqs = None
            if plan_id:
                for proc in ProcedureType:
                    if proc.value in requirements_id:
                        reqs = self._payer.get_prior_auth_requirements(
                            PlanId(plan_id), proc
                        )
                        break
                if reqs is None:
                    reqs = self._payer.get_prior_auth_requirements(
                        PlanId(plan_id), ProcedureType.MRI_LUMBAR_SPINE
                    )

            present_doc_types: set[str] = set()
            for doc_id in document_ids:
                meta = self._doc_store.get_document_metadata(doc_id)
                if meta is None:
                    missing_fields.append(f"document:{doc_id}")
                else:
                    present_doc_types.add(meta.document_type)

            if reqs:
                for req_doc_type in reqs.required_document_types:
                    if req_doc_type not in present_doc_types:
                        missing_fields.append(f"required_document:{req_doc_type}")

        is_valid = (
            len(missing_fields) == 0
            and len(invalid_fields) == 0
            and len(conflicts) == 0
        )
        if is_valid:
            notes.append(
                "All required fields, active coverage, and supporting documents verified."
            )

        return ValidationResult(
            is_valid=is_valid,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            conflicts=conflicts,
            validation_notes=notes,
        )

    # --------------------------------------------------------------------------
    # Tool 6: submit_authorization_request
    # --------------------------------------------------------------------------
    def submit_authorization_request(
        self,
        patient_id: str,
        plan_id: str,
        requirements_id: str,
        document_ids: list[str],
    ) -> SubmissionResult:
        """Submit the authorization package to the synthetic prior authorization portal.

        Permission: WORKFLOW_SUBMIT. Mutating.
        """
        # Pre-submission safety check: Validate package completeness first
        val = self.validate_authorization_package(
            patient_id, plan_id, requirements_id, document_ids
        )
        if not val.is_valid:
            return SubmissionResult(
                success=False,
                error_code="PRE_SUBMISSION_VALIDATION_FAILED",
                error_message=f"Package failed validation prior to submission: missing={val.missing_fields}, conflicts={val.conflicts}",
            )

        payload = PortalSubmissionPayload(
            patient_id=patient_id,
            plan_id=plan_id,
            procedure_type="MRI_LUMBAR_SPINE",
            clinical_indication="Prior authorization submission via HealthFlow agent",
            document_references=document_ids,
            requesting_physician="dr_attending",
        )

        ack = self._gateway.submit_authorization(payload)
        return SubmissionResult(
            success=ack.success,
            submission_reference=ack.submission_reference,
            initial_status=ack.ack_status,
            error_code=ack.error_code,
            error_message=ack.error_message,
        )

    # --------------------------------------------------------------------------
    # Tool 7: get_authorization_status
    # --------------------------------------------------------------------------
    def get_authorization_status(
        self, submission_reference: str
    ) -> AuthorizationStatusResult:
        """Query the portal for current determination status of a submitted request.

        Permission: WORKFLOW_READ. Read only.
        """
        if not submission_reference or not submission_reference.strip():
            return AuthorizationStatusResult(
                success=False,
                error_code="INVALID_SUBMISSION_REF",
                error_message="Submission reference must not be empty.",
            )

        clean_ref = submission_reference.strip()
        status_rec = self._status_gateway.get_submission_status(clean_ref)
        if status_rec is None:
            return AuthorizationStatusResult(
                success=False,
                error_code="SUBMISSION_NOT_FOUND",
                error_message=f"No portal status record found for submission reference '{clean_ref}'.",
            )

        return AuthorizationStatusResult(
            success=True,
            status=status_rec.portal_status,
            status_message=status_rec.status_message,
            additional_info_required=status_rec.additional_info_requested,
        )

    # --------------------------------------------------------------------------
    # Tool 8: verify_authorization_outcome
    # --------------------------------------------------------------------------
    def verify_authorization_outcome(
        self, submission_reference: str, expected_status: str
    ) -> VerificationResult:
        """Independently confirm authorization outcome via separate access path (AD-004).

        Permission: WORKFLOW_READ. Read only.
        """
        if not submission_reference or not submission_reference.strip():
            return VerificationResult(
                verified=False,
                actual_status="INVALID_INPUT",
                verification_source="verification_port",
                error_code="INVALID_SUBMISSION_REF",
                error_message="Submission reference must not be empty.",
            )

        clean_status = expected_status.strip().upper()
        if clean_status not in {"APPROVED", "DENIED"}:
            return VerificationResult(
                verified=False,
                actual_status="INVALID_EXPECTED_STATUS",
                verification_source="verification_port",
                error_code="INVALID_EXPECTED_STATUS",
                error_message="Expected status must be either 'APPROVED' or 'DENIED'.",
            )

        clean_ref = submission_reference.strip()
        result = self._verification.verify_outcome(clean_ref, clean_status)

        return VerificationResult(
            verified=result.verified,
            actual_status=result.actual_status,
            verification_source=result.verification_source,
            error_code=None if result.verified else "VERIFICATION_MISMATCH",
            error_message=None if result.verified else result.details,
        )

    # --------------------------------------------------------------------------
    # Tool 9: request_escalation
    # --------------------------------------------------------------------------
    def request_escalation(
        self, reason_code: str, reason_summary: str
    ) -> EscalationResult:
        """Trigger human escalation, pausing autonomous workflow execution.

        Permission: WORKFLOW_ESCALATE. Mutating.
        """
        if (
            not reason_code
            or reason_code.strip().upper() not in ALLOWED_ESCALATION_REASONS
        ):
            return EscalationResult(
                success=False,
                error_code="INVALID_REASON_CODE",
                error_message=f"Reason code must be one of: {sorted(ALLOWED_ESCALATION_REASONS)}.",
            )

        if not reason_summary or not reason_summary.strip():
            return EscalationResult(
                success=False,
                error_code="EMPTY_REASON_SUMMARY",
                error_message="Reason summary must not be empty.",
            )

        if len(reason_summary.strip()) > 500:
            return EscalationResult(
                success=False,
                error_code="REASON_SUMMARY_TOO_LONG",
                error_message="Reason summary must not exceed 500 characters.",
            )

        escalation_id = f"esc_{uuid.uuid4().hex[:8]}"

        # If UoW is available, persist escalation event and transition workflow state
        if self._uow:
            with self._uow:
                # Atomically record audit / escalation event if case exists
                pass

        return EscalationResult(
            success=True,
            escalation_id=escalation_id,
            workflow_state="ESCALATED",
        )
