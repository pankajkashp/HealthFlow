# Phase 0B Walkthrough — Technical Architecture Specification

**Phase:** 0B — Technical Architecture Specification
**Phase Document:** This phase has no separate PHASE_00B.md; scope is defined in the Phase 0B prompt.
**Date Completed:** 2026-08-28
**Specification Authority:** Product Requirements Specification v1.0

---

## Phase Summary

Phase 0B established the technical architecture specification for HealthFlow.

This was a **design and specification phase only**. No application code was written.
No dependencies were installed. No database schema was created. No agent was implemented.

Three architecture documents were created:
1. `docs/architecture/ARCHITECTURE.md` — the authoritative technical architecture
2. `docs/architecture/ARCHITECTURE_DECISIONS.md` — 15 architectural decisions (10 APPROVED, 5 PENDING APPROVAL)
3. `docs/architecture/REQUIREMENTS_TRACEABILITY.md` — traceability from every PRS section to the architecture

---

## Documents Created

| File | Purpose |
|---|---|
| `docs/architecture/ARCHITECTURE.md` | Authoritative technical architecture specification — 22 sections covering all required topics |
| `docs/architecture/ARCHITECTURE_DECISIONS.md` | 15 architectural decisions with rationale and alternatives |
| `docs/architecture/REQUIREMENTS_TRACEABILITY.md` | Full traceability from PRS §1–§26 to architecture sections |
| `docs/phases/PHASE_00B_WALKTHROUGH.md` | This document |

---

## Documents Modified

None. No existing files were modified.

The Product Requirements Specification (`docs/product/PRODUCT_REQUIREMENTS.md` and `REQUIRMENTS.MD`)
was not modified. Verified with `diff REQUIRMENTS.MD docs/product/PRODUCT_REQUIREMENTS.md` →
output: `PRS_UNMODIFIED`.

---

## Architecture Summary

The architecture describes a six-layer system:

| Layer | Location | Core Responsibility |
|---|---|---|
| Presentation | `apps/web` | Next.js frontend; user interaction only |
| API | `apps/api` | FastAPI HTTP boundary; routing, serialization, auth enforcement |
| Application | `packages/application` | Use-case orchestration; workflow coordination; agent tool definitions |
| Domain | `packages/domain` | Core business concepts; port interfaces; validation rules; workflow state definitions |
| Infrastructure | `packages/infrastructure` | Port implementations; database; simulated system adapters; pgvector/RAG |
| Safety | `packages/safety` | Deterministic validation; permission checks; safety gates |

Plus the Agent Layer (`services/agent`) — AWS Strands + Claude via Amazon Bedrock — a controlled reasoning component that invokes authorized application-layer tool functions only.

The architecture enforces the core safety principle from PRS §7:
> The agent cannot say DONE. The environment must prove DONE.

Every significant action must be followed by independent verification via the VerificationProvider port before the workflow may advance.

---

## Layer Responsibilities

### Presentation (apps/web)
Renders the UI: case view, agent activity, workflow timeline, escalation prompts, verification results.
Must NOT contain business rules or communicate directly with the database or agent.

### API (apps/api)
Accepts HTTP requests; validates request schema; delegates to application use cases; serializes responses.
Must NOT contain business logic; must NOT access the database directly.

### Application (packages/application)
Implements use cases; orchestrates domain + safety + infrastructure ports.
Defines the authorized agent tool functions.
Must NOT import from infrastructure implementations directly (uses port interfaces).

### Domain (packages/domain)
Defines business entities (Patient, Authorization, Workflow, Submission, Verification, Escalation, Audit, etc.).
Defines port interfaces (PatientRepository, InsurancePlanRepository, PolicyProvider, DocumentRepository, AuthorizationGateway, AuthorizationStatusGateway, VerificationProvider).
Must NOT import any framework or infrastructure library.

### Infrastructure (packages/infrastructure)
Implements all port interfaces: SQLAlchemy repositories, simulated system adapters, pgvector/RAG adapter, audit persistence.
Must NOT expose SQLAlchemy types to the domain or application layers.

### Safety (packages/safety)
Implements deterministic input validation, permission checks, and safety gate logic.
These are code-based controls, NOT LLM prompts.
Must NOT be bypassed by any layer.

### Agent (services/agent)
Hosts the Strands SDK and Claude LLM.
Invokes authorized application-layer tools only.
Does not access the database, external systems, or application state directly.
Does not hold authoritative state.
Cannot declare completion independently.

---

## Dependency Rules

### Allowed Direction
```
Presentation → API → Application → Domain
Infrastructure → Domain (implements ports)
Safety → Domain (uses domain contracts)
Agent → Application (invokes tool functions only)
```

### Explicitly Prohibited

| Prohibited | Reason |
|---|---|
| Domain → Infrastructure | Domain must be framework-independent |
| Domain → FastAPI / SQLAlchemy / Strands | Domain must be framework-independent |
| Application → Infrastructure directly | Must use port interfaces |
| Agent → PostgreSQL directly | Agent uses authorized tools only |
| Agent → Simulated systems directly | Agent uses authorized tools only |
| Frontend → Database | Always prohibited |
| API routes → Business logic inline | Routes delegate to application layer |
| Any layer → Safety bypass | Safety controls are non-negotiable |

---

## Agent Boundary

### What the agent MAY do
- Interpret the prior-authorization goal
- Reason about workflow progress
- Select among authorized application-layer tool functions
- Inspect structured tool results
- Determine the next permitted action
- Request escalation

### What the agent MAY NOT do
- Access PostgreSQL directly
- Access simulated external systems directly
- Bypass input validation, permission checks, or safety gates
- Declare workflow completion without verification
- Make clinical decisions
- Hold authoritative workflow state

The agent calls application-layer tool functions. Each tool function runs: permission check → validation → safety gate → action → returns a structured result to the agent.

---

## Safety Boundary

Safety is enforced through six deterministic steps in sequence before and after every significant action:

1. **Input validation** (deterministic code, Safety Layer)
2. **Permission check** (deterministic code, Safety Layer)
3. **Business-rule validation** (deterministic code, Domain Layer)
4. **Safety gate** (deterministic code, Safety Layer)
5. **Action execution** (Application + Infrastructure)
6. **Independent verification** (VerificationProvider port)

Safety controls are implemented in deterministic code — not in LLM prompts.
The LLM cannot bypass any of these steps.

---

## Trust Boundaries

| Source | Trust Level | Authoritative For |
|---|---|---|
| User input | Untrusted | Nothing — must be validated |
| LLM output | Untrusted | Nothing — LLM does not hold state |
| Tool call result | Semi-trusted | Informational, subject to validation |
| PostgreSQL | Trusted | Workflow state, audit records |
| Synthetic EHR | Trusted-but-external | Patient identity (after validation) |
| Synthetic Insurance | Trusted-but-external | Insurance plan (after validation) |
| Synthetic Policy Repo | Informational | Authorization requirements |
| Synthetic Document Repo | Trusted-but-external | Document content (after validation) |
| Synthetic Authorization Portal | Authoritative-external | Submission reference, status |
| VerificationProvider result | Authoritative | Final workflow outcome determination |

---

## Source of Truth

| Concept | Authoritative Source |
|---|---|
| Workflow state | PostgreSQL |
| Authorization case | PostgreSQL |
| Audit records | PostgreSQL (immutable) |
| Final DONE determination | VerificationProvider result |
| LLM / agent context | NOT authoritative for anything |

The LLM is explicitly NOT the source of truth for any data, state, or outcome.

---

## Open Decisions (PENDING APPROVAL)

| ID | Decision Pending |
|---|---|
| AD-011 | Authentication mechanism (JWT, OAuth 2.0, Cognito, etc.) — PRS does not specify |
| AD-012 | Retry policy for transient failures — must distinguish idempotent vs. non-idempotent operations |
| AD-013 | Specific workflow state names and transition graph |
| AD-014 | Exact agent tool function names and parameter/return schemas |
| AD-015 | Embedding model for RAG (must be compatible with Amazon Bedrock + pgvector) |

---

## Out of Scope

The following items are explicitly NOT implemented in Phase 0B:

- Frontend implementation
- Backend API endpoints
- Database schema or migration files
- Agent implementation
- AWS Strands configuration
- Claude/Bedrock integration
- Simulated healthcare system implementations
- Authorization workflow logic
- RAG pipeline implementation
- Authentication or authorization implementation
- Business logic of any kind
- Application dependency installation
- Docker or infrastructure configuration
- Any source code files (.py, .ts, .tsx, .js)

---

## Verification

### Check: No application source code created

Command:
```
find . -not -path './.git/*' \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) | sort
```
Result: No output. Zero source code files found. ✅

### Check: No dependency manifests created

Command:
```
find . -not -path './.git/*' \( -name "package.json" -o -name "requirements.txt" -o -name "pyproject.toml" -o -name "setup.py" -o -name "Pipfile" \) | sort
```
Result: No output. Zero dependency manifests found. ✅

### Check: Product Requirements Specification unmodified

Command:
```
diff REQUIRMENTS.MD docs/product/PRODUCT_REQUIREMENTS.md && echo "PRS_UNMODIFIED"
```
Result: `PRS_UNMODIFIED` ✅

### Check: Architecture does not contradict Product Requirements

Manual review performed: All 22 architecture sections were derived from and cross-referenced
with the Product Requirements Specification. No architecture section introduces requirements
not present in the PRS. Confirmed via the Requirements Traceability document. ✅

### Check: Technology stack unchanged

All technology references in ARCHITECTURE.md use only the locked technology stack from PRS §17.
No substitutions or additions were made. ✅

### Check: All required architecture sections present in ARCHITECTURE.md

Sections present (22 total):
System Overview, Layer Responsibilities, Dependency Direction, Repository Responsibilities,
Domain Boundaries, Ports and Adapters, Agent Boundary, Safety Architecture, Trust Boundaries,
Source of Truth, Workflow State Architecture, Data Flow, External System Architecture,
Database Architecture, RAG Architecture, API Architecture, Frontend Architecture,
Observability Architecture, Security Architecture, Error and Failure Architecture,
Scalability, Architectural Rules. ✅

### Check: Repository tree after Phase 0B

```
./docs/architecture/ARCHITECTURE.md               ← NEW
./docs/architecture/ARCHITECTURE_DECISIONS.md     ← NEW
./docs/architecture/REQUIREMENTS_TRACEABILITY.md  ← NEW
./docs/phases/PHASE_00B_WALKTHROUGH.md            ← NEW
[all other files from Phase 00 unchanged]
```
✅

### Check: Dependency direction is clear

Documented in ARCHITECTURE.md §3 with a diagram and a prohibited dependency table. ✅

### Check: Agent boundaries are clear

Documented in ARCHITECTURE.md §7 with a boundary diagram, permitted/prohibited tables, and tool invocation path. ✅

### Check: Safety boundaries are clear

Documented in ARCHITECTURE.md §8 with a six-step safety flow diagram and an LLM vs. deterministic enforcement table. ✅

### Check: Source-of-truth boundaries are clear

Documented in ARCHITECTURE.md §10 with an explicit source-of-truth table. ✅

### Check: Scalability strategy does not implement future workflows

ARCHITECTURE.md §21 describes the extension strategy (new use cases, new ports, new state machines).
No future workflow code was created. ✅

---

## Dependencies Added

**None.**

---

## Deviations

None. The architecture documentation covers all sections required by the Phase 0B specification.

Architectural decisions that could not be made from the approved requirements are marked
PENDING APPROVAL in `ARCHITECTURE_DECISIONS.md` rather than guessed or invented.

---

## Blockers

None. The five PENDING APPROVAL items are known open decisions that require future phase
specifications. They do not block the completion of Phase 0B because Phase 0B is a
design-only phase and those details belong to later specification phases.

---

## Phase Status

**PASS**

All Phase 0B acceptance criteria are met:

- [x] `docs/architecture/ARCHITECTURE.md` created with all required sections
- [x] `docs/architecture/ARCHITECTURE_DECISIONS.md` created with decisions and rationale
- [x] `docs/architecture/REQUIREMENTS_TRACEABILITY.md` created with full PRS mapping
- [x] `docs/phases/PHASE_00B_WALKTHROUGH.md` created (this document)
- [x] Architecture does not contradict the Product Requirements Specification
- [x] Technology stack is unchanged from PRS §17
- [x] No application source code created
- [x] No dependencies installed
- [x] No database schema implemented
- [x] No agent implementation created
- [x] No AWS configuration created
- [x] Product Requirements Specification is unmodified (verified with diff)
- [x] Dependency direction is documented and clear
- [x] Agent boundaries are documented and clear
- [x] Safety boundaries are documented and clear
- [x] Source-of-truth boundaries are documented and clear
- [x] Scalability strategy does not implement future workflows
