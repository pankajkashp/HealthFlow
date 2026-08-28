# HealthFlow — Architecture Decisions

**Version:** 1.1
**Phase:** Updated in Phase 0C — Architecture Decision Resolution
**Authority:** Product Requirements Specification v1.0

This document records significant architectural decisions made during Phase 0B and resolved in Phase 0C.

Each decision is made only where the Product Requirements Specification and the approved architecture
provide sufficient grounds. Decisions that cannot be made without additional information are marked **PENDING APPROVAL**.

---

## Decision Format

Each decision contains:
- **Decision:** The choice made.
- **Reason:** Why this choice was made, grounded in requirements.
- **Alternatives Considered:** Other options that were evaluated.
- **Why Rejected:** Why the alternatives were not chosen.
- **Impact:** What this decision affects.
- **Status:** APPROVED or PENDING APPROVAL.

---

## AD-001: Clean Architecture with Ports and Adapters

**Decision:**
HealthFlow uses Clean Architecture organized into Domain, Application, Infrastructure,
Safety, and Agent layers, with Ports and Adapters at infrastructure boundaries.

**Reason:**
The Product Requirements Specification explicitly requires:
- clean architecture (§18)
- separation of concerns (§18)
- dependency inversion (§18)
- ports and adapters (§18)
- testability (§18)
- loose coupling (§18)
- business logic independent of infrastructure (§18)

**Alternatives Considered:**
- Layered architecture without strict port interfaces (e.g., direct repository calls in application code)
- Microservices-per-domain-area

**Why Rejected:**
- Layered without ports: violates the requirement for dependency inversion and makes infrastructure replacement difficult.
- Microservices: over-engineering for MVP; requirements do not justify the operational complexity;
  the scalability requirement (§20) is achievable within a modular monolith at MVP scale.

**Impact:**
- Defines directory structure for packages/
- Defines dependency direction rules
- Defines interface/protocol requirements at layer boundaries

**Status:** APPROVED

---

## AD-002: The Agent Is a Controlled Reasoning Component, Not the Source of Truth

**Decision:**
The AI agent (Claude via Strands) reasons over structured context and invokes authorized
application-layer tool functions. It does not hold state, access the database, or
access external systems directly. It cannot declare completion.

**Reason:**
The Product Requirements Specification explicitly states:
- The agent cannot say DONE; the environment must prove DONE (§7)
- The agent must NOT be the database, persistent state, or source of truth (§19)
- The LLM must not receive unrestricted database, filesystem, network, or external-system access (§19)
- The agent must operate through controlled application tools and services (§6)

**Alternatives Considered:**
- Giving the agent direct database read access for context
- Allowing the agent to call external systems through a shared HTTP client
- Trusting the agent's tool response as proof of action success

**Why Rejected:**
- All three alternatives directly violate explicit Product Requirements Specification requirements.

**Impact:**
- Agent tool functions must be defined at the application layer
- All database and external-system access routes through infrastructure adapters
- Independent verification is a mandatory step after critical actions

**Status:** APPROVED

---

## AD-003: Safety Controls Are Deterministic Code, Not LLM Prompts

**Decision:**
Safety controls (input validation, permission checks, safety gates, independent verification)
are implemented in deterministic application/domain/safety code. They are not implemented
solely through LLM prompting.

**Reason:**
- LLM outputs are not deterministic and cannot be relied upon for safety enforcement.
- Product Requirements Specification §9 states: "The LLM must not be allowed to bypass deterministic validation."
- Product Requirements Specification §7 requires independent verification using an authoritative source.
- Product Requirements Specification §11 requires permission checks the agent cannot bypass.

**Alternatives Considered:**
- Using system prompts alone to constrain agent behavior
- Using a "judge" LLM call to validate another LLM call

**Why Rejected:**
- System prompts: Not deterministic; LLMs can be induced to ignore prompt instructions;
  not acceptable for healthcare administrative workflows.
- Judge LLM: Still non-deterministic; adds latency; does not satisfy the requirement for
  deterministic validation.

**Impact:**
- `packages/safety` implements deterministic controls
- Safety controls run before every significant action
- Safety controls cannot be bypassed by the agent or any other layer

**Status:** APPROVED

---

## AD-004: Independent Verification Uses a Logically Separate Access Path

**Decision:**
The VerificationProvider port uses an access path that is logically independent from
the action that produced the claimed result (e.g., a different API endpoint or query
on the authoritative external system, not a re-read of the same response).

**Reason:**
Product Requirements Specification §12 states:
"The verification mechanism must be logically independent from the action that produced
the claimed result."
"A tool response claiming success is insufficient by itself."

**Alternatives Considered:**
- Re-reading the same tool response as verification
- Using a polling call on the same gateway endpoint used for submission

**Why Rejected:**
- Re-reading the same response: Not independent; a failed submission could return a stale
  success response.
- Same endpoint polling: Acceptable only if the status query is genuinely independent of
  the submit call. This will be validated in the simulated systems specification.

**Impact:**
- VerificationProvider port is defined separately from AuthorizationGateway
- The simulated authorization portal must support an independent status query path
- No workflow may complete without a successful VerificationProvider result

**Status:** APPROVED

---

## AD-005: Workflow State Is Explicit and Persisted in PostgreSQL

**Decision:**
Workflow state is represented as an explicit, named enumeration of states. Every state
transition is persisted to PostgreSQL immediately. The workflow can be resumed from
the last persisted state after any interruption.

**Reason:**
Product Requirements Specification §18 requires "explicit workflow state."
The requirements also require observability (§14), auditability (§21), and the ability
to monitor workflow progress (§22 — success criterion #7).

Implicit or in-memory-only state would make recovery, auditability, and observability impossible.

**Alternatives Considered:**
- In-memory state machine with periodic checkpointing
- Event sourcing as the primary state representation

**Why Rejected:**
- In-memory only: Cannot survive process restart; violates recovery and auditability requirements.
- Event sourcing: Not required by the specification; adds significant implementation complexity;
  the requirements are satisfied by an explicit state table with an audit log.

**Impact:**
- Database schema must include workflow state tables (schema defined in a later phase)
- Every state transition produces an audit record
- The infrastructure layer manages state persistence atomically

**Status:** APPROVED

---

## AD-006: Synthetic Healthcare Systems Are Accessed Through Port Interfaces

**Decision:**
All simulated external systems (synthetic EHR, synthetic insurance, synthetic policy,
synthetic documents, synthetic authorization portal) are accessed through domain port
interfaces. The application layer calls ports. Infrastructure adapters implement ports.

**Reason:**
- Ports and adapters is explicitly required (Product Requirements Specification §18).
- This allows simulated systems to be replaced with real systems (in future phases)
  without changing the application layer.
- Testability: ports can be mocked for unit tests without running the simulated systems.

**Alternatives Considered:**
- Direct calls from the application layer to simulated system clients
- Embedding simulated system behavior inline in application code

**Why Rejected:**
- Direct calls: Violates dependency inversion; makes the application layer dependent on infrastructure details; breaks testability.
- Inline behavior: Makes the simulation inseparable from application logic; impossible to test independently.

**Impact:**
- Port interfaces are defined in `packages/domain`
- Adapter implementations are in `packages/infrastructure`
- The application layer imports port interfaces, not adapter implementations

**Status:** APPROVED

---

## AD-007: RAG-Based Policy Retrieval via PolicyProvider Port

**Decision:**
Prior-authorization policy requirements are retrieved using RAG over the synthetic policy
repository, mediated by the PolicyProvider port. Policy content is informational input
to deterministic validation rules, not a binding oracle.

**Reason:**
- The requirements specify a synthetic policy/requirements repository (§13).
- pgvector is in the locked technology stack (§17) — designed specifically for vector similarity search.
- Policy documents are inherently unstructured text, making semantic retrieval appropriate.
- Policy results must be informational (not directly authoritative) to prevent LLM hallucination
  of policy requirements.

**Alternatives Considered:**
- Structured policy database (SQL tables of rules)
- Hard-coded policy rules in domain code

**Why Rejected:**
- Structured SQL: May be appropriate for some rules but cannot represent the full
  complexity of insurance policy requirements. The specification names a policy repository,
  implying document-like content.
- Hard-coded: Not generalizable; changes require code deployment; does not represent
  a realistic simulation of a policy retrieval system.

**Impact:**
- pgvector extension must be enabled in PostgreSQL
- An offline policy ingestion pipeline must be created (defined in a later phase)
- PolicyProvider port abstracts all RAG complexity from the application layer
- RAG results must be treated as informational, not authoritative

**Status:** APPROVED

---

## AD-008: API Versioning via URL Path Prefix

**Decision:**
The FastAPI API uses URL path versioning: `/api/v1/...`

**Reason:**
- Allows non-breaking API evolution.
- Simple to implement with FastAPI routers.
- Compatible with the REST style required for the frontend-to-API boundary.

**Alternatives Considered:**
- Header-based versioning (e.g., `Accept: application/vnd.healthflow.v1+json`)
- No versioning at MVP

**Why Rejected:**
- Header-based: More complex for frontend clients and API gateways; less discoverable.
- No versioning: The specification anticipates future workflows (§20), which will likely
  require API changes. Starting without versioning creates technical debt immediately.

**Impact:**
- All API routes are prefixed with `/api/v1/`
- Future API versions may be introduced as `/api/v2/` without breaking existing clients

**Status:** APPROVED

---

## AD-009: Monorepo Structure with packages/ Separation

**Decision:**
HealthFlow uses a monorepo with clear package separation under `packages/`, `apps/`, and `services/`.
Python packages share the monorepo. The TypeScript frontend is in `apps/web`.

**Reason:**
- The directory structure is established in Phase 00 and is the approved repository structure.
- Package separation enforces the dependency direction rules: `packages/domain` cannot import
  from `packages/infrastructure` because they are separate installable packages.
- This structure enables clear contract testing between packages.

**Alternatives Considered:**
- Single `src/` directory with modules
- Separate repositories per service

**Why Rejected:**
- Single `src/`: Does not enforce dependency direction at the package manager level;
  accidental cross-layer imports are harder to detect.
- Separate repositories: Over-engineering for MVP; increases CI complexity; the team size
  and workflow do not justify separate repositories.

**Impact:**
- Each `packages/` directory will have its own Python package manifest in a later phase
- Dependency direction can be enforced by package manager constraints

**Status:** APPROVED

---

## AD-010: AWS Services Selection for Production Deployment

**Decision:**
The following AWS services are designated for their purposes in the HealthFlow architecture.
Implementation is deferred to the infrastructure specification phase.

| Service              | Purpose                                    |
|----------------------|--------------------------------------------|
| Amazon Bedrock       | Claude LLM access; embedding generation    |
| ECS/Fargate          | Container runtime for `apps/api` and `services/agent` |
| RDS PostgreSQL       | Managed PostgreSQL with pgvector           |
| S3                   | Policy document storage (source for RAG ingestion) |
| Secrets Manager      | Runtime secret retrieval                   |
| CloudWatch           | Operational logging and monitoring         |
| IAM                  | Least-privilege role-based access control  |
| GitHub Actions       | CI/CD pipeline                             |

**Reason:**
The Product Requirements Specification §17 lists these as potential AWS services.
This decision designates which services are planned for the MVP, based on the
architecture needs identified in Phase 0B.

**Alternatives Considered:**
- Self-managed PostgreSQL on EC2 instead of RDS
- Different container orchestration (EKS)

**Why Rejected:**
- Self-managed PostgreSQL: Higher operational burden; RDS provides managed pgvector
  support and backup without additional work.
- EKS: Over-engineering for MVP scale; Fargate is simpler to operate.

**Impact:**
- Infrastructure specification phase must configure these services
- IAM roles must implement least privilege per Security Architecture (Section 19)
- Secrets Manager integration must be implemented before production deployment

**Status:** APPROVED (services designated; configuration is PENDING IMPLEMENTATION)

---

## AD-011: Authentication and Authorization Design

### Status

APPROVED

### Decision

The HealthFlow MVP API uses **JWT Bearer Token** authentication.

- The FastAPI application (`apps/api`) issues signed JWT access tokens upon successful credential validation.
- All API routes that access HealthFlow data require a valid Bearer token in the `Authorization` header.
- Tokens are stateless: no server-side session store is required.
- Token signing uses a secret key stored in AWS Secrets Manager (production) or an environment variable (local development, git-ignored).
- Token expiry is short (recommended: 30–60 minutes for MVP). Refresh token strategy is deferred to a later phase.
- **Single user role for MVP:** The PRS identifies doctors and healthcare administrative staff as users but does not differentiate their permissions at the authorization level. Both user types can initiate and monitor workflows. The safety/permission layer (not the authentication layer) governs what actions are permitted in a given workflow state.
- Authentication is enforced at the API layer via a FastAPI dependency. Routes that do not enforce this dependency are a violation of architectural rules.
- The authenticated user identity is passed as a typed value to the application layer; it is never passed as a raw string through business logic.
- AWS Cognito is explicitly **not** used for MVP. It is a valid future-phase upgrade path if multi-tenant user management or federated identity is required.
- The decision to use JWT does not modify the locked technology stack (FastAPI + Pydantic are used for token validation middleware; no new framework is added).

### Rationale

- The PRS requires least privilege (§11), security (§21), and auditability (§21), but does not specify a mechanism.
- JWT Bearer tokens are stateless, fit naturally with Fargate/ECS (no sticky sessions required), are testable without external services, and are compatible with FastAPI dependency injection without adding a new library (PyJWT is the implementation library; its selection is deferred to the implementation phase to comply with the dependency policy).
- A session-based mechanism would require a session store (Redis or PostgreSQL sessions), adding operational complexity that is not justified for the MVP.
- AWS Cognito adds a managed external service dependency that is not required at MVP scale and would increase the setup cost for local development and testing.
- A single authenticated-user role satisfies the MVP requirements; the PRS does not define role-based permissions that require differentiation at the authentication boundary.

### Alternatives Considered

- AWS Cognito (managed identity provider, OAuth 2.0 / OIDC)
- Session-based authentication with server-side session store
- API Key authentication (no user identity)
- OAuth 2.0 with an external identity provider

### Rejected Alternatives

- **AWS Cognito:** Adds a required external managed service for local development; over-engineering for MVP scale and single-organization use; PRS does not require federated identity. Valid future-phase upgrade.
- **Session-based:** Requires a session store (additional infrastructure); does not work cleanly with stateless ECS/Fargate without sticky routing; more complex to test.
- **API Key:** Provides no user identity; cannot support auditability by user (PRS §21 requires auditability); insufficient for a healthcare administrative system.
- **OAuth 2.0 + external IDP:** No external identity provider is established or required by the PRS; adds external service dependency; over-engineering for MVP.

### Architectural Impact

- `apps/api`: All routes that access workflow data must declare the authentication dependency. Unauthenticated routes (e.g., health check) are the explicit exception, not the default.
- `packages/application`: Receives the authenticated user identity as a typed value from the API layer.
- `packages/safety`: Permission checks receive the authenticated user identity; the single-role MVP permits any authenticated user to initiate and monitor workflows.
- `docs/architecture/ARCHITECTURE.md` §16.4 is updated to reflect this decision.

### Requirements Impact

- PRS §21 (security: least privilege, auditability, explicit permissions): JWT identity enables audit trail per user.
- PRS §11 (permissions): Authentication is the prerequisite for permission enforcement.
- No requirements are modified.

### Implementation Impact

- The JWT library (e.g., PyJWT) must be approved and added under the Dependency Policy before implementation.
- Token signing key must be managed via Secrets Manager; its name/path will be defined in the environment specification.
- Refresh token behavior and token rotation are deferred to a post-MVP phase.

---

## AD-012: Retry Policy for Transient Failures

### Status

APPROVED

### Decision

The retry policy classifies all agent tool operations into one of four categories and applies different retry behavior to each.

#### Category 1: Safe-to-Retry Read Operations

Operations: `get_patient_record`, `get_insurance_plan`, `get_authorization_requirements`, `get_required_document`, `get_authorization_status`.

- **Retryable:** Yes — these are idempotent read operations. Retrying does not change system state.
- **Maximum attempts:** 3 (1 initial + 2 retries).
- **Backoff:** Exponential with jitter. Base delay: 1 second. Multiplier: 2. Maximum delay per attempt: 30 seconds. Jitter: ±20% of the calculated delay.
- **Failure after max attempts:** The tool returns a structured failure result. The workflow transitions to `ESCALATED` state if the failure is on a critical path (e.g., patient not found after all retries during `GATHERING_INFORMATION`). Non-critical path failures (e.g., optional status poll) may stay in `MONITORING`.
- **Safety gate:** Not required for read retries. No state mutation occurs.

#### Category 2: Verification Read Operations

Operation: `verify_authorization_outcome`.

- **Retryable:** Yes — verification is a read operation and is idempotent.
- **Maximum attempts:** 3.
- **Backoff:** Same as Category 1.
- **Failure after max attempts:** The tool returns NOT-CONFIRMED. Workflow transitions to `ESCALATED`. Verification failure must never allow the workflow to reach `COMPLETED`.

#### Category 3: Submission (Write Operation — Non-Retryable Without Pre-Check)

Operation: `submit_authorization_request`.

- **Retryable:** NOT directly retryable. A duplicate submission without checking current state could create duplicate authorization requests.
- **Pre-check required:** Before any retry of a submission, the system MUST first call `get_authorization_status` to determine whether the prior attempt was actually processed.
  - If status shows the submission was already received: Do NOT re-submit. Continue from the acknowledged submission reference.
  - If status confirms no submission exists: A re-submission may proceed, with all safety gates re-running before the retry attempt.
- **Maximum re-submission attempts after pre-check:** 2 additional attempts.
- **Backoff:** Same exponential backoff as Category 1.
- **Failure after max attempts:** Workflow transitions to `ESCALATED`.

#### Category 4: Non-Retryable Operations

Operations: All validation failures, all safety gate failures, all permission failures.

- **Retryable:** NO.
- **Reason:** These are deterministic failures. Retrying without changing the underlying data or permissions would produce the same result. They indicate a problem that requires data correction or human intervention, not a transient error.
- **On failure:** Return structured failure result. Agent reasons about whether more information can be gathered (validation failure) or triggers escalation (safety gate / permission failure).

#### Escalation (write operation)

Operation: `request_escalation`.

- **Retryable:** Not applicable — if the escalation call itself fails transiently, it is retried as a Category 1 read (the escalation record is created; idempotency is enforced by the application layer using the workflow ID).

#### Invariants — Retry Must Never:

- Bypass permission checks (every retry attempt re-runs the full safety flow).
- Bypass deterministic validation.
- Bypass safety gates.
- Mark the workflow as complete without a verified VerificationProvider CONFIRMED result.
- Submit a duplicate request without a status pre-check.

#### Observability

Every retry attempt must be recorded in the audit log with: attempt number, tool name, failure reason, delay applied.

### Rationale

- The PRS requires auditability (§21), reliability, and the DONE principle (§7). The retry policy must not produce silent state ambiguity.
- The submission pre-check pattern (check-before-retry) prevents duplicate submissions without requiring the simulated authorization portal to provide idempotency keys at this stage.
- Deterministic failure categories (validation, safety gate, permission) are explicitly excluded from retry because retrying them would be semantically incorrect — they represent policy violations, not transient errors.
- Exponential backoff with jitter is a standard approach that prevents thundering herd conditions without adding additional library dependencies at the architecture level.

### Alternatives Considered

- Uniform retry with fixed delay for all operations
- No retry policy (fail-fast on all errors)
- Idempotency key approach (require the authorization portal to deduplicate submissions)

### Rejected Alternatives

- **Uniform retry:** Dangerous for write operations (duplicate submissions); too simple for a healthcare administrative system.
- **Fail-fast:** Would produce unnecessary escalations for transient network errors on read operations, dramatically increasing human intervention rate. PRS §10 states human approval must not be required for every routine step.
- **Idempotency keys:** A valid approach, but requires simulated portal API contract definition first. This is deferred to the simulated systems specification phase. The pre-check pattern achieves safety without this dependency.

### Architectural Impact

- Retry logic is implemented in the application layer (within tool functions), not in the infrastructure adapters, so that safety gates are always re-run on retry.
- Infrastructure adapters return structured failure results with an `is_transient` flag to allow the application layer to classify the error.
- `docs/architecture/ARCHITECTURE.md` §20 (Error and Failure Architecture) is updated to reflect this policy.

### Requirements Impact

- PRS §10: Human escalation — retry policy reduces unnecessary escalations for transient errors.
- PRS §7: DONE principle — retry invariants enforce that verification is never bypassed.
- No requirements are modified.

### Implementation Impact

- The retry parameters (max attempts: 3, base delay: 1s, multiplier: 2, max delay: 30s) are configuration values, not hard-coded constants, to allow tuning based on measured performance in the benchmark phase.
- The specific retry library (if any) must be approved under the Dependency Policy. Python's standard `time.sleep` and a simple retry loop are sufficient; no retry framework is required.

---

## AD-013: Workflow State Enumeration and Transition Graph

### Status

APPROVED

### Decision

The MRI prior-authorization workflow has exactly **12 named states** as defined below.

#### State Definitions

| State | Description | Terminal? |
|---|---|---|
| `INITIATED` | Authorization case created; goal received; agent initialized. Initial state. | No |
| `GATHERING_INFORMATION` | Agent is retrieving patient record, insurance plan, authorization requirements, and required documents. | No |
| `VALIDATING` | Deterministic validation of gathered information is running. | No |
| `PREPARING_SUBMISSION` | Authorization submission package is being assembled; pre-submission safety gate is running. | No |
| `SUBMITTED` | Request successfully submitted to the authorization portal; submission reference received. | No |
| `MONITORING` | Agent is polling the authorization portal for a decision. | No |
| `FOLLOW_UP_REQUIRED` | Insurer has requested additional information; agent is gathering supplementary data. | No |
| `VERIFYING` | Independent verification of the claimed final outcome is in progress. | No |
| `ESCALATED` | Human escalation triggered; workflow paused pending human input. Resumable. | No |
| `COMPLETED` | Final state. Independent verification confirmed successful authorization. Only reachable from `VERIFYING`. | YES |
| `DENIED` | Final state. Authorization denied after verification and/or human review. | YES |
| `FAILED` | Final state. Unrecoverable error — exhausted retries or irresolvable system failure. | YES |

#### Transition Graph

```
INITIATED
    ↓ (always)
GATHERING_INFORMATION
    ↓ (information sufficient)     → VALIDATING
    ↓ (information unresolvable)   → ESCALATED

VALIDATING
    ↓ (validation PASS)            → PREPARING_SUBMISSION
    ↓ (validation FAIL, retrievable missing info) → GATHERING_INFORMATION
    ↓ (validation FAIL, conflict/unresolvable)    → ESCALATED

PREPARING_SUBMISSION
    ↓ (safety gate PASS + submission accepted)    → SUBMITTED
    ↓ (safety gate FAIL)           → ESCALATED
    ↓ (submission failure, retries exhausted)     → ESCALATED

SUBMITTED
    ↓ (always)                     → MONITORING

MONITORING
    ↓ (status: approved or denied) → VERIFYING
    ↓ (status: additional info)    → FOLLOW_UP_REQUIRED
    ↓ (status: unexpected/irresolvable) → ESCALATED

FOLLOW_UP_REQUIRED
    ↓ (additional info gathered)   → VALIDATING
    ↓ (additional info unresolvable) → ESCALATED

VERIFYING
    ↓ (verified: approved)         → COMPLETED  ✦ TERMINAL
    ↓ (verified: denied)           → DENIED     ✦ TERMINAL
    ↓ (verification NOT CONFIRMED) → ESCALATED
    ↓ (verification error, retries exhausted) → ESCALATED

ESCALATED
    ↓ (human resolves: continue gathering) → GATHERING_INFORMATION
    ↓ (human resolves: retry submission)   → PREPARING_SUBMISSION
    ↓ (human resolves: deny)               → DENIED    ✦ TERMINAL
    ↓ (human resolves: abandon)            → FAILED    ✦ TERMINAL

COMPLETED  ✦ TERMINAL — no further transitions permitted
DENIED     ✦ TERMINAL — no further transitions permitted
FAILED     ✦ TERMINAL — no further transitions permitted
```

#### Transition Rules

1. A transition may only occur if the application layer validates the preconditions for that transition.
2. Every transition is persisted to PostgreSQL atomically before the agent is notified.
3. Every transition produces an immutable audit record.
4. `COMPLETED` is only reachable from `VERIFYING` with a VerificationProvider result of CONFIRMED + approved. No other path leads to `COMPLETED`.
5. Re-entry to `PREPARING_SUBMISSION` from `ESCALATED` must re-run all safety gates before the submission attempt.
6. Cancelled states are explicitly not in scope for the MVP. The PRS does not specify a cancellation workflow.

#### Prohibited Transitions

- Any state → `COMPLETED` except `VERIFYING` → `COMPLETED` (via VerificationProvider CONFIRMED approved).
- `COMPLETED` → any state.
- `DENIED` → any state.
- `FAILED` → any state.
- Any state → `SUBMITTED` except `PREPARING_SUBMISSION` → `SUBMITTED`.
- Skipping the `VERIFYING` state before reaching `COMPLETED`.

### Rationale

- PRS §18 requires explicit workflow state. PRS §7 requires that DONE is proven by the environment. These constraints directly determine the required states and the prohibition on bypassing `VERIFYING`.
- The 12 states are the minimum set required to represent every distinct behavioral phase described in PRS §6 (14 capabilities) and §22 (12 success criteria).
- `CANCELLED` is not included because the PRS does not describe a cancellation workflow for the MVP.
- `ESCALATED` is a resumable state (not a terminal state) because PRS §10 requires that humans can resolve escalations and the workflow continues.

### Alternatives Considered

- Finer-grained states (one state per agent capability step, e.g., separate states for `PATIENT_IDENTIFICATION`, `INSURANCE_VERIFICATION`, etc.)
- Coarser states (e.g., collapsing all information-gathering into a single `IN_PROGRESS` state)

### Rejected Alternatives

- **Finer-grained states:** Adds 5+ states without adding behavioral distinction. The agent makes multiple tool calls within `GATHERING_INFORMATION` autonomously. Each tool call is an agent action, not a workflow state transition. The workflow state represents a phase of the authorization process, not every tool call.
- **Coarser states:** A single `IN_PROGRESS` state fails to support the observability requirement (PRS §14) and makes it impossible to resume a specific phase after an interruption (violates recovery requirement of AD-005).

### Architectural Impact

- Domain layer (`packages/domain`): Defines the 12 states and the permitted transition map as domain concepts.
- Application layer (`packages/application`): Enforces transition preconditions before persisting any transition.
- Infrastructure layer (`packages/infrastructure`): Persists state atomically; creates audit record per transition.
- `docs/architecture/ARCHITECTURE.md` §11 is updated to reflect the resolved state definitions.

### Requirements Impact

- PRS §6 (core agent behavior — 14 capabilities): All capabilities are covered by the state model.
- PRS §7 (DONE principle): `COMPLETED` is only reachable via `VERIFYING`.
- PRS §14 (observability): Every transition is audited.
- No requirements are modified.

### Implementation Impact

- Database schema must include a `workflow_state` column and a `workflow_state_history` table.
- State and transition definitions must have automated tests in `tests/safety` and `tests/unit`.
- Exact Python type representation (e.g., `StrEnum`, `Enum`) is deferred to the implementation phase.

---

## AD-014: Agent Tool Contracts — Exact Names and Signatures

### Status

APPROVED

### Decision

The MRI prior-authorization MVP exposes exactly **9 agent tools**. Tool names follow `snake_case` per `docs/engineering/NAMING_CONVENTIONS.md`.

All tools are defined in `packages/application` and invoked by the agent via the Strands SDK.
All tools route through the full safety flow (input validation → permission check → business-rule validation → safety gate → action → structured result).
The agent never receives raw exceptions. All failures are returned as structured result objects.

---

#### Tool 1: `get_patient_record`

**Purpose:** Retrieve patient identity and reference data from the synthetic EHR.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `patient_identifier` | `str` | Yes | The patient identifier provided by the user at workflow initiation. Must be non-empty. |

**Output structure:**
```
PatientRecordResult
  success: bool
  patient_id: str | None          # Internal synthetic patient ID
  name_reference: str | None      # Opaque display reference (not a real name for audit logs)
  ehr_reference: str | None       # Synthetic EHR record reference
  is_synthetic: bool              # Must be True; enforcement prevents real data ingestion
  error_code: str | None          # Present when success=False
  error_message: str | None
```

**Allowed caller:** Agent only (via Strands SDK tool invocation).

**Permission required:** `WORKFLOW_READ` on the active authorization case.

**Validation:** `patient_identifier` must be non-empty and match the format defined in the synthetic data specification.

**Safety restrictions:** `is_synthetic` must be `True` on the returned record. If `False`, the tool returns a failure; the workflow escalates.

**Source of truth:** Synthetic EHR (PatientRepository port).

**Failure behavior:** Returns `success=False` with `error_code` for: patient not found, EHR unavailable (transient — retryable), invalid identifier format (non-retryable).

**Operation type:** Read only.

---

#### Tool 2: `get_insurance_plan`

**Purpose:** Retrieve the patient's insurance plan from the synthetic insurance system.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `patient_id` | `str` | Yes | Internal synthetic patient ID from `get_patient_record`. |

**Output structure:**
```
InsurancePlanResult
  success: bool
  plan_id: str | None             # Synthetic insurance plan ID
  insurer_reference: str | None   # Opaque insurer identifier
  plan_type: str | None           # Plan category (e.g., HMO, PPO — synthetic)
  member_reference: str | None    # Synthetic member ID
  error_code: str | None
  error_message: str | None
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_READ`.

**Validation:** `patient_id` must be a known synthetic patient ID (validated against the PatientRepository result).

**Safety restrictions:** None beyond standard input validation.

**Source of truth:** Synthetic Insurance System (InsurancePlanRepository port).

**Failure behavior:** `success=False` with `error_code` for: plan not found, system unavailable (transient — retryable).

**Operation type:** Read only.

---

#### Tool 3: `get_authorization_requirements`

**Purpose:** Retrieve the prior-authorization requirements for an MRI procedure under the patient's insurance plan, using RAG-based retrieval over the synthetic policy repository.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `plan_id` | `str` | Yes | Synthetic insurance plan ID from `get_insurance_plan`. |
| `procedure_type` | `str` | Yes | Fixed value: `"MRI"` for the MVP. |

**Output structure:**
```
AuthorizationRequirementsResult
  success: bool
  requirements_id: str | None         # Opaque ID for this retrieved requirements set
  required_document_types: list[str]  # Document types required (e.g., "physician_referral")
  required_information_fields: list[str] # Information fields required in the submission
  retrieval_confidence: str | None    # "HIGH" | "MEDIUM" | "LOW" — informational only
  error_code: str | None
  error_message: str | None
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_READ`.

**Validation:** `plan_id` must be non-empty. `procedure_type` must be `"MRI"` for the MVP (enforced; other values are rejected).

**Safety restrictions:** The result is **informational only**. The application layer must not treat RAG-retrieved requirements as binding without deterministic validation confirmation.

**Source of truth:** PolicyProvider port (RAG over synthetic policy repository).

**Failure behavior:** `success=False` for: retrieval failure (transient — retryable), ambiguous requirements with `retrieval_confidence="LOW"` (treated as failure; escalation triggered).

**Operation type:** Read only.

---

#### Tool 4: `get_required_document`

**Purpose:** Retrieve a single supporting document from the synthetic document repository.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `document_reference` | `str` | Yes | The document reference identifier (from the requirements or EHR). |
| `document_type` | `str` | Yes | Expected document type (e.g., `"physician_referral"`). Must match a type in the requirements. |

**Output structure:**
```
DocumentResult
  success: bool
  document_id: str | None      # Internal document ID
  document_type: str | None    # Confirmed type
  content_reference: str | None  # Opaque reference to document content (not raw content)
  metadata: dict | None        # Non-sensitive document metadata
  error_code: str | None
  error_message: str | None
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_READ`.

**Validation:** `document_reference` must be non-empty. `document_type` must match a type from the requirements set.

**Safety restrictions:** Document content is not returned in full to the agent. Only a content reference and metadata are returned, preventing the LLM from reasoning directly over raw clinical document text.

**Source of truth:** DocumentRepository port (synthetic document repository).

**Failure behavior:** `success=False` for: document not found, repository unavailable (transient — retryable), type mismatch (non-retryable).

**Operation type:** Read only.

*Note: The agent calls this tool once per required document.*

---

#### Tool 5: `validate_authorization_package`

**Purpose:** Run deterministic validation over the gathered information to confirm the authorization package is complete and internally consistent before preparing the submission.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `patient_id` | `str` | Yes | Synthetic patient ID. |
| `plan_id` | `str` | Yes | Synthetic insurance plan ID. |
| `requirements_id` | `str` | Yes | Requirements set ID from `get_authorization_requirements`. |
| `document_ids` | `list[str]` | Yes | IDs of all gathered documents. |

**Output structure:**
```
ValidationResult
  is_valid: bool
  missing_fields: list[str]       # Fields required by policy but not present
  invalid_fields: list[str]       # Fields present but failing format/type checks
  conflicts: list[str]            # Detected inconsistencies between sources
  validation_notes: list[str]     # Additional informational notes
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_READ`.

**Validation:** All input IDs must reference known records in the current workflow context.

**Safety restrictions:** This is a pure read/analysis operation. No state is modified. The LLM sees the structured validation result only; it does not perform the validation.

**Source of truth:** Domain validation rules (deterministic, in `packages/safety` and `packages/domain`).

**Failure behavior:** Returns `is_valid=False` with populated detail lists. This is not an error — it is an expected outcome that the agent uses to determine next steps.

**Operation type:** Read only (no side effects).

---

#### Tool 6: `submit_authorization_request`

**Purpose:** Submit the prepared authorization request to the synthetic authorization portal.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `patient_id` | `str` | Yes | Synthetic patient ID. |
| `plan_id` | `str` | Yes | Synthetic insurance plan ID. |
| `requirements_id` | `str` | Yes | Requirements set ID. |
| `document_ids` | `list[str]` | Yes | IDs of all required documents (must match validated set). |

**Output structure:**
```
SubmissionResult
  success: bool
  submission_reference: str | None   # Opaque reference from the authorization portal
  initial_status: str | None         # Initial portal status (e.g., "RECEIVED")
  error_code: str | None
  error_message: str | None
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_SUBMIT` (more restrictive than `WORKFLOW_READ`).

**Validation:** All IDs must reference the validated authorization package for the current workflow. `validate_authorization_package` must have returned `is_valid=True` in the current workflow context.

**Safety restrictions:**
- Pre-submission safety gate must pass before the portal is called.
- Safety gate checks: package completeness, no clinically invented fields, `is_synthetic` confirmed on patient record, `is_valid=True` from validation.
- Workflow must be in `PREPARING_SUBMISSION` state at the time of invocation; any other state is a permission failure.
- The submission response alone does not constitute proof of success. `verify_authorization_outcome` must be called after a positive decision is received.

**Source of truth:** AuthorizationGateway port (synthetic authorization portal).

**Failure behavior:** `success=False` for portal rejection or unavailability. The workflow state is preserved (does not advance). Retry policy AD-012 Category 3 applies.

**Operation type:** **Mutating** — creates a submission record in PostgreSQL and calls the synthetic portal.

---

#### Tool 7: `get_authorization_status`

**Purpose:** Query the synthetic authorization portal for the current decision status of a submitted request.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `submission_reference` | `str` | Yes | Submission reference from `submit_authorization_request`. |

**Output structure:**
```
AuthorizationStatusResult
  success: bool
  status: str | None               # "PENDING" | "APPROVED" | "DENIED" | "ADDITIONAL_INFO_REQUIRED" | "UNKNOWN"
  status_message: str | None       # Human-readable status description
  additional_info_required: list[str] | None  # Required fields if status is ADDITIONAL_INFO_REQUIRED
  error_code: str | None
  error_message: str | None
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_READ`.

**Validation:** `submission_reference` must match a submission record in the current workflow context.

**Safety restrictions:** None beyond standard input validation.

**Source of truth:** AuthorizationStatusGateway port (synthetic authorization portal — independent status endpoint).

**Failure behavior:** `success=False` for portal unavailability (transient — retryable per AD-012 Category 1). Status `"UNKNOWN"` may trigger escalation if persistent.

**Operation type:** Read only.

---

#### Tool 8: `verify_authorization_outcome`

**Purpose:** Independently confirm that the expected authorization outcome actually exists in the authoritative external system, using a logically separate access path from the submission path. This is the mechanism that enforces the core safety principle: the agent cannot declare DONE.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `submission_reference` | `str` | Yes | Submission reference to verify. |
| `expected_status` | `str` | Yes | The expected outcome: `"APPROVED"` or `"DENIED"`. |

**Output structure:**
```
VerificationResult
  verified: bool                   # True only if the expected_status is confirmed by the independent source
  actual_status: str               # What the authoritative source actually shows
  verification_source: str         # Identifies the access path used (opaque reference for audit)
  error_code: str | None
  error_message: str | None
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_READ`.

**Validation:** `submission_reference` must match a submitted workflow. `expected_status` must be `"APPROVED"` or `"DENIED"` only.

**Safety restrictions:**
- This tool uses the VerificationProvider port, which is a logically independent access path from AuthorizationGateway. It does NOT re-read the same submission response.
- `verified=True` is the ONLY condition under which the application layer may transition to `COMPLETED` (if `expected_status="APPROVED"`) or `DENIED` (if `expected_status="DENIED"`).
- The workflow may NOT transition to `COMPLETED` based on the output of any other tool.

**Source of truth:** VerificationProvider port (independent read path on the synthetic authorization portal).

**Failure behavior:** Returns `verified=False` for: status mismatch, portal unavailable (retryable per AD-012 Category 2). After max retries, the workflow transitions to `ESCALATED`.

**Operation type:** Read only.

---

#### Tool 9: `request_escalation`

**Purpose:** Trigger a human escalation, pausing autonomous workflow execution and recording the reason for human review.

**Input parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `reason_code` | `str` | Yes | Machine-readable escalation reason code (e.g., `"VALIDATION_CONFLICT"`, `"VERIFICATION_FAILED"`, `"SAFETY_GATE_FAILED"`, `"INFORMATION_UNRESOLVABLE"`, `"PERMISSION_EXCEEDED"`). |
| `reason_summary` | `str` | Yes | Human-readable summary of why escalation is required. Must not contain raw sensitive patient data. Max 500 characters. |

**Output structure:**
```
EscalationResult
  success: bool
  escalation_id: str | None        # Unique escalation record ID
  workflow_state: str              # Confirms transition to "ESCALATED"
  error_code: str | None
  error_message: str | None
```

**Allowed caller:** Agent only.

**Permission required:** `WORKFLOW_ESCALATE`.

**Validation:** `reason_code` must be one of the defined escalation reason codes. `reason_summary` must be non-empty and within the character limit.

**Safety restrictions:**
- `reason_summary` must not contain raw patient identifiers, clinical details, or sensitive data. The application layer sanitizes this field before persistence.
- The workflow state transitions to `ESCALATED` atomically. The agent cannot continue invoking other tools after this tool returns successfully.

**Source of truth:** Application layer (creates EscalationRecord in PostgreSQL via infrastructure port).

**Failure behavior:** If the escalation record cannot be created (transient failure), the tool retries up to 3 times. If all retries fail, a `FAILED` terminal state is recorded directly by the application layer, bypassing the agent.

**Operation type:** **Mutating** — creates an escalation record in PostgreSQL and transitions workflow state to `ESCALATED`.

---

#### Tool Set Summary

| Tool | Operation Type | Permission | Retry Category |
|---|---|---|---|
| `get_patient_record` | Read | WORKFLOW_READ | Category 1 |
| `get_insurance_plan` | Read | WORKFLOW_READ | Category 1 |
| `get_authorization_requirements` | Read | WORKFLOW_READ | Category 1 |
| `get_required_document` | Read | WORKFLOW_READ | Category 1 |
| `validate_authorization_package` | Read | WORKFLOW_READ | Category 4 (failure = not error) |
| `submit_authorization_request` | Mutating | WORKFLOW_SUBMIT | Category 3 |
| `get_authorization_status` | Read | WORKFLOW_READ | Category 1 |
| `verify_authorization_outcome` | Read | WORKFLOW_READ | Category 2 |
| `request_escalation` | Mutating | WORKFLOW_ESCALATE | Special (see above) |

### Rationale

- The 9 tools map directly to the 14 agent capabilities in PRS §6. No additional tools are needed for the MRI MVP.
- Document retrieval is a single-document tool (`get_required_document`) rather than a bulk fetch, because the agent must reason about which documents are still needed based on validation results — this is an agent reasoning task, not a bulk data load.
- `validate_authorization_package` is a separate tool (not folded into `submit_authorization_request`) to allow the agent to identify and address validation failures before attempting submission, supporting the iterative information-gathering workflow.
- Raw document content is not returned to the agent (only content references) because the LLM must not reason directly over raw clinical documents; clinical content may not be invented or summarized.

### Alternatives Considered

- Bulk document retrieval tool (fetch all documents in one call)
- Combined validate-and-submit tool
- Returning raw document text to the agent for LLM reasoning

### Rejected Alternatives

- **Bulk document retrieval:** Prevents the agent from reasoning about which documents are still missing; would require the agent to always fetch all possible documents even when some are unnecessary.
- **Combined validate-and-submit:** Prevents the agent from acting on validation failure details (missing information requires additional gathering before submission).
- **Raw document text to LLM:** Creates risk of the LLM reasoning over clinical content, summarizing it, or — critically — inventing it. The safety boundary (§8.3) prohibits this.

### Architectural Impact

- `packages/application`: Each tool is implemented as a Python function conforming to the Strands tool interface.
- `packages/safety`: Permission codes `WORKFLOW_READ`, `WORKFLOW_SUBMIT`, `WORKFLOW_ESCALATE` must be defined.
- `docs/architecture/ARCHITECTURE.md` §7.2 (agent boundary diagram) is updated to remove the "illustrative" note and replace it with the finalized tool list.

### Requirements Impact

- PRS §6 (14 agent capabilities): All 14 capabilities are addressed by the 9 tools.
- PRS §7 (DONE principle): `verify_authorization_outcome` is the only path to `COMPLETED`.
- PRS §11 (permissions): Permission codes defined for each tool.
- No requirements are modified.

### Implementation Impact

- Each tool function signature must be decorated per the Strands SDK tool decorator pattern (exact pattern defined in the implementation phase).
- Input and output types must use Pydantic models for validation.
- The 9 tool functions must have unit tests in `tests/unit` and safety tests in `tests/safety`.

---

## AD-015: Embedding Model Selection for RAG

### Status

APPROVED

### Decision

The RAG pipeline uses **Amazon Titan Text Embeddings V2** as the embedding model.

- Bedrock model ID: `amazon.titan-embed-text-v2:0`
- Embedding dimensions: **1024**
- pgvector index vector dimension: **1024** (must match at schema definition time)
- Input token limit: 8,192 tokens (sufficient for standard insurance policy document chunks)
- Invoked via the existing Amazon Bedrock boto3 client (no additional embedding service required)
- Authentication: uses the same IAM role already established for Bedrock Claude access

### Rationale

- **Bedrock-native:** Amazon Titan Text Embeddings V2 is a first-party Amazon Bedrock model. It requires no additional service, API key, or SDK beyond the boto3 Bedrock client already designated in AD-010. This is the lowest-overhead choice for the AWS-first stack.
- **Compatibility:** pgvector supports 1024-dimensional vectors efficiently. 1024 dimensions is a standard size for modern embedding models and provides a good balance of retrieval quality and storage cost.
- **Healthcare policy text:** Policy documents are English-language administrative text. Amazon Titan Text Embeddings V2 is trained for general English text understanding and performs well on administrative and regulatory document types.
- **Reproducibility and testability:** Using a managed Bedrock model gives reproducible embeddings for the same input text (no local model weights to manage, no version drift outside of Bedrock model version pinning).
- **No additional dependency:** The Titan embedding model is accessed through the same boto3 Bedrock Runtime client used for Claude. No separate embedding library or model serving infrastructure is required.
- **MVP suitability:** The model is available in standard Bedrock regions (us-east-1, us-west-2), aligns with the MVP's AWS infrastructure, and requires no special provisioning beyond enabling the model in the AWS account.

### Alternatives Considered

- **Cohere Embed English v3** (`cohere.embed-english-v3`) via Amazon Bedrock — 1024 dimensions
- **Amazon Titan Embeddings G1 - Text** (`amazon.titan-embed-text-v1`) — 1536 dimensions
- **OpenAI `text-embedding-3-small`** — 1536 dimensions
- **Local/self-hosted sentence-transformers model**

### Rejected Alternatives

- **Cohere Embed English v3:** Also a valid Bedrock option. Cohere is a third-party model; using a first-party Amazon model reduces external dependency surface. Both have similar English text performance; the AWS-first preference favors Titan.
- **Amazon Titan Embeddings G1 (v1):** Older model; superseded by V2. V2 provides better retrieval quality for the same AWS-native approach. V1 is not preferred for new implementations.
- **OpenAI `text-embedding-3-small`:** Requires an OpenAI API key — an external service dependency outside the locked AWS/Bedrock stack. Violates the constraint to use the locked technology stack (PRS §17). Rejected.
- **Self-hosted sentence-transformers:** Requires running a local model serving process, managing model weights, and additional infrastructure. Adds significant operational complexity that is not justified for MVP. Introduces an infrastructure dependency that is not in the locked stack.

### Architectural Impact

- `docs/architecture/ARCHITECTURE.md` §15.2 (RAG Pipeline) is updated to replace the placeholder "model to be specified" with `amazon.titan-embed-text-v2:0`.
- `docs/architecture/ARCHITECTURE.md` §15.5 (Embedding Model) is updated with the resolved decision.
- pgvector index dimension is fixed at **1024**. This constraint must be applied when the database schema is defined in the schema specification phase. Changing the embedding model after the schema is created requires a migration.

### Requirements Impact

- PRS §17 (technology: Amazon Bedrock, pgvector): This decision uses both as required.
- No requirements are modified.

### Implementation Impact

- The boto3 Bedrock Runtime `invoke_model` call for embedding generation will target `amazon.titan-embed-text-v2:0`.
- pgvector column definition: `VECTOR(1024)`.
- Chunk size for policy documents must be tuned to stay within the 8,192-token input limit (exact chunk size defined in the RAG ingestion pipeline specification).
- Model version pinning: the implementation must pin the specific model version to avoid unexpected behavior from model updates.
