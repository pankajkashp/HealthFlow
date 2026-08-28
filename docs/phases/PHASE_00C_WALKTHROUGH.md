# Phase 0C Walkthrough — Architecture Decision Resolution

**Phase:** 0C — Architecture Decision Resolution
**Date Completed:** 2026-08-28
**Specification Authority:** Product Requirements Specification v1.0
**Prior Phase:** Phase 0B — Technical Architecture Specification

---

## Phase Purpose

Phase 0C resolved the five pending architecture decisions identified in Phase 0B
and documented in `docs/architecture/ARCHITECTURE_DECISIONS.md`.

This was a **documentation and decision resolution phase only**.
No application code was written.
No dependencies were installed.
No database schema was created.
No agent implementation was created.
No AWS or infrastructure was configured.

---

## Documents Inspected Before Taking Any Action

| Document | Inspected |
|---|---|
| `docs/product/PRODUCT_REQUIREMENTS.md` | YES |
| `docs/engineering/AI_ENGINEERING_RULES.md` | YES |
| `docs/engineering/CODING_STANDARDS.md` | YES |
| `docs/engineering/NAMING_CONVENTIONS.md` | YES |
| `docs/engineering/DEPENDENCY_POLICY.md` | YES |
| `docs/phases/PHASE_00.md` | YES |
| `docs/architecture/ARCHITECTURE.md` | YES |
| `docs/architecture/ARCHITECTURE_DECISIONS.md` | YES |
| `docs/architecture/REQUIREMENTS_TRACEABILITY.md` | YES |
| `docs/phases/PHASE_00B_WALKTHROUGH.md` | YES |

---

## Decisions Reviewed

| Decision | Prior Status |
|---|---|
| AD-011: Authentication and Authorization Design | PENDING APPROVAL |
| AD-012: Retry Policy for Transient Failures | PENDING APPROVAL |
| AD-013: Workflow State Enumeration and Transition Graph | PENDING APPROVAL |
| AD-014: Agent Tool Contracts — Exact Names and Signatures | PENDING APPROVAL |
| AD-015: Embedding Model Selection for RAG | PENDING APPROVAL |

---

## Decisions Approved

All five pending decisions were resolved. None remain pending.

### AD-011: Authentication and Authorization Design — APPROVED

**Decision:** JWT Bearer Token authentication.

- FastAPI issues signed JWT access tokens upon credential validation.
- All routes accessing workflow data require a valid Bearer token in the `Authorization` header.
- Tokens are stateless; no server-side session store is required.
- Single user role for MVP (doctors and admin staff are not differentiated at the authentication boundary; workflow-state-level permissions are enforced by the safety layer).
- AWS Cognito explicitly not used for MVP.
- Token signing key managed via AWS Secrets Manager (production) or git-ignored environment variable (local development).
- JWT library selection (e.g., PyJWT) is deferred to the implementation phase, per the Dependency Policy.

**Rationale summary:** JWT is stateless (compatible with Fargate/ECS), testable without external services, compatible with FastAPI dependency injection. PRS does not require federated identity or multi-tenant auth at MVP scale.

---

### AD-012: Retry Policy for Transient Failures — APPROVED

**Decision:** Four-category retry classification.

- **Category 1 (read operations — retryable):** `get_patient_record`, `get_insurance_plan`, `get_authorization_requirements`, `get_required_document`, `get_authorization_status`. Max 3 attempts, exponential backoff with jitter (1s base, ×2, max 30s, ±20% jitter).
- **Category 2 (verification reads — retryable):** `verify_authorization_outcome`. Same backoff. Failure after max retries → `ESCALATED`; must never reach `COMPLETED`.
- **Category 3 (submission — NOT directly retryable):** `submit_authorization_request` requires a `get_authorization_status` pre-check before any retry attempt, to prevent duplicate submissions. Max 2 additional attempts after pre-check.
- **Category 4 (non-retryable):** All validation failures, safety gate failures, permission failures. These are deterministic; retrying would produce the same result.

**Invariants:** Every retry re-runs the full safety flow. Retry attempts are audit-logged. Retry must never bypass verification or lead to workflow completion without VerificationProvider CONFIRMED.

---

### AD-013: Workflow State Enumeration and Transition Graph — APPROVED

**Decision:** 12 named explicit workflow states.

| State | Terminal? |
|---|---|
| `INITIATED` | No |
| `GATHERING_INFORMATION` | No |
| `VALIDATING` | No |
| `PREPARING_SUBMISSION` | No |
| `SUBMITTED` | No |
| `MONITORING` | No |
| `FOLLOW_UP_REQUIRED` | No |
| `VERIFYING` | No |
| `ESCALATED` | No (resumable) |
| `COMPLETED` | YES |
| `DENIED` | YES |
| `FAILED` | YES |

**Key constraint:** `COMPLETED` is only reachable from `VERIFYING` via a VerificationProvider CONFIRMED + approved result. No other path leads to `COMPLETED`.

`ESCALATED` is resumable: human input can direct the workflow to `GATHERING_INFORMATION`, `PREPARING_SUBMISSION`, `DENIED`, or `FAILED`.

Full transition graph, transition rules, and prohibited transitions are documented in AD-013 in `ARCHITECTURE_DECISIONS.md`.

---

### AD-014: Agent Tool Contracts — Exact Names and Signatures — APPROVED

**Decision:** 9 finalized agent tool functions.

| Tool | Type | Permission |
|---|---|---|
| `get_patient_record` | Read | `WORKFLOW_READ` |
| `get_insurance_plan` | Read | `WORKFLOW_READ` |
| `get_authorization_requirements` | Read | `WORKFLOW_READ` |
| `get_required_document` | Read | `WORKFLOW_READ` |
| `validate_authorization_package` | Read | `WORKFLOW_READ` |
| `submit_authorization_request` | Mutating | `WORKFLOW_SUBMIT` |
| `get_authorization_status` | Read | `WORKFLOW_READ` |
| `verify_authorization_outcome` | Read | `WORKFLOW_READ` |
| `request_escalation` | Mutating | `WORKFLOW_ESCALATE` |

Each tool has a fully defined input parameter set (names, types, required/optional), output structure, permission code, validation requirements, safety restrictions, source of truth, failure behavior, and retry category.

Key safety decisions embedded in tool contracts:
- Document content is NOT returned to the agent (only an opaque content reference) — prevents LLM reasoning over raw clinical text.
- `verify_authorization_outcome` is the ONLY tool that can authorize the `COMPLETED` state transition.
- `submit_authorization_request` requires `WORKFLOW_SUBMIT` (more restrictive than `WORKFLOW_READ`) and the safety gate must pass before the portal is called.
- `request_escalation` transitions the workflow to `ESCALATED` atomically; the agent cannot continue invoking other tools after this call.

---

### AD-015: Embedding Model Selection for RAG — APPROVED

**Decision:** Amazon Titan Text Embeddings V2.

- **Bedrock model ID:** `amazon.titan-embed-text-v2:0`
- **Embedding dimensions:** 1024
- **pgvector column definition:** `VECTOR(1024)` (fixed at schema creation time)
- **Access:** Via the existing Amazon Bedrock boto3 client — no additional service, library, or API key required.
- **Input token limit:** 8,192 tokens (sufficient for policy document chunks).

Rationale: first-party Bedrock model, no additional dependency, compatible with the locked AWS/Bedrock stack, reproducible embeddings, suitable for English administrative text.

---

## Decisions Still Pending

**None.** All five AD-011 through AD-015 decisions are APPROVED.

---

## Files Created

| File | Purpose |
|---|---|
| `docs/phases/PHASE_00C_WALKTHROUGH.md` | This walkthrough (Phase 0C) |

---

## Files Modified

| File | Changes |
|---|---|
| `docs/architecture/ARCHITECTURE_DECISIONS.md` | Version updated to 1.1; AD-011 through AD-015 resolved from PENDING APPROVAL to APPROVED with full decision text, rationale, alternatives, and impact |
| `docs/architecture/ARCHITECTURE.md` | Version updated to 1.1; §7.2 tool list finalized (removed "illustrative" note, added permission annotations); §11.3 workflow states table added (12 named states); §15.2 RAG pipeline embedding model resolved; §15.5 embedding model section replaced with resolved decision; §16.4 authentication boundary replaced with JWT decision |
| `docs/architecture/REQUIREMENTS_TRACEABILITY.md` | Version updated to 1.1; PRS §6 capability rows updated with AD-014 tool references; PRS §17 pgvector row updated with AD-015; PRS §18 workflow state and verification rows updated with AD-013/AD-014; PRS §22 success criteria rows updated — two previously DEFERRED rows are now SATISFIED |

---

## Files NOT Modified

| File |
|---|
| `docs/product/PRODUCT_REQUIREMENTS.md` |
| `REQUIRMENTS.MD` |
| `docs/engineering/AI_ENGINEERING_RULES.md` |
| `docs/engineering/CODING_STANDARDS.md` |
| `docs/engineering/NAMING_CONVENTIONS.md` |
| `docs/engineering/DEPENDENCY_POLICY.md` |
| `docs/phases/PHASE_00.md` |
| `docs/phases/PHASE_00_WALKTHROUGH.md` |
| `docs/phases/PHASE_00B_WALKTHROUGH.md` |

---

## Commands Executed

```
# Repository inspection before taking action
find . -not -path './.git/*' | sort && git status

# Verification — no source code files
find . -not -path './.git/*' \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) | sort

# Verification — no dependency manifests
find . -not -path './.git/*' \( -name "package.json" -o -name "requirements.txt" -o -name "pyproject.toml" -o -name "setup.py" -o -name "Pipfile" -o -name "poetry.lock" \) | sort

# Verification — PRS unmodified
diff REQUIRMENTS.MD docs/product/PRODUCT_REQUIREMENTS.md && echo "PRS_UNMODIFIED"

# Verification — all 15 decisions present with status sections
grep -c "^## AD-" docs/architecture/ARCHITECTURE_DECISIONS.md
grep "### Status" docs/architecture/ARCHITECTURE_DECISIONS.md | head -20

# Verification — no active PENDING APPROVAL statuses remaining
grep -n "PENDING APPROVAL" docs/architecture/ARCHITECTURE_DECISIONS.md | head -20

# Verification — remaining DEFERRED items are legitimate deferrals
grep -n "DEFERRED TO LATER PHASE" docs/architecture/REQUIREMENTS_TRACEABILITY.md | head -20

# Final repository tree and git status
find . -not -path './.git/*' | sort && git status
```

---

## Verification Results

| Check | Command | Result |
|---|---|---|
| No `.py`/`.ts`/`.tsx`/`.js`/`.jsx` source files | `find` command | ✅ Zero files found |
| No dependency manifests | `find` command | ✅ Zero files found |
| PRS unmodified | `diff REQUIRMENTS.MD docs/product/PRODUCT_REQUIREMENTS.md` | ✅ `PRS_UNMODIFIED` |
| 15 decisions present in ARCHITECTURE_DECISIONS.md | `grep -c "^## AD-"` | ✅ Returns `15` |
| AD-011 through AD-015 all have `### Status` sections | `grep "### Status"` | ✅ 5 status sections found |
| No active PENDING APPROVAL decision status | `grep -n "PENDING APPROVAL"` | ✅ Only 2 lines: line 10 (document format description) and line 22 (format legend) — no decision is in PENDING APPROVAL status |
| Remaining DEFERRED items are legitimate | `grep -n "DEFERRED TO LATER PHASE"` | ✅ 4 remaining deferred items: data labeling (simulated systems spec), simulated system behavior (simulated systems spec), code quality tooling configuration (implementation phase), Docker/AWS configuration (infrastructure phase). None are from the five resolved decisions. |
| Git status: no source code committed | `git status` | ✅ Only 3 modified `.md` documentation files; no source code or dependency files |

---

## Dependencies Added

**None.**

---

## Deviations

None. All five decisions were resolved based on the authoritative documents and the constraints established in Phase 0B.

No architectural decisions were made outside the five explicitly authorized decisions.

The Technology Stack remains unchanged from PRS §17. No new technologies were introduced. The JWT library (e.g., PyJWT) required for AD-011 implementation is explicitly deferred to the implementation phase per the Dependency Policy.

---

## Blockers

None.

The following items remain legitimately deferred to later specification phases. These are not blockers for Phase 0C:

| Item | Deferred To |
|---|---|
| Synthetic data labeling mechanism (exact format) | Simulated systems specification phase |
| Simulated system behavior (deterministic rules) | Simulated systems specification phase |
| Code quality tool configuration (Ruff, MyPy, ESLint, Prettier) | Implementation phase |
| Docker and AWS infrastructure configuration | Infrastructure specification phase |
| JWT library selection (e.g., PyJWT) | Implementation phase (subject to Dependency Policy approval) |
| pgvector schema definition (`VECTOR(1024)`) | Database schema specification phase |
| Strands SDK tool decorator pattern | Implementation phase |
| Embedding model chunk size tuning | RAG ingestion pipeline specification |

---

## Out of Scope

The following were explicitly NOT performed in Phase 0C:

- Frontend implementation
- Backend API implementation
- Agent implementation
- Database schema creation
- Migration files
- AWS Strands configuration
- Amazon Bedrock integration
- Simulated healthcare system implementations
- Authorization workflow logic
- RAG pipeline implementation
- Authentication middleware implementation
- Retry logic implementation
- State machine implementation
- Tool function implementation (as executable code)
- Any source code of any kind
- Docker or infrastructure configuration
- Application dependency installation

---

## Phase Status

**PASS**

All Phase 0C acceptance criteria are met:

- [x] All five decisions (AD-011 through AD-015) have an explicit APPROVED status
- [x] No decision was silently guessed — each decision includes rationale, alternatives considered, and rejected alternatives
- [x] Architecture documentation is internally consistent (AD-011 through AD-015 are reflected in ARCHITECTURE.md where applicable)
- [x] Product Requirements Specification is unmodified (verified with diff → PRS_UNMODIFIED)
- [x] No application source code exists
- [x] No dependencies were added
- [x] Requirements traceability updated and remains valid — two previously DEFERRED rows are now SATISFIED
- [x] No known blocker is hidden
- [x] Walkthrough document created (`docs/phases/PHASE_00C_WALKTHROUGH.md`)
- [x] All verification checks passed
- [x] Git status shows only 3 modified documentation files; no committed source code
