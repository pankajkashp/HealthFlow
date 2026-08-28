# HealthFlow

**MVP:** MRI Prior Authorization

---

## Purpose

HealthFlow is an autonomous AI agent for doctors and healthcare administrative staff.

It executes permitted MRI prior-authorization administrative workflows autonomously:
receiving a prior-authorization goal, gathering and validating required information from
authorized synthetic healthcare systems, preparing and submitting the administrative request,
monitoring its status, handling permitted routine follow-ups, and independently verifying
the final administrative outcome.

HealthFlow is designed to reduce repetitive administrative work while maintaining strict
safety, traceability, authorization, and human oversight.

---

## Key Principles

**Synthetic data only.**
HealthFlow uses synthetic healthcare data at every stage of development, testing, benchmarking,
and demonstration. Real patient information is never used.

**Autonomous administrative workflow.**
The agent owns the permitted workflow from goal to independently verified administrative outcome.
It does not perform medical diagnosis or make clinical decisions.

**Verification principle.**
The agent cannot declare an action complete. The environment must prove completion.
Every significant administrative action is independently verified using an authoritative source.

---

## Current Phase

**Phase 2 — Domain Model + Persistence Foundation (COMPLETE / PASS)**

- Phase 0A — Specification Foundation: PASS
- Phase 0B — Technical Architecture: PASS
- Phase 0C — Architecture Decisions: PASS
- Phase 1 — Engineering Foundation: PASS
- Phase 2 — Domain Model + Persistence Foundation: PASS

---

## Implementation Approach

Implementation follows controlled specifications.

Each phase of implementation requires:
1. An approved phase specification
2. Explicit authorization before work begins
3. Acceptance criteria verification before the phase is closed

The locked Product Requirements Specification is the authoritative source for all
product requirements: `docs/product/PRODUCT_REQUIREMENTS.md`.

---

## Repository Structure

```
docs/
├── product/          # Product Requirements Specification
├── architecture/     # Architecture decisions (future phases)
├── contracts/        # API and interface contracts (future phases)
├── engineering/      # Engineering governance
├── testing/          # Testing strategy (future phases)
└── phases/           # Phase specifications and status

apps/
├── api/              # Backend API application (future phases)
└── web/              # Frontend web application (future phases)

services/
└── agent/            # AI agent service (future phases)

packages/
├── domain/           # Domain layer (future phases)
├── application/      # Application layer (future phases)
├── infrastructure/   # Infrastructure layer (future phases)
├── safety/           # Safety controls (future phases)
└── shared/           # Shared utilities (future phases)

tests/
├── unit/
├── integration/
├── contract/
├── agent/
├── safety/
└── benchmark/

scripts/              # Development and operational scripts (future phases)
migrations/           # Database migrations (future phases)
docker/               # Container configuration (future phases)
```

---

## Technology Stack

Defined in the Product Requirements Specification (§17). Implementation is authorized in later phases.

| Category    | Technology                                           |
|-------------|------------------------------------------------------|
| Frontend    | Next.js, TypeScript, Tailwind CSS, shadcn/ui         |
| Backend     | Python, FastAPI, Pydantic                            |
| Agent       | AWS Strands Agents SDK                               |
| LLM         | Claude via Amazon Bedrock                            |
| Database    | PostgreSQL, SQLAlchemy 2.x, Alembic, pgvector        |
| Testing     | pytest, Vitest, React Testing Library, Playwright    |
| Infrastructure | Docker, Docker Compose, AWS                       |

---

## Engineering Governance

See `docs/engineering/` for:
- `AI_ENGINEERING_RULES.md` — Rules governing coding agent behavior
- `CODING_STANDARDS.md` — Production coding standards
- `NAMING_CONVENTIONS.md` — Domain-oriented naming rules
- `DEPENDENCY_POLICY.md` — Dependency approval requirements
