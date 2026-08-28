# HealthFlow — Requirements Traceability

**Version:** 1.0
**Phase:** 0B — Technical Architecture Specification
**Authority:** Product Requirements Specification v1.0

This document maps each major section of the Product Requirements Specification to the
architecture sections and decisions that satisfy it.

Legend:
- **SATISFIED** — The architecture explicitly addresses this requirement.
- **DEFERRED TO LATER PHASE** — The requirement is acknowledged but its implementation
  design requires a later specification phase (schema, API contract, auth, workflow states, etc.).
- **PENDING APPROVAL** — An architectural decision is needed that cannot be made
  from the current specification.

---

## Traceability Table

---

### PRS §1 — Specification Control

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Implementation must conform to the specification | All architecture documents | Architecture is derived from and constrained by the locked PRS. Every decision cites the PRS section it satisfies. | SATISFIED |
| Agent must not modify requirements | `docs/engineering/AI_ENGINEERING_RULES.md` Rule 3 | Established as an engineering rule in Phase 00, reinforced in architecture. | SATISFIED |
| Stop and report on unclear requirements | `ARCHITECTURE_DECISIONS.md` PENDING items | Architecture explicitly marks undecidable items as PENDING APPROVAL rather than guessing. | SATISFIED |

---

### PRS §2 — Project Overview

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Autonomous AI agent for doctors and admin staff | §7 Agent Boundary, §2.6 Agent Layer | The agent layer is defined as a controlled reasoning component. | SATISFIED |
| Executes permitted administrative workflows | §7, §2.3 Application Layer, §12 Data Flow | Application layer orchestrates the workflow; agent invokes authorized tools only. | SATISFIED |
| Safety, traceability, authorization, human oversight | §8 Safety Architecture, §9 Trust Boundaries, §18 Observability, §7.4 Agent Prohibitions | All four are addressed in distinct architecture sections. | SATISFIED |

---

### PRS §3 — MVP Scope (MRI Prior Authorization)

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Exactly one workflow: MRI Prior Authorization | §12 Data Flow, §21 Scalability | Data flow describes the MRI workflow. Scalability section defines how future workflows are added without disturbing MRI. | SATISFIED |
| End-to-end with synthetic data | §13 External System Architecture, §14 Database Architecture | All external interactions are through simulated systems. No real data dependencies exist. | SATISFIED |
| No medical diagnosis or clinical decisions | §8.3 Medical Safety Boundary, §7.4 Agent Prohibitions | Clinical decision-making is structurally prohibited by the absence of tools for it and explicit safety gate constraints. | SATISFIED |

---

### PRS §4 — Data Requirements

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Synthetic healthcare data only | §13 External System Architecture, §19.4 Data Boundaries | All five simulated systems use synthetic data. No production healthcare API dependencies. | SATISFIED |
| Data must be distinguishable from real | §19.4 Data Boundaries | The architecture notes this requirement. Exact labeling mechanism is defined in the simulated systems specification. | DEFERRED TO LATER PHASE |
| MVP must not require production healthcare data | §13, §19.8 Environment Separation | Production healthcare connections are explicitly prohibited at all phases. | SATISFIED |

---

### PRS §5 — Primary Users

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Doctors and healthcare admin staff | §17 Frontend Architecture, §16 API Architecture | Frontend is the user-facing entry point. Users initiate the workflow through the UI. | SATISFIED |
| User provides the authorization goal | §12 Data Flow (Step 1), §17.2 Patient Interaction | Workflow initiation starts with the user submitting a goal through the frontend. | SATISFIED |

---

### PRS §6 — Core Agent Behavior (14 capabilities)

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| 1. Understand the authorization goal | §7 Agent Boundary, §12 Step 1 | Agent receives workflow context and reasons over the goal. | SATISFIED |
| 2. Determine required information | §7 Agent Boundary, §12 Steps 2–5 | Agent selects tools to gather information; application layer provides results. | SATISFIED |
| 3. Retrieve through controlled tools | §7.5 Tool Invocation Path, §6 Ports and Adapters | All retrieval is through authorized tool functions → application layer → port interfaces. | SATISFIED |
| 4. Identify missing or inconsistent information | §12 Step 6, §8 Safety Flow (step 3) | Validation step identifies missing and inconsistent data before proceeding. | SATISFIED |
| 5. Gather supporting documentation | §6.4 DocumentRepository, §12 Step 5 | DocumentRepository port retrieves required documents. | SATISFIED |
| 6. Validate before use | §8 Safety Architecture (steps 1–3), §12 Step 6 | Deterministic validation runs before any action proceeds. | SATISFIED |
| 7. Prepare the authorization request | §12 Step 7, §2.3 Application Layer | Application layer (not the LLM) prepares the submission package deterministically. | SATISFIED |
| 8. Pass required safety checks | §8 Safety Flow (step 4 Safety Gate), §12 Step 8 | Safety gate must pass before submission. | SATISFIED |
| 9. Submit through simulated authorization system | §6.5 AuthorizationGateway, §12 Step 9 | AuthorizationGateway port submits to the synthetic portal. | SATISFIED |
| 10. Monitor request status | §6.6 AuthorizationStatusGateway, §12 Step 10 | Agent uses status tool; application queries AuthorizationStatusGateway. | SATISFIED |
| 11. Handle permitted routine follow-up | §12 Step 11, §20 Error/Failure Architecture | Follow-up on additional-information requests is handled; policy defined in later phase. | DEFERRED TO LATER PHASE (exact follow-up rules) |
| 12. Detect additional-information requests | §20 Error/Failure Table (additional-information row), §12 Step 11 | Detected through status monitoring and classified as a workflow continuation path. | SATISFIED |
| 13. Escalate situations requiring human judgment | §5.9 Escalation domain, §8 Safety Flow, §17.6 Human Escalation UI | Escalation is a first-class domain concept with UI support. | SATISFIED |
| 14. Independently verify final outcome | §6.7 VerificationProvider, §12 Step 12, AD-004 | VerificationProvider port enforces independent verification via a separate access path. | SATISFIED |

---

### PRS §7 — Critical Safety Principle (agent cannot say DONE)

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Actions are not themselves proof of completion | §8 Safety Flow (step 6), §10 Source of Truth, §7.4 last row | No workflow may complete without VerificationProvider CONFIRMED result. | SATISFIED |
| Independent verification required | §6.7 VerificationProvider, AD-004, §12 Step 12 | VerificationProvider uses a logically independent access path. | SATISFIED |
| Workflow marked complete only after verification | §11 Workflow State Architecture, §12 Step 12 | Completion is a database state reached only through a verified transition. | SATISFIED |

---

### PRS §8 — Medical Safety Boundary

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| No diagnosis, treatment recommendation, or clinical decision | §8.3 Medical Safety Boundary, §7.4 Agent Prohibitions, §22.2 Safety Rules | Absent tools + explicit safety gates prevent clinical content from entering submissions. | SATISFIED |
| HealthFlow handles administrative workflow only | §2 System Overview, §7 Agent Boundary | Architecture is defined entirely around administrative workflow. | SATISFIED |

---

### PRS §9 — Validation Requirements

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Deterministic validation | §8 Safety Architecture, §2.7 Safety Layer, AD-003 | Safety layer implements deterministic code-based validation; LLM cannot override. | SATISFIED |
| Detect missing, invalid, inconsistent, conflicting, unsupported data | §8 Safety Flow steps 1–3, §20 Error/Failure Architecture | All five data failure types are addressed in the safety flow and failure classification table. | SATISFIED |
| LLM must not bypass validation | §8.2 LLM vs Deterministic table, AD-003 | Validation runs in code before any action executes; LLM sees only the structured result. | SATISFIED |

---

### PRS §10 — Human Escalation

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Escalation supported | §5.9 Escalation domain, §17.6 Frontend Escalation, §8 Safety Flow | Escalation is a first-class domain concept and workflow state. | SATISFIED |
| Triggers: ambiguity, conflict, safety failure, clinical decision, permission exceeded, verification failure | §20 Error/Failure Architecture, §8 Safety Flow | All six escalation triggers are addressed in the failure architecture table. | SATISFIED |
| Human remains in control of critical decisions | §5.9 Escalation, §17.6 Frontend Escalation | Human input is required to resolve escalation; workflow pauses. | SATISFIED |
| Routine steps do not require human approval | §7 Agent Boundary (permitted actions), §12 Data Flow | Routine information retrieval and standard steps proceed autonomously. | SATISFIED |

---

### PRS §11 — Permissions

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Explicit permissions for agent actions | §8 Safety Flow step 2, §19.1 Least Privilege | Permission check is a mandatory step in the safety flow before every action. | SATISFIED |
| Least privilege | §19.1 Least Privilege, §22.5 Agent Rules | Agent receives only tools for the current workflow phase; IAM enforces infrastructure-level least privilege. | SATISFIED |
| Agent cannot bypass permission/validation/safety/workflow constraints | §8.2, §22.1, §22.2, AD-003 | Deterministic controls are enforced in code; agent receives structured results only. | SATISFIED |

---

### PRS §12 — Independent Verification

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Independent verification mechanism required | §6.7 VerificationProvider, AD-004 | VerificationProvider port is defined as a required, independent port. | SATISFIED |
| Must confirm actual administrative state | §6.7, §12 Step 12 | Verification queries the authoritative external system independently. | SATISFIED |
| Tool response claiming success is insufficient | §8 Safety Flow step 6, AD-004, §22.2 | Architecture explicitly prohibits treating tool responses as proof of completion. | SATISFIED |
| Logically independent from producing action | AD-004 | VerificationProvider uses a different access path from AuthorizationGateway. | SATISFIED |

---

### PRS §13 — Simulated Healthcare Systems

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| MVP uses simulated systems | §13 External System Architecture | Five simulated systems defined with port interfaces. | SATISFIED |
| Simulated environment: EHR, insurance, policy, document, portal | §13.2 Simulated Systems table | All five systems listed with corresponding port interfaces. | SATISFIED |
| Deterministic and controllable | §13.3 Determinism Requirement | Explicitly required; detailed behavior is deferred to simulated systems specification. | DEFERRED TO LATER PHASE (implementation behavior) |
| No real healthcare system dependency | §13, §19.8 Environment Separation | Real healthcare system dependencies are prohibited at all phases. | SATISFIED |

---

### PRS §14 — Observability

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Sufficient information to understand a workflow | §18 Observability Architecture | Workflow events, agent events, validation events, audit records all defined. | SATISFIED |
| List of traceable events | §18.4 Required Observable Events | All 11 events listed in the PRS are covered in the observability architecture. | SATISFIED |
| Sensitive data not unnecessarily exposed | §18.3, §19.6 Logging Safety | Sensitive data policy defined; operational logs use opaque references. | SATISFIED |

---

### PRS §15 — Benchmarking

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Synthetic test cases | §4.14 tests/benchmark | Benchmark tests directory is established. | SATISFIED |
| Measure actual performance (not qualitative claims) | §4.14 | Benchmark tests must produce actual measurements. | SATISFIED |
| Relevant metrics defined | §4.14 | 10 metrics from PRS §15 are named in the repository responsibility definition. | SATISFIED |
| Results only from actual executed tests | `AI_ENGINEERING_RULES.md` Rule 19 | Engineering rule prohibits claiming results without execution. | SATISFIED |

---

### PRS §16 — Testing

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Multiple test levels: unit, integration, contract, agent, safety, benchmark, frontend, e2e | §4.9–§4.14, repository structure | All 8 test levels have corresponding directories and defined responsibilities. | SATISFIED |
| Critical safety, permission, state, verification paths have automated tests | §4.13 tests/safety | Safety tests directory is established with this explicit requirement documented. | SATISFIED |

---

### PRS §17 — Technology Requirements

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui | §2.1 Presentation Layer, §4.2 apps/web | Technology designated for apps/web. | SATISFIED |
| Backend: Python, FastAPI, Pydantic | §2.2 API Layer, §4.1 apps/api | Technology designated for apps/api. | SATISFIED |
| Agent: AWS Strands Agents SDK | §2.6 Agent Layer, §4.3 services/agent | Technology designated for services/agent. | SATISFIED |
| LLM: Claude via Amazon Bedrock | §2.6, §4.3 | Designated in agent layer architecture. | SATISFIED |
| Database: PostgreSQL, SQLAlchemy 2.x, Alembic | §14 Database Architecture, §4.6 packages/infrastructure | Technology designated for infrastructure layer. | SATISFIED |
| Vector: pgvector | §15 RAG Architecture, AD-007 | pgvector designated for policy retrieval pipeline. | SATISFIED |
| Testing tools | §4.9–§4.14 | All testing tools designated for their respective test layers. | SATISFIED |
| Code quality tools | §4.4–§4.7 | Ruff, MyPy, ESLint, Prettier designated; configuration deferred to implementation phase. | DEFERRED TO LATER PHASE (configuration) |
| Infrastructure: Docker, Docker Compose, AWS | §4.18 docker, AD-010 | Infrastructure designated; configuration deferred to infrastructure phase. | DEFERRED TO LATER PHASE (configuration) |
| Potential AWS services | AD-010 | All 8 listed services are designated in AD-010 with their purpose. | SATISFIED |

---

### PRS §18 — Architecture Requirements

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| SOLID principles | §3 Dependency Direction, §2 Layer Responsibilities | Single responsibility (each layer has one responsibility), open/closed (new workflows extend, not modify), dependency inversion (ports and adapters). | SATISFIED |
| Clean architecture | §1 System Overview, §2 Layer Responsibilities, AD-001 | Full clean architecture with layered, inward dependencies. | SATISFIED |
| Separation of concerns | §2 Layer Responsibilities (each layer's must NOT section) | Each layer's prohibited actions enforce separation. | SATISFIED |
| Dependency inversion | §3 Dependency Direction, AD-001 | Domain defines ports; infrastructure implements them. | SATISFIED |
| Ports and adapters | §6 Ports and Adapters, AD-006 | All external system interactions are mediated by port interfaces. | SATISFIED |
| Explicit workflow state | §11 Workflow State Architecture, AD-005 | State is explicit, named, and persisted. | SATISFIED |
| Deterministic validation | §8 Safety Architecture, AD-003 | Validation is in deterministic code. | SATISFIED |
| Independent verification | §6.7 VerificationProvider, AD-004 | Separate port, separate access path. | SATISFIED |
| Least privilege | §19.1, §22.5 | Least privilege at agent tool level and infrastructure IAM level. | SATISFIED |
| Testability | §4.9–§4.14, §2 Layer Responsibilities | All layers are designed for isolation and testability via port injection. | SATISFIED |
| Observability | §18 Observability Architecture | Comprehensive observability architecture defined. | SATISFIED |
| Loose coupling | §3 Dependency Direction, §6 Ports and Adapters | Layers communicate through interfaces; infrastructure is replaceable. | SATISFIED |
| High cohesion | §2 Layer Responsibilities, §5 Domain Boundaries | Each layer and domain concept has a single, clear responsibility. | SATISFIED |
| Business logic independent of infrastructure | §3.2 Prohibited Dependencies | Domain and Application cannot depend on infrastructure directly. | SATISFIED |
| Domain and Application independent of frameworks | §4.4, §4.5, §3.2 | Explicit prohibited dependency lists for both layers. | SATISFIED |

---

### PRS §19 — Agent Architecture Boundary

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Agent is a reasoning component | §7 Agent Boundary, AD-002 | Agent defined as reasoning-only; does not hold state. | SATISFIED |
| Agent must not be database, state, source of truth, or substitute for validation/auth/verification | §7.4, §10 Source of Truth, AD-002 | All five prohibitions are explicitly stated in the agent boundary. | SATISFIED |
| Authoritative state belongs to application and simulated external systems | §10 Source of Truth | Source-of-truth table assigns authority to PostgreSQL and external systems, not the LLM. | SATISFIED |
| LLM must not have unrestricted DB/filesystem/network/external-system access | §7.4, §22.5 Agent Rules | Explicit prohibitions in agent boundary; tool invocation path mediates all access. | SATISFIED |

---

### PRS §20 — Scalability

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Architecture allows future workflows without redesign | §21 Scalability | Strategy defined: new use cases, new port interfaces, new state machines, new tools, new adapters. Existing code is not modified. | SATISFIED |
| New workflows through appropriate abstractions | §21.2 Strategy | Clean architecture layers are the abstractions. New workflows are additions, not modifications. | SATISFIED |

---

### PRS §21 — Security Requirements

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Least privilege | §19.1 | Defined for both agent tool access and infrastructure IAM. | SATISFIED |
| Explicit permissions | §8 Safety Flow step 2, §19.3 | Permission check is a mandatory safety flow step. | SATISFIED |
| Secure secret handling | §19.2 | Secrets Manager in production; environment variables locally; no secrets in source control. | SATISFIED |
| Controlled tool access | §7 Agent Boundary, §19.5 | Agent receives only authorized tools; no unrestricted access tools. | SATISFIED |
| Input validation | §8 Safety Flow step 1, §19.7 | Deterministic input validation is the first safety flow step. | SATISFIED |
| Auditability | §18 Observability, §5.10 Audit domain, §14.6 Audit Data | Immutable audit records defined in domain and infrastructure. | SATISFIED |
| Safe logging | §18.3, §19.6 | Sensitive data policy defined for operational logs. | SATISFIED |
| Separation of trusted/untrusted | §9 Trust Boundaries, §19.7 | Trust classification table and separation principle defined. | SATISFIED |
| No credentials in source control | §19.2, `AI_ENGINEERING_RULES.md` | Engineering rule prohibits committed credentials. | SATISFIED |
| No real healthcare credentials for MVP | §19.8 | Explicitly prohibited at all phases. | SATISFIED |

---

### PRS §22 — MVP Success Criteria

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| 1. Synthetic case created | §12 Step 1, §14 Database Architecture | Authorization case created in PostgreSQL at workflow initiation. | SATISFIED |
| 2. Agent understands the goal | §7 Agent Boundary, §12 Step 1 | Agent receives goal and reasons over it. | SATISFIED |
| 3. Agent retrieves via controlled tools | §7.5 Tool Invocation Path | All retrieval through authorized tools via application layer. | SATISFIED |
| 4. Deterministic validation | §8 Safety Architecture | Mandatory validation step in safety flow. | SATISFIED |
| 5. Authorization request prepared | §12 Step 7 | Application layer prepares submission deterministically. | SATISFIED |
| 6. Request submitted to simulated system | §6.5 AuthorizationGateway, §12 Step 9 | AuthorizationGateway port submits to synthetic portal. | SATISFIED |
| 7. Workflow can be monitored | §18 Observability, §17.5 Workflow Timeline | Observability architecture and frontend timeline support monitoring. | SATISFIED |
| 8. Permitted follow-up performed | §12 Step 11, §20 | Follow-up path is defined; exact rules deferred. | DEFERRED TO LATER PHASE |
| 9. Critical situations escalated | §5.9 Escalation, §8 Safety Flow | Escalation is a first-class state; all escalation triggers covered. | SATISFIED |
| 10. Final outcome independently verified | §6.7 VerificationProvider, AD-004 | Verification is a mandatory final step. | SATISFIED |
| 11. Never claims completion without verification | §7.4, §8 Safety Flow step 6, §22.2 | Architecture prohibits completion without VerificationProvider CONFIRMED. | SATISFIED |
| 12. Workflow observable and testable | §18 Observability, §4.9–§4.14 tests | Observability and test architecture cover all required events. | SATISFIED |

---

### PRS §23 — Explicit Non-Goals

| Non-Goal | Architecture Coverage | How Enforced | Status |
|---|---|---|---|
| No medical diagnosis | §8.3, §7.4 | No tools exist for it; safety gates block clinical content. | SATISFIED |
| No treatment recommendations | §8.3, §7.4 | Same as above. | SATISFIED |
| No clinical decision-making | §8.3, §7.4 | Same as above. | SATISFIED |
| No real patient data | §13, §19.4 | Simulated systems only; explicit prohibition in architecture. | SATISFIED |
| No real insurer integration | §13 | All external systems are synthetic/simulated. | SATISFIED |
| No real healthcare-provider integration | §13 | Same as above. | SATISFIED |
| No production healthcare deployment | §19.8 | Production healthcare credentials prohibited for MVP. | SATISFIED |
| No autonomous clinical decisions | §7.4, §8.3 | Structurally prevented by tool absence and safety gates. | SATISFIED |
| No unverified autonomous actions | §8 Safety Flow step 6, §22.2 | Independent verification is required before completion. | SATISFIED |
| No unsupported workflows | §21 Scalability | Only MRI prior authorization is implemented in the MVP. | SATISFIED |
| No unrestricted LLM access | §7.4, §19.5, §22.5 | Tool invocation path mediates all access; direct access is prohibited. | SATISFIED |

---

### PRS §25 — Change Control

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Specification is LOCKED | Architecture is derived from, not a replacement for, the PRS | Architecture cites the PRS throughout. | SATISFIED |
| Stop and report on requirement changes | `AI_ENGINEERING_RULES.md` Rules 3, 21, 23 | Engineering rules mandate stopping and reporting. | SATISFIED |

---

### PRS §26 — Product Principle

| Requirement | Architecture Coverage | How Satisfied | Status |
|---|---|---|---|
| Owns the workflow from goal to verified outcome | §12 Data Flow (complete flow) | Architecture covers all 12 steps from initiation to verification. | SATISFIED |
| Autonomy + Accuracy + Safety + Verification + Traceability | §7 Agent + §8 Safety + §6.7 Verification + §18 Observability | All five dimensions are addressed in distinct architecture sections. | SATISFIED |
