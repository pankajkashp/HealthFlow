# HealthFlow — Technical Architecture Specification

**Version:** 1.0
**Status:** APPROVED — Phase 0B
**Authority:** Product Requirements Specification v1.0
**Phase:** 0B — Technical Architecture Specification

This document is the authoritative technical architecture for HealthFlow.
All implementation phases must conform to this architecture.

No implementation agent may deviate from this architecture without explicit project-owner approval
and a documented architecture decision record in `docs/architecture/ARCHITECTURE_DECISIONS.md`.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Layer Responsibilities](#2-layer-responsibilities)
3. [Dependency Direction](#3-dependency-direction)
4. [Repository Responsibilities](#4-repository-responsibilities)
5. [Domain Boundaries](#5-domain-boundaries)
6. [Ports and Adapters](#6-ports-and-adapters)
7. [Agent Boundary](#7-agent-boundary)
8. [Safety Architecture](#8-safety-architecture)
9. [Trust Boundaries](#9-trust-boundaries)
10. [Source of Truth](#10-source-of-truth)
11. [Workflow State Architecture](#11-workflow-state-architecture)
12. [Data Flow](#12-data-flow)
13. [External System Architecture](#13-external-system-architecture)
14. [Database Architecture](#14-database-architecture)
15. [RAG Architecture](#15-rag-architecture)
16. [API Architecture](#16-api-architecture)
17. [Frontend Architecture](#17-frontend-architecture)
18. [Observability Architecture](#18-observability-architecture)
19. [Security Architecture](#19-security-architecture)
20. [Error and Failure Architecture](#20-error-and-failure-architecture)
21. [Scalability](#21-scalability)
22. [Architectural Rules](#22-architectural-rules)

---

## 1. System Overview

HealthFlow is an autonomous administrative workflow system. The primary user (doctor or
healthcare administrative staff) initiates an MRI prior-authorization goal. The system then
autonomously executes the permitted administrative workflow, verifying the final outcome
independently before declaring completion.

### 1.1 High-Level System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        PRIMARY USERS                         │
│                  (Doctors / Admin Staff)                     │
└───────────────────────────┬──────────────────────────────────┘
                            │  HTTPS
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                         │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │           Next.js Web Application (apps/web)        │   │
│   │      TypeScript · Tailwind CSS · shadcn/ui          │   │
│   └─────────────────────────┬───────────────────────────┘   │
└─────────────────────────────┼────────────────────────────────┘
                              │  REST / JSON over HTTPS
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       API LAYER                              │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │         FastAPI Application (apps/api)              │   │
│   │           Python · Pydantic · REST                  │   │
│   └─────────────────────────┬───────────────────────────┘   │
└─────────────────────────────┼────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│              (packages/application)                          │
│                                                              │
│   Use cases · Workflow orchestration · Event publication     │
│   Coordinates: Domain · Safety · Infrastructure ports        │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
                ▼                              ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│      DOMAIN LAYER        │   │       SAFETY LAYER           │
│   (packages/domain)      │   │    (packages/safety)         │
│                          │   │                              │
│  Business concepts       │   │  Input validation            │
│  Business rules          │   │  Permission checks           │
│  Workflow state          │   │  Safety gates                │
│  Port definitions        │   │  Action controls             │
│  Domain events           │   │  Verification contracts      │
└──────────────────────────┘   └──────────────────────────────┘
                │
                ▼ (via ports/interfaces — dependency inversion)
┌──────────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                         │
│              (packages/infrastructure)                       │
│                                                              │
│  PostgreSQL adapters (SQLAlchemy 2.x)                        │
│  Synthetic EHR adapter                                       │
│  Synthetic Insurance adapter                                 │
│  Synthetic Policy adapter                                    │
│  Synthetic Document adapter                                  │
│  Synthetic Authorization Portal adapter                      │
│  pgvector / RAG adapter                                      │
│  Storage adapter (S3 — future)                               │
│  Observability adapter (CloudWatch / structured logs)        │
└──────────────────────────────────────────────────────────────┘

                    AGENT PATH (parallel to the above)

┌──────────────────────────────────────────────────────────────┐
│                       AGENT LAYER                            │
│                   (services/agent)                           │
│                                                              │
│  AWS Strands Agents SDK                                      │
│  Claude via Amazon Bedrock                                   │
│                                                              │
│  Receives: Workflow context from Application Layer           │
│  Selects: Authorized application-layer tools only           │
│  Returns: Tool call requests                                 │
│                                                              │
│  The agent does NOT access PostgreSQL directly.              │
│  The agent does NOT access external systems directly.        │
│  The agent is NOT the source of truth.                       │
└──────────────────────────────────────────────────────────────┘

                    SIMULATED EXTERNAL SYSTEMS

┌──────────────────────────────────────────────────────────────┐
│              SYNTHETIC HEALTHCARE SYSTEMS                    │
│              (accessed through Infrastructure adapters)      │
│                                                              │
│  Synthetic EHR              Synthetic Insurance System       │
│  Synthetic Policy Repo      Synthetic Document Repository    │
│  Synthetic Authorization Portal                              │
│                                                              │
│  All systems are deterministic and controllable.             │
│  No real healthcare data. No real healthcare systems.        │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Core Architectural Principle

> The agent cannot declare DONE. The environment must prove DONE.
> (Ref: Product Requirements Specification §7)

Authoritative state belongs to PostgreSQL and the simulated external systems.
The LLM reasons over information provided by authorized tools. It does not hold state.

---

## 2. Layer Responsibilities

### 2.1 Presentation Layer

**Location:** `apps/web`

**Responsibility:**
- Render the user interface for doctors and healthcare administrative staff.
- Display authorization case status, workflow timeline, agent activity, escalation prompts, and verification results.
- Collect user input (goal initiation, escalation decisions).
- Communicate with the API layer exclusively via REST.

**Must NOT:**
- Contain business rules.
- Communicate directly with the database.
- Communicate directly with the agent.
- Render sensitive patient data unnecessarily.
- Make clinical decisions or display clinical recommendations.

---

### 2.2 API Layer

**Location:** `apps/api`

**Responsibility:**
- Accept and validate incoming HTTP requests.
- Authenticate requests (authentication details deferred to a later specification).
- Delegate to application-layer use cases.
- Serialize and return responses.
- Own the HTTP contract: request schema, response schema, HTTP status codes, error responses.

**Must NOT:**
- Contain business logic.
- Contain workflow orchestration.
- Communicate directly with the database.
- Communicate directly with external systems.
- Communicate directly with the agent.
- Return raw database objects.

---

### 2.3 Application Layer

**Location:** `packages/application`

**Responsibility:**
- Implement use cases that represent permitted user or system operations.
- Orchestrate domain objects, safety checks, and infrastructure ports to fulfill a use case.
- Coordinate workflow state transitions (through domain concepts, not by managing state directly in the application layer).
- Publish domain events to observability infrastructure.
- Provide the tool interface that the agent invokes (tools are application-layer operations, not direct infrastructure calls).

**Must NOT:**
- Contain domain business rules (those belong in the domain layer).
- Import from infrastructure implementations directly (use ports/interfaces).
- Import FastAPI, SQLAlchemy, or any infrastructure framework type.
- Bypass safety controls.
- Make decisions that require clinical judgment.

---

### 2.4 Domain Layer

**Location:** `packages/domain`

**Responsibility:**
- Define the core business concepts for HealthFlow (Patient, Authorization, Workflow, etc.).
- Define business rules that are independent of infrastructure and frameworks.
- Define port interfaces (protocols/abstract base classes) that infrastructure must satisfy.
- Define domain events.
- Define workflow state and permitted transitions as domain concepts.
- Define validation rules for domain concepts.

**Must NOT:**
- Import from FastAPI, SQLAlchemy, Next.js, Strands, Claude, AWS SDK, or any infrastructure library.
- Know how data is persisted.
- Know how external systems are called.
- Know how the agent works.
- Make network calls.
- Access the database.

The domain layer is the innermost layer. It has no outward dependencies on any other application layer.

---

### 2.5 Infrastructure Layer

**Location:** `packages/infrastructure`

**Responsibility:**
- Implement the port interfaces defined by the domain layer.
- Manage database sessions, connections, and queries via SQLAlchemy 2.x.
- Manage Alembic migration configuration.
- Implement adapters for each simulated external system.
- Implement the pgvector/RAG adapter for policy retrieval.
- Implement observability output (structured logging, audit event persistence).

**Must NOT:**
- Contain business rules.
- Contain application orchestration.
- Expose infrastructure types (e.g., SQLAlchemy models) to the application or domain layers.
- Bypass domain port interfaces.

---

### 2.6 Agent Layer

**Location:** `services/agent`

**Responsibility:**
- Host the AWS Strands Agents SDK runtime.
- Initialize the Claude via Amazon Bedrock model.
- Receive workflow context from the application layer.
- Select authorized application-layer tools and invoke them.
- Reason about tool results and determine the next action.
- Request escalation when uncertainty exceeds defined thresholds.

**Must NOT:**
- Access PostgreSQL directly.
- Access simulated external systems directly.
- Bypass application-layer validation or safety gates.
- Declare workflow completion independently.
- Make clinical decisions.
- Hold authoritative workflow state.

See Section 7 for the complete agent boundary definition.

---

### 2.7 Safety Layer

**Location:** `packages/safety`

**Responsibility:**
- Implement deterministic input validation.
- Implement permission checks for workflow actions.
- Implement safety gate logic (pre-action guards).
- Define and enforce action authorization rules.
- Provide the verification contract interface used after actions.

**Must NOT:**
- Be bypassed by any layer, including the agent.
- Be implemented solely through LLM prompting.
- Contain business rules unrelated to safety, permissions, or validation.
- Make clinical decisions.

---

## 3. Dependency Direction

### 3.1 Allowed Dependency Direction

```
Presentation (apps/web)
    ↓  REST only
API (apps/api)
    ↓
Application (packages/application)
    ↓
Domain (packages/domain)  ←──────────────────────────────────┐
    │                                                         │
    │ defines port interfaces                                 │
    ▼                                                         │
[Port Interface]                                              │
    ↑                                                         │
Infrastructure (packages/infrastructure)                      │
    │ implements port interfaces defined by domain            │
    └─────────────────────────────────────────────────────────┘

Safety (packages/safety)
    → depends on Domain contracts
    → used by Application

Agent (services/agent)
    → invokes Application-layer tool functions only
    → no direct dependency on Infrastructure, Domain internals, or Database
```

### 3.2 Prohibited Dependencies

| Prohibited                                    | Reason                                          |
|-----------------------------------------------|-------------------------------------------------|
| Domain → Infrastructure                       | Domain must be framework-independent            |
| Domain → FastAPI                              | Domain must be framework-independent            |
| Domain → SQLAlchemy                           | Domain must be framework-independent            |
| Domain → Strands / Claude / AWS SDK           | Domain must be framework-independent            |
| Application → Infrastructure (direct)         | Must use port interfaces, not implementations   |
| Application → FastAPI                         | API concerns must not enter the application     |
| Agent → PostgreSQL (direct)                   | Agent must use authorized tools only            |
| Agent → Simulated systems (direct)            | Agent must use authorized tools only            |
| Frontend → Database                           | Prohibited at all times                         |
| API routes → Business logic (inline)          | Business logic belongs in the application layer |
| Infrastructure logic → Domain entities        | Direction must not be reversed                  |
| Any layer → Safety bypass                     | Safety controls are mandatory                   |

### 3.3 Shared Package

`packages/shared` may contain:
- Common Pydantic base models with no domain semantics
- Common value types used across multiple layers (e.g., identifiers, timestamps)
- Cross-cutting utilities that are purely technical (e.g., result/error types)

`packages/shared` must NOT contain:
- Business rules
- Domain logic
- Infrastructure implementations

---

## 4. Repository Responsibilities

### 4.1 `apps/api`

**Purpose:** FastAPI backend application — HTTP entry point for HealthFlow.

**Allowed dependencies:** `packages/application`, `packages/shared`, FastAPI, Pydantic, standard library.

**Prohibited dependencies:** `packages/domain` (direct), `packages/infrastructure` (direct), `services/agent` (direct), any simulated external system client.

**Responsibilities:**
- HTTP routing and request/response serialization
- Request validation (schema-level, not business-rule-level)
- Authentication enforcement (once authentication is specified)
- Delegation to application-layer use cases

---

### 4.2 `apps/web`

**Purpose:** Next.js frontend web application — user interface for doctors and admin staff.

**Allowed dependencies:** React, Next.js, TypeScript, Tailwind CSS, shadcn/ui, REST API calls to `apps/api`.

**Prohibited dependencies:** Direct database access, direct agent access, domain types from `packages/domain`.

**Responsibilities:**
- Rendering authorization case UI
- Capturing user input (goal submission, escalation decisions)
- Displaying workflow state, agent activity, escalation requests, verification results
- Fetching data from the API layer

---

### 4.3 `services/agent`

**Purpose:** AWS Strands Agents SDK runtime — the AI reasoning component.

**Allowed dependencies:** AWS Strands Agents SDK, Amazon Bedrock client, application-layer tool functions, `packages/shared`.

**Prohibited dependencies:** Direct PostgreSQL access, direct SQLAlchemy usage, direct simulated-system clients, `packages/domain` internals, `packages/infrastructure`.

**Responsibilities:**
- Hosting the Strands agent runtime
- Invoking Claude via Amazon Bedrock
- Executing authorized application-layer tools
- Reasoning over tool results
- Triggering escalation when required

---

### 4.4 `packages/domain`

**Purpose:** Core business concepts and business rules — the innermost layer.

**Allowed dependencies:** Python standard library, Pydantic (for value validation only), `packages/shared`.

**Prohibited dependencies:** Everything else — no FastAPI, no SQLAlchemy, no AWS SDK, no Strands, no infrastructure libraries.

**Responsibilities:**
- Domain entities (Patient, Authorization, Workflow, etc.)
- Domain value objects
- Port interface definitions (Protocols / ABCs)
- Domain events
- Workflow state definitions (as domain concepts)
- Domain validation rules

---

### 4.5 `packages/application`

**Purpose:** Use-case orchestration — coordinates domain, safety, and infrastructure.

**Allowed dependencies:** `packages/domain`, `packages/safety`, `packages/shared`, Python standard library, Pydantic.

**Prohibited dependencies:** FastAPI, SQLAlchemy, Strands, AWS SDK, `packages/infrastructure` (direct — must use ports).

**Responsibilities:**
- Use case implementations
- Workflow orchestration (invoking domain rules, safety checks, infrastructure ports)
- Agent tool function definitions (the application functions the agent is permitted to call)
- Domain event publication

---

### 4.6 `packages/infrastructure`

**Purpose:** Implementations of domain port interfaces — all framework and external-system details.

**Allowed dependencies:** `packages/domain`, `packages/shared`, SQLAlchemy 2.x, Alembic, pgvector, boto3/Bedrock client, simulated-system clients, structured logging library.

**Prohibited dependencies:** `packages/application` (infrastructure must not depend upward on application), FastAPI.

**Responsibilities:**
- SQLAlchemy repository implementations
- Simulated external system adapter implementations
- pgvector embedding and retrieval adapter
- Audit event persistence
- Structured log output

---

### 4.7 `packages/safety`

**Purpose:** Deterministic safety controls — validation, permissions, and safety gates.

**Allowed dependencies:** `packages/domain`, `packages/shared`, Python standard library, Pydantic.

**Prohibited dependencies:** `packages/infrastructure`, `packages/application`, FastAPI, SQLAlchemy.

**Responsibilities:**
- Input validation logic (deterministic, rule-based)
- Permission check implementations
- Safety gate implementations (pre-action guards)
- Action authorization rules
- Verification contract interfaces

---

### 4.8 `packages/shared`

**Purpose:** Common technical types and utilities with no domain semantics.

**Allowed dependencies:** Python standard library, Pydantic (minimal), TypeScript standard library.

**Prohibited dependencies:** Domain logic, application logic, infrastructure libraries.

**Responsibilities:**
- Common identifier types
- Common result/error types
- Common timestamp utilities
- Cross-cutting technical constants

---

### 4.9 `tests/unit`

**Purpose:** Fast, isolated tests of individual units.

**Scope:** Domain logic, safety logic, application use cases (with mocked ports), shared utilities.

**Dependencies:** pytest, Vitest, mocking libraries appropriate to the language.

---

### 4.10 `tests/integration`

**Purpose:** Tests of integrated components, including real infrastructure (test database, test adapters).

**Scope:** Repository implementations with a test database, adapter implementations with simulated systems.

---

### 4.11 `tests/contract`

**Purpose:** Contract tests verifying that infrastructure adapters correctly satisfy domain port interfaces.

**Scope:** Each port interface has at least one contract test verifying behavioral compliance of its adapter.

---

### 4.12 `tests/agent`

**Purpose:** Tests of agent behavior against controlled workflow scenarios.

**Scope:** Agent tool selection, tool invocation sequences, escalation triggering, response to simulated outcomes.

---

### 4.13 `tests/safety`

**Purpose:** Automated tests of all safety-critical paths.

**Scope:** Input validation, permission checks, safety gates, verification logic.

Critical safety, permission, state-transition, and verification behavior MUST have automated tests
in this directory. (Ref: Product Requirements Specification §16)

---

### 4.14 `tests/benchmark`

**Purpose:** Performance and quality benchmarks run against synthetic test cases.

**Scope:** End-to-end completion rate, validation accuracy, verification accuracy, false-completion rate,
unsafe-action rate, and other metrics defined in Product Requirements Specification §15.

No benchmark result may be presented as a measured achievement unless it was actually executed.

---

### 4.15 `docs`

**Purpose:** All project documentation — specifications, architecture, contracts, engineering rules, phase records.

No application source code belongs here.

---

### 4.16 `scripts`

**Purpose:** Development and operational scripts — database seed scripts, local setup helpers, CI utilities.

Scripts must not contain business logic. Scripts are not production application code.

---

### 4.17 `migrations`

**Purpose:** Alembic database migration files.

Migration files are generated by Alembic and represent the PostgreSQL schema evolution.

Schema definition belongs to a later specification phase.

---

### 4.18 `docker`

**Purpose:** Docker and Docker Compose configuration for local development.

Docker configuration will be defined in the applicable implementation phase.

---

## 5. Domain Boundaries

The following domain areas are identified from the Product Requirements Specification.
No implementations are created here. This section defines conceptual responsibility only.

### 5.1 Patient

**Responsibility:** Represents the subject of a prior-authorization workflow.
Holds identity and reference data retrieved from the synthetic EHR.

**Does NOT:** Make clinical decisions about the patient. Does not contain medical assessment.

**Relationships:** Referenced by Authorization. Retrieved via the PatientRepository port.

---

### 5.2 Authorization

**Responsibility:** Represents a single MRI prior-authorization case from initiation to verified outcome.
Owns the lifecycle of one authorization attempt: goal, state, submission reference, and final result.

**Does NOT:** Determine whether an MRI is medically necessary. Does not hold insurance policy rules.

**Relationships:** References Patient, InsurancePlan, Workflow. Subject of Submission and Verification.

---

### 5.3 Workflow

**Responsibility:** Represents the execution state of an authorization process.
Tracks the current state, the history of state transitions, and the conditions that must be
met before a transition may occur.

**Does NOT:** Execute transitions autonomously. State transitions are driven by the application layer,
validated by safety controls, and persisted by infrastructure.

**Relationships:** Belongs to Authorization. Produces WorkflowEvents.

---

### 5.4 Insurance

**Responsibility:** Represents the patient's insurance plan and insurer identity, as retrieved
from the synthetic insurance system.

**Does NOT:** Determine coverage decisions. Does not contain the prior-authorization policy rules
(those belong to Policy).

**Relationships:** Referenced by Authorization. Retrieved via the InsurancePlanRepository port.

---

### 5.5 Policy

**Responsibility:** Represents the prior-authorization requirements for a specific MRI procedure
under a specific insurance plan. Retrieved from the synthetic policy repository via RAG.

**Does NOT:** Interpret clinical necessity. Does not apply the policy (application layer does that).

**Relationships:** Consulted during document gathering and validation. Retrieved via the PolicyProvider port.

---

### 5.6 Document

**Responsibility:** Represents a supporting document required for the authorization request
(e.g., physician notes, referral, imaging history). Retrieved from the synthetic document repository.

**Does NOT:** Verify clinical content. Does not assess document validity (validation layer does that).

**Relationships:** Gathered during workflow execution. Required by Authorization. Retrieved via the DocumentRepository port.

---

### 5.7 Submission

**Responsibility:** Represents the act of submitting a prepared authorization request to the
simulated authorization portal. Records the submission reference and the portal's response.

**Does NOT:** Determine whether a submission was truly successful (Verification does that).

**Relationships:** Belongs to Authorization. Follows successful safety-gate passage.

---

### 5.8 Verification

**Responsibility:** Represents the independent check confirming that the expected administrative
outcome actually exists in the authoritative external system.

This is the mechanism that enforces the core safety principle:
the agent cannot say DONE; the environment must prove DONE.
(Ref: Product Requirements Specification §7, §12)

**Does NOT:** Rely on the original action's own response to determine success.

**Relationships:** Applied after Submission (and other critical actions). Uses the VerificationProvider port.

---

### 5.9 Escalation

**Responsibility:** Represents a human escalation request triggered when the agent or system
encounters a situation it cannot safely resolve autonomously.

Triggers include: ambiguous information, conflicting sources, failed safety gate,
required clinical decision, action exceeding authorized permissions, failed verification.
(Ref: Product Requirements Specification §10)

**Does NOT:** Resolve the escalated situation autonomously. Waits for human input.

**Relationships:** Can be triggered from Workflow at any state. Pauses autonomous execution.

---

### 5.10 Audit

**Responsibility:** Represents an immutable record of a significant system event: workflow transitions,
agent actions, tool invocations, validation results, safety-gate outcomes, verification results,
human escalations.
(Ref: Product Requirements Specification §14)

**Does NOT:** Affect workflow logic. Read-only record.

**Relationships:** Created by every significant domain event. Persisted by infrastructure.

---

## 6. Ports and Adapters

Ports are interfaces defined in the domain layer. Infrastructure adapters implement them.
The application layer uses ports, not adapters directly.

Detailed method contracts will be finalized in a later contract specification phase.
This section defines the conceptual responsibility of each port.

---

### 6.1 PatientRepository

**Responsibility:** Retrieve patient identity and reference information from the synthetic EHR.

**Input concept:** Patient identifier (provided by the user at workflow initiation).

**Output concept:** Patient record (identity data, EHR reference).

**Failure behavior:** Returns a structured failure result when the patient cannot be found or the
synthetic EHR is unavailable. Does not throw unhandled exceptions into the application layer.

**Trust level:** Treated as a trusted-but-unverified source. Retrieved data must pass domain
validation before use.

**Access type:** Read only.

---

### 6.2 InsurancePlanRepository

**Responsibility:** Retrieve insurance plan details for a patient from the synthetic insurance system.

**Input concept:** Patient identifier or insurance member identifier.

**Output concept:** Insurance plan (insurer identity, plan type, member reference).

**Failure behavior:** Structured failure result on unavailability or not-found.

**Trust level:** Treated as a trusted-but-unverified source. Retrieved data must pass validation.

**Access type:** Read only.

---

### 6.3 PolicyProvider

**Responsibility:** Retrieve prior-authorization requirements for a specific procedure under a
specific insurance plan, using RAG-based retrieval over the synthetic policy repository.

**Input concept:** Procedure type (MRI), insurance plan reference.

**Output concept:** Authorization requirements (required documents, required information fields,
submission criteria).

**Failure behavior:** Structured failure result when requirements cannot be retrieved or are ambiguous.
Ambiguous requirements trigger escalation.

**Trust level:** Informational — retrieved policy content guides the workflow but is not the
authoritative determinant of compliance. Deterministic validation enforces compliance rules.

**Access type:** Read only.

---

### 6.4 DocumentRepository

**Responsibility:** Retrieve supporting documents required for the authorization request from the
synthetic document repository.

**Input concept:** Document reference identifiers (as specified by the policy requirements).

**Output concept:** Document records (content reference, metadata, type).

**Failure behavior:** Structured failure result for missing or inaccessible documents. Missing
required documents trigger escalation or workflow pause.

**Trust level:** Trusted-but-unverified source. Document metadata and content must be validated
before use.

**Access type:** Read only.

---

### 6.5 AuthorizationGateway

**Responsibility:** Submit a prepared prior-authorization request to the simulated authorization portal.

**Input concept:** Prepared authorization submission (patient data, clinical references, required documents, insurer target).

**Output concept:** Submission acknowledgment (reference number, initial status).

**Failure behavior:** Structured failure result on submission failure. Submission failure does not
mark the workflow complete. The original workflow state is preserved.

**Trust level:** The gateway's own submission response is NOT treated as authoritative proof of
success. Independent verification is required. (Ref: Product Requirements Specification §7, §12)

**Access type:** Write (submit) + Read (status query).

---

### 6.6 AuthorizationStatusGateway

**Responsibility:** Query the simulated authorization portal for the current status of a submitted
authorization request.

**Input concept:** Submission reference from AuthorizationGateway.

**Output concept:** Authorization status (pending, approved, denied, additional-information-requested, etc.).

**Failure behavior:** Structured failure result on unavailability. Workflow transitions to a
monitoring/retry state.

**Trust level:** Treated as an authoritative external source for status. Still subject to
independent verification for final outcome determination.

**Access type:** Read only.

---

### 6.7 VerificationProvider

**Responsibility:** Independently confirm that an expected administrative outcome actually exists
in the authoritative simulated healthcare system, using a different access path from the
action that produced the claimed result.
(Ref: Product Requirements Specification §12)

**Input concept:** Expected outcome specification (e.g., authorization approved for patient X, reference Y).

**Output concept:** Verification result (confirmed, not-confirmed, error).

**Failure behavior:** Unconfirmed or error results prevent workflow completion. Escalation is triggered.

**Trust level:** This port is the mechanism that enforces the DONE principle. Its result is treated
as authoritative for completion determination.

**Access type:** Read only (independent from the write path).

---

## 7. Agent Boundary

### 7.1 What the Agent Is

The agent is a **reasoning component**. It:
- Interprets the user's prior-authorization goal.
- Reasons about what information is needed and what actions are permitted.
- Selects among authorized application-layer tool functions.
- Inspects tool results to determine the next step.
- Requests escalation when it cannot safely proceed.

### 7.2 Boundary Diagram

```
┌────────────────────────────────────────────────────────────┐
│                       AGENT LAYER                          │
│                  (services/agent)                          │
│                                                            │
│   Claude LLM (via Amazon Bedrock)                          │
│   AWS Strands Agents SDK runtime                           │
│                                                            │
│   Receives:  Workflow context (sanitized, from App Layer)  │
│   Calls:     Authorized tool functions only                │
│   Returns:   Tool invocation requests                      │
│                                                            │
│   ┌────────────────────────────────────────────────────┐  │
│   │               AUTHORIZED TOOL FUNCTIONS            │  │
│   │          (defined in packages/application)         │  │
│   │                                                    │  │
│   │  get_patient_record()                              │  │
│   │  get_insurance_plan()                              │  │
│   │  get_authorization_requirements()                  │  │
│   │  get_required_documents()                          │  │
│   │  validate_authorization_package()                  │  │
│   │  submit_authorization_request()                    │  │
│   │  get_authorization_status()                        │  │
│   │  verify_authorization_outcome()                    │  │
│   │  request_human_escalation()                        │  │
│   │                                                    │  │
│   │  NOTE: Tool names are illustrative.                │  │
│   │  Exact names are defined in the tool specification │  │
│   │  phase. Each tool routes through the Application   │  │
│   │  Layer and its safety controls.                    │  │
│   └────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            │
                            │  tool invocation
                            ▼
┌────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                        │
│            (packages/application)                          │
│                                                            │
│   Validates permissions → runs safety gates →              │
│   invokes domain logic → invokes infrastructure port →     │
│   returns structured result to agent                       │
└────────────────────────────────────────────────────────────┘
```

### 7.3 What the Agent May Do

- Interpret the prior-authorization goal supplied by the user.
- Reason about workflow progress based on tool results.
- Select which authorized tool to invoke next.
- Inspect tool results to determine the next permitted action.
- Request human escalation when uncertainty, conflict, or safety failure is detected.
- Recognize when required information is missing or inconsistent.

### 7.4 What the Agent May NOT Do

| Prohibited Action                              | Reason                                           |
|------------------------------------------------|--------------------------------------------------|
| Access PostgreSQL directly                     | Database access belongs to the infrastructure layer |
| Execute arbitrary SQL                          | Would bypass all safety controls                 |
| Directly modify application state              | State changes belong to the application layer    |
| Call simulated external systems directly       | Must use authorized tools only                   |
| Bypass input validation                        | Validation is deterministic and mandatory        |
| Bypass permission checks                       | Permissions are enforced by the safety layer     |
| Bypass safety gates                            | Safety gates are non-negotiable                  |
| Access filesystem or network unrestricted      | Violates least privilege (Ref: PRS §19)          |
| Make clinical decisions                        | HealthFlow is administrative only (Ref: PRS §8)  |
| Declare workflow complete without verification | Violates the core safety principle (Ref: PRS §7) |
| Hold authoritative workflow state              | State belongs to PostgreSQL (Ref: PRS §19)       |

### 7.5 Tool Invocation Path

```
Agent selects tool
    ↓
Strands SDK invokes application-layer tool function
    ↓
Tool function runs: permission check → validation → safety gate
    ↓
Tool function invokes domain logic / infrastructure port
    ↓
Structured result returned to agent
    ↓
Agent reasons over result; selects next action
```

Each step in the invocation path is deterministic up to the domain/infrastructure boundary.
The LLM receives only the structured tool result, not raw database output or raw external-system responses.

---

## 8. Safety Architecture

### 8.1 Safety Flow

```
Incoming request / agent tool invocation
    │
    ▼
┌────────────────────────────────────┐
│  1. INPUT VALIDATION               │
│  (packages/safety)                 │
│                                    │
│  Deterministic. Rule-based.        │
│  Checks: required fields present,  │
│  field formats valid, types        │
│  correct, no injection patterns.   │
│                                    │
│  LLM cannot bypass.                │
└────────────────┬───────────────────┘
                 │ PASS
                 ▼
┌────────────────────────────────────┐
│  2. PERMISSION CHECK               │
│  (packages/safety)                 │
│                                    │
│  Is this action authorized for     │
│  the current workflow state and    │
│  the current actor?                │
│                                    │
│  Least privilege enforced.         │
│  LLM cannot bypass.                │
└────────────────┬───────────────────┘
                 │ AUTHORIZED
                 ▼
┌────────────────────────────────────┐
│  3. BUSINESS-RULE VALIDATION       │
│  (packages/domain)                 │
│                                    │
│  Are domain invariants satisfied?  │
│  Is the data internally consistent?│
│  Are required documents present?   │
│  Are conflicting records detected? │
│                                    │
│  Deterministic. Not LLM-driven.    │
└────────────────┬───────────────────┘
                 │ VALID
                 ▼
┌────────────────────────────────────┐
│  4. SAFETY GATE                    │
│  (packages/safety)                 │
│                                    │
│  Pre-action guard. Must pass       │
│  before any write action proceeds. │
│                                    │
│  Examples:                         │
│  - No clinical data invented       │
│  - Required verification possible  │
│  - Submission data complete        │
│                                    │
│  Deterministic. Not LLM-driven.    │
└────────────────┬───────────────────┘
                 │ PASS
                 ▼
┌────────────────────────────────────┐
│  5. ACTION EXECUTION               │
│  (packages/application/            │
│   packages/infrastructure)         │
│                                    │
│  The action is performed.          │
│  State is persisted.               │
│  Domain event is published.        │
└────────────────┬───────────────────┘
                 │ COMPLETED
                 ▼
┌────────────────────────────────────┐
│  6. INDEPENDENT VERIFICATION       │
│  (VerificationProvider port)       │
│                                    │
│  The expected outcome is           │
│  confirmed using the authoritative │
│  external source via a different   │
│  access path.                      │
│                                    │
│  FAIL → escalate / do not complete │
│  PASS → workflow may progress      │
└────────────────────────────────────┘
```

### 8.2 LLM Reasoning vs. Deterministic Enforcement

| Control Type           | Implemented By     | Bypassed By LLM? |
|------------------------|--------------------|------------------|
| Input validation       | Safety layer (code)| NO               |
| Permission check       | Safety layer (code)| NO               |
| Business-rule validation | Domain layer (code) | NO             |
| Safety gate            | Safety layer (code)| NO               |
| Independent verification | VerificationProvider (code) | NO   |
| Workflow state transition | Domain + Application (code) | NO  |
| Reasoning about next step | LLM (Claude)    | N/A — LLM role   |
| Tool selection         | LLM (Claude)       | N/A — LLM role   |

Safety controls are implemented in code, not in prompts.
A prompt instructing the LLM to perform safety checks is insufficient.

### 8.3 Medical Safety Boundary

The agent must not:
- Diagnose patients
- Recommend treatments
- Determine MRI medical necessity
- Override physician judgment
- Invent or alter clinical information

(Ref: Product Requirements Specification §8)

These prohibitions are enforced by:
1. The absence of tools that allow clinical decisions.
2. The safety gate preventing any clinical content from being written to submissions.
3. Structural boundaries that limit what information the LLM receives.

---

## 9. Trust Boundaries

### 9.1 Trust Classification

| Information Source         | Trust Classification | Authoritative For                     |
|----------------------------|---------------------|---------------------------------------|
| User input                 | Untrusted           | Nothing — must be validated           |
| LLM output                 | Untrusted           | Nothing — LLM does not hold state     |
| Tool call result           | Semi-trusted        | Informational, subject to validation  |
| PostgreSQL application state | Trusted            | Workflow state, audit records         |
| Synthetic EHR response     | Trusted-but-external | Patient identity (requires validation) |
| Synthetic Insurance response | Trusted-but-external | Insurance plan (requires validation) |
| Synthetic Policy repository | Informational       | Authorization requirements (informational, not binding) |
| Synthetic Document repository | Trusted-but-external | Document content (requires validation) |
| Synthetic Authorization Portal | Authoritative-external | Submission reference, status |
| VerificationProvider result | Authoritative       | Final workflow outcome determination  |

### 9.2 Key Rules

- User input must be validated before entering any domain or application logic.
- LLM output (reasoning, planned actions) does NOT directly change state. It results in tool calls,
  which are validated independently.
- Tool results are structured responses from application-layer functions. They are informational
  for the LLM but the underlying data has already been validated by the application layer before
  being returned.
- The VerificationProvider result is the only authoritative source for determining workflow completion.

---

## 10. Source of Truth

| Concept                             | Authoritative Source                          |
|-------------------------------------|-----------------------------------------------|
| Workflow state                      | PostgreSQL (application database)             |
| Authorization case data             | PostgreSQL (application database)             |
| Audit records                       | PostgreSQL (application database)             |
| Patient identity                    | Synthetic EHR (via PatientRepository port)    |
| Insurance plan                      | Synthetic Insurance System (via InsurancePlanRepository port) |
| Authorization requirements          | Synthetic Policy Repository (via PolicyProvider port) |
| Required documents                  | Synthetic Document Repository (via DocumentRepository port) |
| Submission status                   | Synthetic Authorization Portal (via AuthorizationStatusGateway port) |
| Final outcome (DONE determination)  | VerificationProvider result from authoritative external source |
| LLM / agent context                 | NOT authoritative for any decision            |

**The LLM is explicitly NOT the source of truth for any data, state, or outcome.**

The LLM receives structured context prepared by the application layer and reasons over it.
It does not persist state, does not determine verification outcomes, and does not override
deterministic validation results.

---

## 11. Workflow State Architecture

### 11.1 Design Requirements

The workflow state machine must support:
- Explicit, named states (no implicit or inferred state)
- Deterministic, validated transitions (a transition may only occur if its preconditions are met)
- Persistence (state is persisted to PostgreSQL after every transition)
- Recovery (an interrupted workflow can resume from its last persisted state)
- Auditability (every transition is recorded with timestamp, actor, and result)
- Failure states (transitions to failure are first-class states, not exceptions)
- Escalation states (human escalation is a first-class workflow state)
- Resumability (after escalation resolution, the workflow can continue from where it paused)

### 11.2 State Ownership

Workflow state is owned by the domain layer (state definitions and transition rules)
and persisted by the infrastructure layer (PostgreSQL).

The agent does not own, modify, or query workflow state directly.
The application layer reads and writes workflow state through domain logic
and infrastructure ports.

### 11.3 State Definitions

Detailed state enumeration and transition graph will be defined in the workflow
specification phase, which is a later approved phase.

No states are invented here beyond what is justified by the requirements:
- An initial state (workflow created, goal received)
- Intermediate states (information gathering, validation, preparation, submission, monitoring, follow-up)
- A verification state (independent verification in progress)
- A completed state (only reachable after successful verification)
- Failure states
- Escalation state(s)

---

## 12. Data Flow

This section describes the expected end-to-end data flow for the MRI prior-authorization workflow.
No implementation is created here.

```
1. USER STARTS AUTHORIZATION
   ─────────────────────────
   User (doctor/admin) → Next.js → REST → FastAPI → Application Layer
   Application creates Authorization case in PostgreSQL (initial state).
   Agent is initialized with workflow context.

2. PATIENT IS IDENTIFIED
   ─────────────────────
   Agent selects: get_patient_record tool
   Application Layer: validates input → checks permission → invokes PatientRepository port
   Infrastructure: queries synthetic EHR
   Result: patient record returned to application → validated → returned to agent as structured result

3. INSURANCE IS CHECKED
   ─────────────────────
   Agent selects: get_insurance_plan tool
   Application Layer: validates input → checks permission → invokes InsurancePlanRepository port
   Infrastructure: queries synthetic insurance system
   Result: insurance plan returned → validated → returned to agent

4. REQUIREMENTS ARE RETRIEVED
   ───────────────────────────
   Agent selects: get_authorization_requirements tool
   Application Layer: invokes PolicyProvider port (RAG-based retrieval from synthetic policy repo)
   Infrastructure: embedding query → pgvector → policy chunks retrieved
   Result: authorization requirements returned → returned to agent

5. DOCUMENTS ARE GATHERED
   ────────────────────────
   Agent selects: get_required_documents tool (one or more calls)
   Application Layer: invokes DocumentRepository port
   Infrastructure: queries synthetic document repository
   Result: documents retrieved → validated → returned to agent

6. INFORMATION IS VALIDATED
   ──────────────────────────
   Agent selects: validate_authorization_package tool
   Application Layer: runs deterministic domain validation
   Safety Layer: validates all fields, checks consistency, identifies missing information
   Result: validation result (PASS / FAIL with details) returned to agent
   If FAIL: agent may gather more information or trigger escalation

7. AUTHORIZATION IS PREPARED
   ───────────────────────────
   Application Layer: prepares authorization submission package (deterministic, not LLM-authored)
   Safety Gate: validates the prepared package before submission is allowed

8. SAFETY CHECKS RUN
   ───────────────────
   Safety Layer: runs pre-submission safety gate
   Checks: no invented clinical data, package complete, verification possible
   FAIL → workflow pauses, escalation triggered
   PASS → submission authorized

9. AUTHORIZATION IS SUBMITTED
   ────────────────────────────
   Agent selects: submit_authorization_request tool
   Application Layer: invokes AuthorizationGateway port
   Infrastructure: submits to synthetic authorization portal
   Result: submission acknowledgment (reference, initial status)
   State: workflow transitions to monitoring state in PostgreSQL

10. STATUS IS MONITORED
    ─────────────────────
    Agent selects: get_authorization_status tool (periodically)
    Application Layer: invokes AuthorizationStatusGateway port
    Infrastructure: queries synthetic authorization portal
    Result: current status returned

11. FOLLOW-UP IS HANDLED
    ──────────────────────
    If status = additional-information-requested:
    Agent reasons over requirements, gathers additional information
    Additional validation and safety gate run before re-submission

    If status = denied or unresolvable:
    Escalation triggered

12. FINAL RESULT IS INDEPENDENTLY VERIFIED
    ─────────────────────────────────────────
    Agent selects: verify_authorization_outcome tool
    Application Layer: invokes VerificationProvider port
    Infrastructure: queries authoritative external source via independent path
    Result: CONFIRMED or NOT-CONFIRMED
    CONFIRMED → workflow transitions to completed state in PostgreSQL
    NOT-CONFIRMED → escalation triggered; workflow does NOT complete
```

---

## 13. External System Architecture

### 13.1 Design Principle

All simulated external system interactions are mediated by the infrastructure layer
through port interfaces defined in the domain layer.

The application layer never calls simulated systems directly.
The agent never calls simulated systems directly.

```
Agent (reasoning)
    ↓ tool invocation
Application Layer (orchestration + safety)
    ↓ port interface
Infrastructure Adapter
    ↓ HTTP / in-process call
Synthetic External System
```

### 13.2 Simulated Systems

| System                           | Port Interface              | Notes                                          |
|----------------------------------|-----------------------------|------------------------------------------------|
| Synthetic EHR                    | PatientRepository           | Deterministic, controllable test data          |
| Synthetic Insurance System       | InsurancePlanRepository     | Deterministic, controllable test data          |
| Synthetic Policy Repository      | PolicyProvider (via RAG)    | Deterministic policy documents + pgvector      |
| Synthetic Document Repository    | DocumentRepository          | Deterministic, controllable test data          |
| Synthetic Authorization Portal   | AuthorizationGateway + AuthorizationStatusGateway + VerificationProvider | Deterministic responses |

### 13.3 Determinism Requirement

Simulated systems must be deterministic and controllable to support reproducible testing
and benchmarking. (Ref: Product Requirements Specification §13)

Detailed simulated-system behavior will be defined in the simulated systems specification,
which is a later approved phase.

### 13.4 Independence of VerificationProvider

The VerificationProvider must use an access path that is logically independent from the
AuthorizationGateway write path. This prevents a single point of failure from falsely
confirming a successful submission. (Ref: Product Requirements Specification §12)

---

## 14. Database Architecture

### 14.1 Responsibility

PostgreSQL (via SQLAlchemy 2.x) is the authoritative store for all HealthFlow application state:
- Authorization cases
- Workflow state and transitions
- Audit records
- Submission references
- Verification records
- Escalation records

### 14.2 Persistence Boundary

The database is accessed exclusively through repository implementations in `packages/infrastructure`.
No other layer may construct database sessions, query the database, or write to the database.

### 14.3 Repository Boundary

Each repository implementation satisfies one or more domain port interfaces.
The domain layer defines what data the application needs. The infrastructure layer
defines how it is persisted.

SQLAlchemy model types must not leak into the domain or application layers.
The infrastructure layer maps between SQLAlchemy models and domain types.

### 14.4 Migration Ownership

All schema changes are managed through Alembic migrations in the `migrations/` directory.
No schema change may occur outside of a migration.

Database schema will be defined in the schema specification phase.

### 14.5 Transaction Boundary

Transactions are managed by the infrastructure layer. A single use-case execution
should occur within a single transaction where atomicity is required.

The application layer signals the boundary of a logical operation. The infrastructure
layer is responsible for transaction management.

### 14.6 Audit Data

Audit records are immutable once written. The infrastructure layer must enforce this.
Audit records are separate from mutable application state records.

### 14.7 Application State vs. External System State

PostgreSQL stores HealthFlow's own representation of the authorization lifecycle.
It does not replicate external system data wholesale. Submission references and
verification results link internal state to external system state without embedding
the external system as a table.

---

## 15. RAG Architecture

### 15.1 Purpose

Policy retrieval uses Retrieval-Augmented Generation (RAG) to find the relevant
prior-authorization requirements for a given procedure and insurance plan.
This is mediated by the PolicyProvider port.

### 15.2 Pipeline

```
Synthetic Policy Documents (source documents)
    ↓ offline processing (document ingestion pipeline)
Text Chunking
    ↓
Embedding Generation (Amazon Bedrock embedding model — model to be specified)
    ↓
pgvector (stored in PostgreSQL)
    ↓
Query-time: procedure + plan context → embedding query
    ↓
Similarity Retrieval (pgvector)
    ↓
Retrieved policy chunks
    ↓
PolicyProvider port (packages/infrastructure adapter)
    ↓
Application Layer
    ↓
Agent receives structured authorization requirements
```

### 15.3 What RAG Is Authorized For

- Retrieving the prior-authorization requirements for a specific MRI procedure and insurance plan.
- Providing informational policy content to the application layer for validation rule construction.

### 15.4 What RAG Is NOT Authoritative For

- RAG results are **informational**, not binding determinations.
- RAG results must be used to guide deterministic validation — they do not replace it.
- The LLM may not use RAG results to invent policy requirements that are not present
  in the retrieved content.
- RAG results are not the authoritative source of truth for authorization approval decisions.

### 15.5 Embedding Model

The specific embedding model to be used will be defined in the RAG implementation specification.
The choice must be compatible with Amazon Bedrock and pgvector.

---

## 16. API Architecture

### 16.1 Responsibility

The FastAPI application in `apps/api` is the HTTP boundary between the frontend and
the application layer.

### 16.2 Versioning

API versioning strategy: URL path prefix versioning (e.g., `/api/v1/...`).

This allows non-breaking evolution of the API and permits future API versions without
disrupting existing clients.

### 16.3 Request/Response Boundary

- All request bodies are Pydantic models validated at the API boundary.
- All responses are serialized Pydantic models.
- Raw domain types or SQLAlchemy models must never appear in API responses.
- Sensitive patient data fields must not be included in responses unless explicitly required.

### 16.4 Authentication Boundary

Authentication will be specified in a later phase. The API layer is responsible for
enforcing authentication (all routes that access HealthFlow data must require authentication).

Authentication details are NOT invented at this phase.

### 16.5 Authorization Boundary

Authorization (which user can perform which action) will be coordinated by the
safety/application layers. The API layer is responsible for passing authenticated
identity to the application layer.

### 16.6 Error Handling

All errors are serialized as structured JSON responses with:
- An error code (machine-readable)
- An error message (human-readable)
- No stack traces or internal implementation details in production responses

### 16.7 Relationship to Application Services

Each API route delegates entirely to an application-layer use case.
No business logic lives in route handler functions.

Detailed endpoint definitions will be created in the API contract specification phase.

---

## 17. Frontend Architecture

### 17.1 Responsibility

The Next.js application in `apps/web` provides the user interface for:
- Initiating a prior-authorization workflow (submitting the goal)
- Viewing the current authorization case and its status
- Monitoring agent activity (what the agent is doing, what tools it is calling)
- Viewing the workflow timeline (states reached, transitions made)
- Responding to human escalation prompts
- Viewing verification results
- Viewing error states and failure explanations

### 17.2 Patient Interaction

The frontend collects the minimum required information from the user to initiate the workflow.
It does not ask the user to make clinical decisions. It does not expose raw patient data unnecessarily.

### 17.3 Authorization Case View

Displays the current state of the authorization case: patient reference, insurer, workflow state,
submission reference (if submitted), and final result.

### 17.4 Agent Activity

Provides a real-time or near-real-time view of what the agent is doing:
which tool it selected, what result it received, and what it is doing next.

### 17.5 Workflow Timeline

A chronological display of workflow state transitions, each with a timestamp and description.

### 17.6 Human Escalation

When the system triggers an escalation, the frontend presents the escalation reason
and the available human actions. Human input is submitted back through the API.

### 17.7 Verification Result

Displays the independent verification outcome: confirmed, not confirmed, or error.

### 17.8 Error State

Displays meaningful error information when a workflow fails or an action cannot proceed.
Does not expose internal system details.

### 17.9 Business Rule Prohibition

The frontend must not contain business rules. All business rules are enforced by the
domain and safety layers. The frontend renders data returned by the API layer.

---

## 18. Observability Architecture

### 18.1 Categories of Observable Information

| Category            | Description                                                       | Sensitive? |
|---------------------|-------------------------------------------------------------------|------------|
| Operational logs    | Application startup, HTTP requests, errors, infrastructure events | Low        |
| Workflow events     | Workflow initiation, state transitions, completion/failure        | Medium     |
| Agent events        | Tool selections, tool invocations, tool results (sanitized)       | Medium     |
| Validation events   | Validation results (pass/fail, not detailed patient data)         | Medium     |
| Safety gate events  | Safety gate results (pass/fail)                                   | Medium     |
| Audit records       | Immutable records of all significant actions                      | High       |
| Human escalations   | Escalation triggers and resolution                                | High       |
| Verification events | Verification results                                              | Medium     |

### 18.2 Operational Logs vs. Audit Records

**Operational logs:** Structured text/JSON output to stdout or a log aggregation service (CloudWatch).
Used for debugging and monitoring. May be rotated and expired.

**Audit records:** Immutable records persisted to PostgreSQL. Used for compliance, traceability,
and forensic review. Must not be deleted or overwritten by the application.

### 18.3 Sensitive Data in Logs

Sensitive information (patient identifiers, clinical details, credentials) must not appear
unnecessarily in operational logs. Use reference identifiers or opaque tokens instead of
raw sensitive values in log output. (Ref: Product Requirements Specification §14)

### 18.4 Required Observable Events

Per Product Requirements Specification §14, the following must be traceable:
- Workflow initiation
- Workflow state transitions
- Agent actions (tool selections and invocations)
- Tool call results
- Validation results
- Safety-gate results
- Human escalations
- External-system responses
- Verification results
- Final workflow state

### 18.5 Infrastructure

Local development: structured JSON logs to stdout.
Production: AWS CloudWatch Logs (pending infrastructure phase specification).

---

## 19. Security Architecture

### 19.1 Least Privilege

- The agent operates with only the tool functions authorized for the current workflow phase.
- Infrastructure adapters have only the database permissions and external-system permissions
  required for their function.
- Each component receives only the secrets and configuration it needs.
- (Ref: Product Requirements Specification §11, §21)

### 19.2 Secret Handling

- No credentials or secrets may be committed to source control.
- Secrets are provided through environment variables in local development (`.env`, git-ignored).
- In production, secrets are retrieved from AWS Secrets Manager at runtime.
- Secret values must never appear in logs.
- (Ref: Product Requirements Specification §21)

### 19.3 Permissions Model

Agent tool permissions are defined by the workflow phase. The safety layer enforces
what actions are permitted in the current state. The agent cannot self-grant permissions.

### 19.4 Data Boundaries

- Synthetic data must not mix with any real patient data.
- The application must be able to distinguish synthetic from real data at the data source level.
- (Ref: Product Requirements Specification §4)

### 19.5 Tool Access Controls

The agent receives only the tool functions that correspond to authorized workflow actions.
It does not receive tools for arbitrary database access, filesystem access, or unrestricted
network calls. (Ref: Product Requirements Specification §19)

### 19.6 Logging Safety

Sensitive data must not appear in operational logs. Use opaque references.
(Ref: Product Requirements Specification §14, §21)

### 19.7 Trusted vs. Untrusted Data

The application must separate trusted data (PostgreSQL application state, verified external data)
from untrusted data (user input, LLM output, unvalidated external responses) and apply
appropriate validation before using untrusted data.

### 19.8 Environment Separation

Development, testing, and production environments must be isolated.
Production healthcare credentials (real) are prohibited for the MVP.
(Ref: Product Requirements Specification §21)

---

## 20. Error and Failure Architecture

### 20.1 Failure Classification

| Failure Type                          | Response                                                    |
|---------------------------------------|-------------------------------------------------------------|
| Missing required information          | Workflow pauses; agent attempts to gather; escalate if unresolvable |
| Invalid information (validation fail) | Workflow pauses; specific failure returned to agent         |
| Conflicting information               | Escalation triggered; human resolves conflict               |
| Tool failure (transient)              | Structured failure result to agent; agent may retry (retry policy TBD in later phase) |
| External-system unavailable           | Structured failure result; workflow transitions to wait/retry state |
| Timeout                               | Structured failure result; workflow state preserved; escalation if persistent |
| Submission failure                    | Submission NOT marked complete; workflow state preserved; structured failure to agent |
| Additional-information request        | Workflow continues; agent gathers additional information     |
| Authorization denied                  | Workflow transitions to denied state; escalation for human review |
| Verification failure (not confirmed)  | Workflow does NOT complete; escalation triggered             |
| Unexpected state                      | Escalation triggered; workflow paused pending human review  |

### 20.2 Failure Principles

- No failure silently marks the workflow as complete.
- All failures produce a structured result that is persisted to the audit log.
- Failures are first-class states, not unhandled exceptions.
- The application layer catches infrastructure exceptions and converts them to structured failures
  before returning them to the agent.
- The agent is never given a raw exception trace.

### 20.3 Retry Policy

Retry policies for transient tool and external-system failures will be defined in the
implementation specification phase. No retry policy is invented at this stage.

---

## 21. Scalability

### 21.1 Requirement

The architecture must support future administrative workflows (beyond MRI prior authorization)
without redesigning the existing system.
(Ref: Product Requirements Specification §20)

### 21.2 Strategy

New workflows are introduced through:

1. **New use cases in the application layer** — each workflow has its own use case set.
   MRI prior-authorization use cases are not modified to accommodate new workflows.

2. **New or extended port interfaces** — if a new workflow requires a new external-system
   interaction, a new port interface is defined. Existing ports are not polluted with
   workflow-specific logic.

3. **New workflow state definitions** — each workflow has its own state machine definition
   in the domain layer. Existing workflow state definitions are not modified.

4. **New agent tool functions** — new workflows expose their own set of authorized tool
   functions. Existing tools are not modified.

5. **New infrastructure adapters (if needed)** — new external systems get new adapters.

### 21.3 What Does NOT Change for New Workflows

- The safety architecture is reused. Safety controls are applied identically.
- The verification principle is reused. All workflows must independently verify outcomes.
- The observability architecture is reused.
- The database persistence architecture is reused (new tables, not a new database).
- The API architecture is reused (new routes, not a new API).

### 21.4 Isolation

MRI prior-authorization workflow code is isolated from future workflow code.
A bug in a future workflow must not affect the MRI prior-authorization workflow.

---

## 22. Architectural Rules

The following are hard rules. No implementation phase may violate them.

### 22.1 Dependency Rules

- **Domain → Infrastructure: PROHIBITED.** The domain layer must have no dependency on any infrastructure library.
- **Agent → Database: PROHIBITED.** The agent may not directly access PostgreSQL.
- **Frontend → Database: PROHIBITED.** The frontend communicates only with the API layer.
- **API routes → Business logic (inline): PROHIBITED.** Route handlers delegate to application use cases.
- **Infrastructure logic → Domain entities: PROHIBITED.** Infrastructure implements domain ports; domain entities do not know about infrastructure.
- **Any layer → Safety bypass: PROHIBITED.** Safety controls are non-negotiable.

### 22.2 Safety Rules

- **Safety checks must be implemented in deterministic code, not in LLM prompts.**
- **No workflow may complete without independent verification.**
- **Tool responses alone are not sufficient proof of action success.**
- **The LLM is not a substitute for validation, authorization, or verification.**

### 22.3 Data Rules

- **No real healthcare data at any stage.** Development, testing, and demonstration use synthetic data exclusively.
- **Synthetic data must be identifiable as synthetic.**
- **The LLM is not the source of truth for any application data or state.**

### 22.4 Code Quality Rules

- **No duplicate business logic across layers.**
- **No dead code in production packages.**
- **No framework-specific types in the domain or application layers.**
- **No credentials in source code or committed configuration.**

### 22.5 Agent Rules

- **The agent may not invoke tools that grant unrestricted system access.**
- **The agent may not hold or persist application state.**
- **The agent may not declare completion — only verification can authorize completion.**
