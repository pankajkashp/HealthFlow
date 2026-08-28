# Dependency Policy

**Project:** HealthFlow
**Authority:** Product Requirements Specification v1.0

This document governs the addition of dependencies to any HealthFlow package or application.

---

## Core Rule

A dependency may only be added when **all** of the following conditions are satisfied:

1. **It solves a documented requirement.**
   The requirement must be traceable to the Product Requirements Specification
   or an approved phase specification.

2. **It is compatible with the locked technology stack.**
   The locked technology stack is defined in Section 17 of the Product Requirements Specification.
   A dependency that conflicts with the locked stack requires explicit project-owner approval
   before it may be considered.

3. **It is actually needed.**
   Do not add a dependency speculatively or in anticipation of a future requirement.
   Add it when the requirement is approved and implementation is authorized.

4. **It does not duplicate an existing capability.**
   Before adding a dependency, verify that no already-approved dependency or
   standard library capability satisfies the requirement.

5. **Its version or version constraint can be controlled.**
   Pin or constrain the dependency version to prevent unexpected upgrades.
   Unpinned or wildcard versions are not permitted in production manifests.

6. **Its use is documented where appropriate.**
   When a non-obvious dependency is added, document why it was chosen
   in the relevant phase specification or in an inline comment at the point of use.

---

## Who May Approve a New Dependency

Coding agents may **not** add dependencies merely because they are convenient or familiar.

A new dependency requires explicit approval from the project owner.

---

## Prohibited Dependency Patterns

- No dependency may be added to enable a feature that has not been approved.
- No dependency may replace a capability already provided by an approved dependency.
- No dependency may be added to a production manifest if it is only needed for development or testing.
  Use the appropriate development/test dependency group.
- No dependency with a known critical security vulnerability may be introduced.
- No dependency that requires real healthcare credentials or production healthcare API access
  may be introduced at any phase.
  (Ref: Product Requirements Specification §21)

---

## Technology Stack Reference

The following dependencies are pre-approved by the locked technology stack
(Product Requirements Specification §17). Installation is authorized only in the
applicable implementation phase, not in Phase 0.

| Category         | Approved Technology          |
|-----------------|------------------------------|
| Frontend        | Next.js, TypeScript, Tailwind CSS, shadcn/ui |
| Backend         | Python, FastAPI, Pydantic    |
| Agent           | AWS Strands Agents SDK       |
| LLM             | Claude via Amazon Bedrock    |
| Database        | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Vector          | pgvector                     |
| Testing (Py)    | pytest                       |
| Testing (TS)    | Vitest, React Testing Library, Playwright |
| Code Quality    | Ruff, MyPy, ESLint, Prettier |
| Infrastructure  | Docker, Docker Compose, AWS  |

All other dependencies require explicit project-owner approval before use.

---

## Dependency Change Log

Changes to dependencies must be recorded in the applicable phase document
or in a dedicated changelog entry, noting:

- The dependency name and version
- The requirement it satisfies
- The phase in which it was introduced
