# Naming Conventions

**Project:** HealthFlow
**Authority:** Product Requirements Specification v1.0

Names in this project communicate domain responsibility and engineering intent.
Names must be unambiguous to a reader who has not previously seen the codebase.

---

## Core Principle

> A name is correct when it can be read in isolation and its responsibility is immediately clear.

---

## Language-Specific Conventions

### Python

| Construct        | Convention       | Example                        |
|-----------------|------------------|--------------------------------|
| Module          | `snake_case`     | `authorization_request.py`     |
| Package         | `snake_case`     | `prior_authorization/`         |
| Class           | `PascalCase`     | `AuthorizationRequest`         |
| Function        | `snake_case`     | `validate_patient_record()`    |
| Variable        | `snake_case`     | `patient_identifier`           |
| Constant        | `UPPER_SNAKE`    | `MAX_RETRY_ATTEMPTS`           |
| Type alias      | `PascalCase`     | `WorkflowStateTransition`      |
| Protocol/ABC    | `PascalCase`     | `AuthorizationGateway`         |

### TypeScript

| Construct        | Convention       | Example                              |
|-----------------|------------------|--------------------------------------|
| File (component) | `PascalCase`    | `AuthorizationStatus.tsx`            |
| File (utility)  | `kebab-case`     | `format-date.ts`                     |
| Interface       | `PascalCase`     | `AuthorizationRequest`               |
| Type            | `PascalCase`     | `WorkflowState`                      |
| Enum            | `PascalCase`     | `AuthorizationStatus`                |
| Function        | `camelCase`      | `submitAuthorizationRequest()`       |
| Variable        | `camelCase`      | `patientIdentifier`                  |
| Constant        | `UPPER_SNAKE`    | `MAX_RETRY_ATTEMPTS`                 |
| React component | `PascalCase`     | `AuthorizationStatusPanel`           |
| React hook      | `camelCase` + `use` prefix | `useAuthorizationStatus()` |

---

## Domain-Oriented Naming

Names must reflect domain concepts from the Product Requirements Specification.
The following domain terms are established for use in names:

| Domain Concept              | Notes                                                        |
|-----------------------------|--------------------------------------------------------------|
| Authorization               | The prior-authorization workflow                             |
| Patient                     | The subject of the authorization                             |
| Workflow                    | The end-to-end administrative process                        |
| WorkflowState               | An explicit state in the workflow lifecycle                  |
| Validation                  | Deterministic information validation                         |
| Verification                | Independent confirmation of an expected outcome             |
| Escalation                  | Human escalation trigger                                     |
| SafetyGate                  | A safety check that must pass before an action proceeds     |
| Tool                        | An authorized agent capability                               |
| Submission                  | The act of submitting an authorization request              |
| Observation / Event         | A traceable workflow event                                   |

> These names are starting points. Additional domain terms will be defined in the applicable technical specification before implementation.

---

## Prohibited Names

The following names are not permitted anywhere in the codebase:

| Prohibited Name   | Reason                                    |
|-------------------|-------------------------------------------|
| `ai_magic`        | Does not communicate responsibility       |
| `super_agent`     | Does not communicate responsibility       |
| `brain`           | Does not communicate responsibility       |
| `helper`          | Catch-all, unclear scope                  |
| `helper_final`    | Version suffix in name is prohibited      |
| `utils`           | Catch-all, unclear scope                  |
| `utils2`          | Version suffix in name is prohibited      |
| `service_new`     | Version suffix in name is prohibited      |
| `temp`            | Indicates unfinished work                 |
| `test123`         | Indicates unfinished work                 |
| `misc`            | Catch-all, unclear scope                  |
| `stuff`           | Unclear scope                             |
| `data` (standalone) | Too generic without a qualifying noun |

---

## Version Suffixes

Version suffixes in names are prohibited in production code:

- No `_v2`, `_new`, `_final`, `_old`, `_2`, etc.
- If a concept changes, rename it to reflect the new responsibility or use version control history.

---

## Test File Naming

Test files must mirror the structure of the code they test.

| Language   | Convention                                 | Example                              |
|------------|--------------------------------------------|--------------------------------------|
| Python     | `test_<module_name>.py`                    | `test_authorization_request.py`      |
| TypeScript | `<ComponentName>.test.tsx` or `.spec.tsx`  | `AuthorizationStatus.test.tsx`       |

---

## Directory Naming

Directories must use `kebab-case` for consistency across operating systems.

Directories must represent cohesive domain or architectural concepts, not broad catch-alls.

---

## Notes on Premature Naming

Do not define names for modules, classes, or packages that have not yet been designed.

Module names will be established in the applicable technical specification prior to implementation.
