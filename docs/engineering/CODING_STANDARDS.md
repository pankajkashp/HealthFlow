# Coding Standards

**Project:** HealthFlow
**Authority:** Product Requirements Specification v1.0

These standards apply to all production code written for HealthFlow.
They are derived from requirements explicitly established in the Product Requirements Specification (§17, §18).

---

## General Principles

### Production-Oriented Naming

- Names must communicate responsibility clearly to any reader unfamiliar with the codebase.
- Use domain language from the Product Requirements Specification.
- Avoid abbreviations that obscure meaning.
- Avoid generic placeholder names (see `docs/engineering/NAMING_CONVENTIONS.md`).

### Single Responsibility

- Each module, class, and function has one clearly defined responsibility.
- If a unit requires multiple qualifying phrases to describe what it does, split it.

### Small, Cohesive Modules

- Prefer small modules with a focused purpose over large all-purpose modules.
- Avoid catch-all utility modules (e.g., `utils.py`, `helpers.ts`).
- If shared logic genuinely belongs to no specific domain, place it in `packages/shared/` and document why.

---

## Type Safety

### Strong Typing

- Python: Use type annotations on all public functions, methods, and module-level variables.
  Enforce with MyPy in strict mode where practical.
- TypeScript: Use TypeScript strict mode (`"strict": true`).
  Do not use `any` except in narrow, documented exceptions.

### Explicit Interfaces at Architectural Boundaries

- Define explicit interfaces or protocols where layers interact (e.g., domain ↔ application, application ↔ infrastructure).
- Do not allow infrastructure types to leak into domain or application layers.
- (Ref: Product Requirements Specification §18 — ports and adapters)

---

## Architecture

### Separation of Concerns

- Keep domain logic, application logic, and infrastructure logic in separate layers.
- Each layer may only depend on the layers permitted by the clean architecture model.
- (Ref: Product Requirements Specification §18)

### Dependency Inversion

- High-level modules must not depend on low-level modules directly.
- Depend on abstractions (interfaces/protocols) at architectural boundaries.
- Infrastructure implementations fulfill domain-defined interfaces, not the reverse.

### No Unnecessary Abstractions

- Do not create abstraction layers ahead of a documented need.
- Only add an interface when there is more than one implementation or when isolation is required for testability.

---

## Validation

### Deterministic Validation

- Input validation must be deterministic and rule-based.
- The LLM must not be used as a substitute for deterministic validation.
- (Ref: Product Requirements Specification §9)

---

## Testability

- Write code that can be tested in isolation.
- Inject dependencies rather than constructing them inside business logic.
- Avoid global mutable state.
- Safety-critical paths must have automated tests.
  (Ref: Product Requirements Specification §16)

---

## Code Readability

### Readable Code

- Optimize for the reader, not the writer.
- Prefer explicit over implicit.
- Prefer straightforward logic over clever shortcuts.

### Comments

- Comments explain **why**, not **what**.
- Do not comment obvious code.
- If code requires a long comment to explain what it does, consider simplifying the code first.

---

## Code Quality Enforcement

The following tools are required by the locked technology stack (Product Requirements Specification §17):

| Context    | Tool      | Purpose                    |
|------------|-----------|----------------------------|
| Python     | Ruff      | Linting and formatting     |
| Python     | MyPy      | Static type checking       |
| TypeScript | ESLint    | Linting                    |
| TypeScript | Prettier  | Formatting                 |

Configuration for these tools will be defined in the applicable phase specification.

---

## Prohibited Patterns

- No duplicate logic. If logic is needed in more than one place, extract and reuse it.
- No dead code. Remove unused functions, imports, variables, and branches.
- No unused dependencies. Every installed dependency must be actively used.
- No catch-all exception handlers that silently swallow errors.
- No framework-specific types in the domain or application layers.
- No credentials or secrets in source code or committed configuration files.
  (Ref: Product Requirements Specification §21)
