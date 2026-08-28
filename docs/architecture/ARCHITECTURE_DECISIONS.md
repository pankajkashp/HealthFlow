# HealthFlow — Architecture Decisions

**Version:** 1.0
**Phase:** 0B — Technical Architecture Specification
**Authority:** Product Requirements Specification v1.0

This document records significant architectural decisions made during Phase 0B.

Each decision is made only where the Product Requirements Specification provides sufficient
grounds. Decisions that cannot be made without additional information are marked **PENDING APPROVAL**.

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

**Decision:** PENDING APPROVAL

**Reason:**
The Product Requirements Specification does not specify an authentication mechanism,
identity provider, or authorization model for the MVP.

Authentication is required (the API must not be publicly accessible), but the specific
mechanism (e.g., JWT, OAuth 2.0, session-based, AWS Cognito) has not been approved.

**Impact:**
Authentication must be specified in a future phase specification before the API layer
can be implemented with authentication enforcement.

**Status:** PENDING APPROVAL

---

## AD-012: Retry Policy for Transient Failures

**Decision:** PENDING APPROVAL

**Reason:**
The Product Requirements Specification does not specify retry behavior for transient
tool failures or external-system unavailability.

Retry behavior must be defined carefully in a healthcare administrative context:
- Retrying a submission could result in duplicate submissions.
- Retrying a status query is safer.

The distinction between idempotent and non-idempotent operations must be specified
before a retry policy is implemented.

**Status:** PENDING APPROVAL

---

## AD-013: Specific Workflow States Enumeration

**Decision:** PENDING APPROVAL

**Reason:**
The Product Requirements Specification describes the workflow at a behavioral level
(§6 — 14 agent capabilities, §22 — success criteria). It does not enumerate specific
workflow state names.

The state machine design requires explicit state names, transition conditions, and
failure/escalation paths. This requires a dedicated workflow specification phase.

**Status:** PENDING APPROVAL

---

## AD-014: Agent Tool API — Exact Function Names and Signatures

**Decision:** PENDING APPROVAL

**Reason:**
Tool names used in ARCHITECTURE.md Section 7 (e.g., `get_patient_record`,
`validate_authorization_package`) are illustrative only. The exact function names,
parameter schemas, and return schemas must be defined in a dedicated tool contract
specification phase.

Tool names must conform to `docs/engineering/NAMING_CONVENTIONS.md`.

**Status:** PENDING APPROVAL

---

## AD-015: Embedding Model Selection for RAG

**Decision:** PENDING APPROVAL

**Reason:**
The Product Requirements Specification specifies pgvector and Amazon Bedrock but does not
specify which embedding model to use. The choice of embedding model affects:
- Embedding dimensions (pgvector index must match)
- Retrieval quality for policy text
- Cost

This decision requires the RAG implementation specification phase.

**Status:** PENDING APPROVAL
