# HEALTHFLOW — PHASE 6 TECHNICAL WALKTHROUGH & AUDIT REPORT
## Production Polish, Frontend Integration & Demo Scenarios

```text
================================================================================
PROJECT:             HealthFlow (Autonomous Healthcare Administrative AI Agent)
PHASE:               Phase 6 — Production Polish, Frontend Integration & Demo Scenarios
STATUS:              COMPLETE / PASSED
QUALITY GATE:        100% (Ruff clean, MyPy strict clean, ESLint clean, TypeScript clean)
DATABASE:            PostgreSQL 17.x (localhost:5432) — Phase 2 schema, unmodified
TEST SUITE:          233/233 Python tests passing (225 pre-existing + 8 new), 6/6 frontend tests
DATE:                2026-09-09
================================================================================
```

---

## 1. Metadata & Document Control

- **Document Title:** Phase 6 Technical Walkthrough & Verification Audit
- **Project:** HealthFlow
- **Author:** Lead Implementation Engineer
- **Target Audience:** Product Architect, Hackathon Judges (Agents for Humans — Devpost)
- **Approved Specifications:**
  - Product Requirements Specification v1.0 (`docs/product/PRODUCT_REQUIREMENTS.md`)
  - Architecture Document v1.0 (`docs/architecture/ARCHITECTURE.md`)
  - Phase 5 Walkthrough (`docs/phases/PHASE_05_WALKTHROUGH.md`), §32 "Readiness for Phase 6"
  - This phase's plan, approved in-session prior to implementation (per `AI_ENGINEERING_RULES.md`
    rules 1, 2, 22)

---

## 2. Executive Summary

Phase 5 left the project with a fully tested domain/application/safety layer but nothing actually
running end to end. Investigation at the start of this phase surfaced one fact that reshaped its
scope: **`HealthFlowAgent.execute_workflow` was not an LLM agent** — it was a hardcoded,
deterministic 8-step Python script. The Strands SDK and Bedrock were declared dependencies but
never imported or called anywhere in the repository. There was no live LLM reasoning in the project.

Phase 6 therefore centered on wiring in a **real, LLM-driven Strands agent** that reasons over the 9
approved tools, alongside the FastAPI backend, Next.js dashboard, and Docker Compose wiring needed
to run and observe it. The core HealthFlow principle — *the LLM reasons, deterministic code
controls, the environment proves completion* — is unchanged and, for the first time, actually
exercised end to end: the previously hardcoded script is preserved unmodified as an offline/test
fallback, and a new real LLM tool-calling loop is added alongside it, with the exact same
deterministic domain state machine and independent-verification contract governing both.

---

## 3. What Was Built in Phase 6

1. **Real LLM agent runtime (`services/agent/`):**
   - `tool_adapters.py`: `@tool`-decorated Strands wrapper functions for all 9 `AgentTools` methods
     (locked by AD-014, never modified).
   - `model_factory.py`: builds `strands.models.AnthropicModel` or `BedrockModel` (or `None` for
     the scripted path) from `AgentConfig.llm_provider`.
   - `state_sync.py`: `WorkflowStateSync` — the deterministic mapping from a completed tool call to
     a legal workflow-state transition, using the exact domain transition graph
     (`packages/domain/.../workflow_state.py`, unmodified). Used live by the LLM runner and as a
     post-hoc replay for the scripted path.
   - `llm_runner.py`: `LlmDrivenWorkflowRunner` — constructs a real `strands.Agent`, runs it against
     a goal/patient, and feeds every completed tool call to `WorkflowStateSync`.
   - `config.py`: added `llm_provider`, `anthropic_api_key`, `anthropic_model_id`, `max_tokens`.
2. **Seed data (`scripts/seed_demo_data.py`):** idempotently seeds `Patient`/`InsurancePlan` rows
   for all 6 synthetic benchmark fixtures into Postgres.
3. **FastAPI backend (`apps/api/`):**
   - `dependencies.py`: the composition root — `CaseOrchestrator`, wiring the synthetic-environment
     adapters, `PostgresUnitOfWork`, `CreateAuthorizationCaseService`, `TransitionWorkflowStateService`,
     and either `HealthFlowAgent` (scripted) or `LlmDrivenWorkflowRunner` (anthropic/bedrock).
   - `schemas.py`: Pydantic response/request models.
   - `routes/cases.py`: `GET/POST /api/v1/cases`, `GET /api/v1/cases/{id}`,
     `POST /api/v1/cases/{id}/run`, `GET /api/v1/cases/patients`.
   - `main.py`: CORS middleware, router registration.
4. **Next.js dashboard (`apps/web/`):**
   - `src/lib/api-client.ts`: typed REST client.
   - `src/app/page.tsx`: case list + "start a new case" picker over the 6 benchmark patients.
   - `src/app/cases/[id]/page.tsx` + `case-detail-client.tsx`: live case detail — state badge,
     workflow timeline, tool-call trace, verification/escalation banners, ~2s polling while active.
5. **Docker Compose:** `db` migrates and seeds automatically on `api` container start;
   `api.Dockerfile` rebuilt to install the whole monorepo (previously only installed `apps/api`
   itself, which could never have worked once `apps/api` depended on the other packages).
6. **Tests:** 8 new API tests (`apps/api/tests/test_cases_api.py`) covering create/run/get for both
   the standard-success and false-success/DONE-principle escalation paths; 4 new frontend tests.
7. **Incidental bug fix (`migrations/env.py`, `alembic.ini`):** see §15.

---

## 4. Phase Scope and Boundaries

### Strictly In Scope:
- A real, LLM-driven Strands agent tool-calling loop (Anthropic and Bedrock providers).
- FastAPI endpoints exposing case creation, agent execution, and case/workflow state.
- A Next.js dashboard to drive and observe the workflow live.
- Docker Compose wiring so the full stack runs with one command.
- Automated tests for the new API surface.
- A demo script covering all 12 PRS §22 MVP success criteria.

### Explicitly Deferred (see §5 for the reasoning behind each):
- Full JWT authentication (AD-011).
- WebSocket push notifications — the dashboard polls instead.
- RAG / pgvector / Titan embeddings.
- Public cloud hosting/deployment (local `docker compose up` only).
- Persisting `SubmissionRecord`/`VerificationRecord`/`EscalationRecord` rows — the workflow
  transition timeline (with per-hop reasons) already carries the same narrative for the demo; the
  schema for these tables already exists (Phase 2) for a future phase to populate.

---

## 5. Explicit Deviations From Locked Documentation

Per `AI_ENGINEERING_RULES.md` rule 11 ("stop and report" architectural decisions not covered by
approved docs) and rule 23 (deviations must be documented, not hidden). All four were discussed and
approved with the project owner before implementation began.

1. **LLM provider is config-swappable, not Bedrock-only.** Locked §17 specifies "Claude through
   Amazon Bedrock." The project owner had neither AWS Bedrock model access nor an Anthropic API key
   at the start of this phase. `AgentConfig.llm_provider` (env `LLM_PROVIDER`) selects `scripted`
   (default), `anthropic`, or `bedrock`. Bedrock support is fully implemented
   (`model_factory.build_model`) and exactly matches the original locked design — it is untested in
   this session only because Bedrock model access was not available, not because it was skipped.
2. **The existing hardcoded `HealthFlowAgent.execute_workflow` is preserved unmodified**, not
   replaced, and continues to back all 225 pre-existing tests untouched. `LlmDrivenWorkflowRunner`
   is a wholly new, additive class.
3. **`apps/api/src/healthflow_api/dependencies.py` is a narrow, documented exception to
   ARCHITECTURE.md §4.1**, which prohibits `apps/api` from depending on `packages/domain` or
   `packages/infrastructure` directly. Taken literally, no request could ever construct a database
   session. This one file (the composition root) is the sole exception; `routes/cases.py` imports
   neither domain nor infrastructure and contains no business logic — it only calls
   `CaseOrchestrator` methods, which already return the Pydantic schema objects to return.
4. **JWT authentication (AD-011) is deferred, not silently dropped.** The demo runs locally against
   100% synthetic data with no real PHI. Flagged here explicitly as future work.

Also narrowed (sequencing choices, not deviations from a locked spec): WebSocket updates →
polling; RAG/pgvector remain deferred (already flagged in the Phase 5 walkthrough, not required by
any PRS §22 criterion); no public hosting in this phase.

---

## 6. LLM Agent Architecture

```text
                    LLM (Claude, via Strands Agent)
                               │
                               │ Reasons about which tool to call next
                               ▼
        ┌──────────────────────────────────────────────┐
        │  tool_adapters.py — @tool wrappers            │
        │  (thin; calls the unmodified AgentTools)      │
        └──────────────────────┬───────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │  AgentTools (packages/application, AD-014)    │
        │  — unmodified. Input validation, permissions, │
        │    safety gates, AD-012 retries all unchanged │
        └──────────────────────┬───────────────────────┘
                               │ tool result
                               ▼
        ┌──────────────────────────────────────────────┐
        │  state_sync.WorkflowStateSync                 │
        │  — deterministic: maps (tool, result) to the  │
        │    domain-legal next WorkflowState, walking   │
        │    ALLOWED_TRANSITIONS (packages/domain)      │
        └──────────────────────┬───────────────────────┘
                               │ on_transition callback
                               ▼
        ┌──────────────────────────────────────────────┐
        │  TransitionWorkflowStateService (application) │
        │  — persists via AuthorizationCase.transition_ │
        │    to(), enforcing the DONE-principle          │
        │    invariant exactly as in Phase 5             │
        └────────────────────────────────────────────────┘
```

The LLM never calls `TransitionWorkflowStateService` or sees `WorkflowState` at all — it only sees
tool results. Whether a call implies a transition, and whether that transition is legal, is decided
entirely by code the LLM cannot influence.

---

## 7. API Surface (new)

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/v1/cases/patients` | List the 6 synthetic benchmark patients for the demo picker |
| GET | `/api/v1/cases` | List all cases |
| POST | `/api/v1/cases` | Create a case from a benchmark `patient_id` |
| GET | `/api/v1/cases/{id}` | Case detail + full workflow transition timeline |
| POST | `/api/v1/cases/{id}/run` | Execute the agent synchronously; returns the full tool-call trace |

`POST /run` is synchronous by design: each transition is committed via its own short-lived
`TransitionWorkflowStateService` call rather than one outer transaction, so a concurrent
`GET /cases/{id}` from another tab genuinely observes live progress while a real (slower) LLM run
is still in flight — no background task queue was needed for this.

---

## 8. Live Verification Performed (this session, real output)

### 8.1 Full backend test suite

```text
$ DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/healthflow_dev \
  python -m pytest tests/ apps/api/tests/ -v
...
======================== 233 passed, 1 warning in 1.24s ========================
```
233 = 225 pre-existing (Phases 1–5, untouched, all still pass) + 8 new (`test_cases_api.py`).

### 8.2 Quality gates

```text
$ ruff check packages/ services/ apps/ tests/ scripts/ migrations/
All checks passed!

$ ruff format --check packages/ services/ apps/ tests/ scripts/ migrations/
78 files already formatted

$ mypy packages/domain packages/shared packages/safety packages/application \
       packages/infrastructure services/agent apps/api tests/
Success: no issues found in 72 source files
```

### 8.3 Frontend

```text
$ npm run test -- --run
 Test Files  2 passed (2)
      Tests  6 passed (6)

$ npm run lint
(no output — clean)

$ npx tsc --noEmit
(no output — clean)

$ npm run build
✓ Compiled successfully
Route (app)
┌ ○ /
├ ○ /_not-found
└ ƒ /cases/[id]
```

### 8.4 Live end-to-end run (`LLM_PROVIDER=scripted`, real Postgres, real HTTP)

Full API session captured live (`curl`) against a running `uvicorn` process:

- **`pat_jenkins_001` (standard success):** created → ran → `status=COMPLETED`,
  `is_verified=true`, 7 persisted transitions from `INITIATED` through `COMPLETED`, final
  transition reason `"Independently verified APPROVED."`
- **`pat_chen_006` (false-success / DONE-principle test):** created → ran → `status=ESCALATED`,
  `is_verified=false`. The `submit_authorization_request` step succeeded
  (`success: true, submission_reference: "AUTH-ACK-CHEN-006"`), but `verify_authorization_outcome`
  returned `verified: false`; final persisted transition:
  `VERIFYING -> ESCALATED: "Independent verification did not confirm expected outcome: Authoritative
  state mismatch: expected 'APPROVED', but authoritative external state is 'DENIED'."`

### 8.5 Live browser verification

Both scenarios above, plus the `pat_martinez_002` (missing document) scenario, were additionally
driven through the actual Next.js dashboard in a real browser (dev servers on `localhost:3000` /
`localhost:8010`): case creation, the Run button, the live workflow timeline, the tool-call trace
panel, and both the green "completed/verified" and amber "escalated" banners were visually
confirmed rendering correctly.

**Not verified this session:** a live run with `LLM_PROVIDER=anthropic` (no API key was available),
and `docker compose up --build` itself (the Docker daemon was not available in this environment).
The equivalent local `pip install -e` sequence the Dockerfile performs was run manually and
succeeded; the Dockerfile/compose changes were reviewed against that but not built as an image.
**Action for the project owner:** run `docker compose -f docker/docker-compose.yml up --build`
before a live demo to confirm the container build, and set `ANTHROPIC_API_KEY` /
`LLM_PROVIDER=anthropic` to exercise the real LLM path at least once beforehand.

---

## 9. Complete File Manifest

### Created (19):
- `services/agent/src/healthflow_agent/tool_adapters.py`
- `services/agent/src/healthflow_agent/model_factory.py`
- `services/agent/src/healthflow_agent/llm_runner.py`
- `services/agent/src/healthflow_agent/state_sync.py`
- `services/agent/src/healthflow_agent/py.typed`
- `scripts/seed_demo_data.py`
- `apps/api/src/healthflow_api/schemas.py`
- `apps/api/src/healthflow_api/dependencies.py`
- `apps/api/src/healthflow_api/routes/__init__.py`
- `apps/api/src/healthflow_api/routes/cases.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_cases_api.py`
- `apps/web/src/lib/api-client.ts`
- `apps/web/src/components/state-badge.tsx`
- `apps/web/src/app/cases/[id]/page.tsx`
- `apps/web/src/app/cases/[id]/case-detail-client.tsx`
- `apps/web/src/app/cases/[id]/case-detail-client.test.tsx`
- `docs/phases/PHASE_06_DEMO_SCRIPT.md`
- `docs/phases/PHASE_06_WALKTHROUGH.md` (this document)

### Modified (15):
- `services/agent/src/healthflow_agent/config.py` — added LLM provider fields.
- `services/agent/src/healthflow_agent/__init__.py` — exported new symbols.
- `services/agent/pyproject.toml` — added `strands-agents[anthropic]`, `healthflow-domain`,
  `healthflow-application`.
- `apps/api/src/healthflow_api/main.py` — CORS middleware, registered `cases` router.
- `apps/api/pyproject.toml` — added `healthflow-application`, `healthflow-agent`,
  `healthflow-domain`, `healthflow-infrastructure`.
- `apps/web/src/app/page.tsx` — replaced the Phase-1 placeholder with the real dashboard.
- `apps/web/src/app/page.test.tsx` — rewritten for the new dashboard.
- `apps/web/src/app/layout.tsx` — fixed leftover `create-next-app` metadata.
- `docker/docker-compose.yml` — repo-root build context, DB migration/seed on start, LLM env vars.
- `docker/api.Dockerfile` — rebuilt to install the whole monorepo, not just `apps/api`.
- `.env.example` — documented all new environment variables.
- `migrations/env.py` — bug fix, see §15.
- `alembic.ini` — bug fix, see §15.
- `README.md` — updated current phase status.

### Pre-existing, unrelated uncommitted change (not part of this phase):
- `docker/web.Dockerfile` — a comment-wording change was already present in the working tree before
  this session began; left as-is, not reviewed or altered further here.

---

## 10. Dependency Governance

New dependencies added, all within already-approved categories (agent/LLM SDK, web framework) per
`docs/engineering/DEPENDENCY_POLICY.md`:
- `strands-agents[anthropic]` (services/agent) — the `anthropic` extra of the already-approved
  Strands SDK, needed for `strands.models.AnthropicModel`.
- Intra-repo path packages (`healthflow-domain`, `healthflow-application`, `healthflow-agent`,
  `healthflow-infrastructure`) added to `services/agent` and `apps/api` — no new external
  dependencies, just declaring dependencies that were previously used without being declared
  (`services/agent/agent.py` already imported `healthflow_application` without it being listed;
  fixed as an incidental correction).
- No new frontend npm packages were added — the dashboard uses only what was already installed
  (`next/navigation`, `@testing-library/user-event`, already-present shadcn primitives/Tailwind).

---

## 11. Independent Verification / DONE-Principle Continuity

Nothing about the DONE-principle enforcement built in Phase 5 was changed:
- `AuthorizationCase.transition_to(COMPLETED)` still raises unless
  `verification_status == VerificationStatus.CONFIRMED` from `VERIFYING` — unmodified.
- `AgentTools.verify_authorization_outcome` — unmodified.
- The only new code in this chain, `state_sync.target_for_tool_result`, reads a
  `VerificationResult`'s `verified` **and** `actual_status` fields (not the LLM's claimed
  `expected_status`) to decide `COMPLETED` vs. `DENIED` vs. `ESCALATED` — the authoritative external
  state, not the agent's intent, still decides the outcome.
- §8.4 above is a live, real-request demonstration of the false-success interception continuing to
  work end to end through the new HTTP/LLM-runner layers.

---

## 12. Human Escalation Continuity

All escalation triggers from Phase 5 (`PRE_ACTION_SAFETY_GATE_FAILED`, `PERMISSION_DENIED`,
`VERIFICATION_MISMATCH`, `RETRIES_EXHAUSTED`, `CLINICAL_DATA_CONFLICT`,
`INFORMATION_UNRESOLVABLE`, `PORTAL_ERROR`) surface through the same `request_escalation` tool,
unmodified, and are now visible in the dashboard's amber escalation banner and workflow timeline.
`LlmDrivenWorkflowRunner` additionally forces an `ESCALATED` transition if an LLM run ends without
calling either `verify_authorization_outcome` or `request_escalation` (`_finalize_status`'s safety
net) — the environment, not the LLM's silence, decides a stuck case still needs a human.

---

## 13. Architecture Compliance Audit

- `packages/domain`, `packages/safety` — zero changes.
- `packages/application` (`AgentTools`, `tool_models.py`) — zero changes; `services.py`
  (`CreateAuthorizationCaseService`, `TransitionWorkflowStateService`) — zero changes, now actually
  invoked for the first time.
- `services/agent` — additive only (`agent.py`/`config.py`'s existing fields untouched; `config.py`
  gained new optional fields with safe defaults).
- `apps/api` — the §4.1 exception is confined to one file (`dependencies.py`); see §5.
- `apps/web` — depends only on the REST API, per §4.2; no domain types imported.

---

## 14. Negative / Out-of-Scope Audit

- **Agent-Controlled Completion:** Checked. Neither the LLM nor `LlmDrivenWorkflowRunner` calls
  `TransitionWorkflowStateService` directly with `COMPLETED` — `state_sync` derives the target from
  the verification result's `actual_status`/`verified` fields, not from the LLM's text or intent.
- **LLM-Controlled Permission:** Checked. `AgentTools`' permission engine is untouched and still the
  sole gate on `submit_authorization_request`.
- **Direct Database Mutation from Routes:** Checked. `routes/cases.py` contains zero SQL/ORM
  imports; all persistence happens inside `CaseOrchestrator` (`dependencies.py`) via the existing
  application-layer services.
- **Unauthorized Tools:** Checked. `tool_adapters.py` wraps exactly the same 9 methods
  `HealthFlowAgent._tool_registry` already exposed — no new tool was added.
- **Safety Bypass:** Checked. The LLM path calls the same `AgentTools` instance, so input
  validation, permission checks, and pre-action safety gates run identically to the scripted path.

---

## 15. Incidental Bug Fix: `migrations/env.py` Database-URL Precedence

While seeding demo data and running the full test suite repeatedly, `healthflow_dev`'s schema was
observed being silently wiped after every test run. Root cause: `tests/integration/test_alembic_
migrations.py` isolates itself to a separate `healthflow_test` database via
`Config.set_main_option("sqlalchemy.url", TEST_DB_URL)`, but `migrations/env.py`'s `get_url()`
checked the `DATABASE_URL` environment variable **before** the Config object's already-set value —
so whenever a developer had `DATABASE_URL` exported (which is the project's own documented normal
workflow: Phase 5's gate G-04 command is `DATABASE_URL=... pytest tests/ apps/api/tests/ -v`), the
migration test's `command.downgrade(cfg, "base")` silently ran against the real `healthflow_dev`
database instead of the isolated `healthflow_test` one, dropping its schema every time.

This is a pre-existing, deterministic bug (not test flakiness or ordering) that predates this
phase, confirmed to reproduce identically on unmodified `main` before any Phase 6 change was
applied. It directly threatened this phase's demo environment (a shared local Postgres), so it was
fixed here: `get_url()`'s precedence now checks `config.get_main_option("sqlalchemy.url")` first,
and `alembic.ini`'s previously-hardcoded default `sqlalchemy.url` (which always shadowed the
per-test override for the same reason) was blanked so normal CLI usage still falls through
correctly to `DATABASE_URL`. Verified: running the migration test with `DATABASE_URL` exported (the
documented workflow) now correctly leaves `healthflow_dev` untouched (see §8.1 — 233/233 including
this test passing in the same run that seeds and exercises `healthflow_dev`).

This is reported here per rule 23 rather than left silent, and is a narrow correctness fix, not an
architectural redesign.

---

## 16. Requirements Traceability (PRS §22 MVP Success Criteria)

| # | Criterion | Demonstrated By |
| :--- | :--- | :--- |
| 1 | Synthetic case created | `POST /api/v1/cases`, dashboard "Start case" |
| 2 | Agent understands the goal | `LlmDrivenWorkflowRunner` prompt construction |
| 3 | Controlled tool retrieval | `tool_adapters.py` (9 tools, unchanged from AD-014) |
| 4 | Deterministic validation | `validate_authorization_package`, unmodified |
| 5 | Request prepared | `PREPARING_SUBMISSION` transition, persisted |
| 6 | Submitted to simulated system | `submit_authorization_request`, unmodified |
| 7 | Workflow monitorable | `GET /cases/{id}`, live dashboard polling |
| 8 | Routine follow-up | `get_authorization_status` step, unmodified |
| 9 | Escalation for critical/ambiguous cases | `pat_chen_006`, `pat_martinez_002` live runs (§8.4/8.5) |
| 10 | Independently verified outcome | `verify_authorization_outcome`, unmodified |
| 11 | Never claims completion without verification | §11 above |
| 12 | Fully observable/testable | Dashboard tool-trace + timeline; `test_cases_api.py` |

---

## 17. Blockers

None blocking. Two items require the project owner's action before a live judged demo (not
blockers to this phase's completion, since the system is fully functional on `LLM_PROVIDER=scripted`
today): obtaining an `ANTHROPIC_API_KEY` (or AWS Bedrock access) for a real LLM-driven run, and
running `docker compose up --build` once locally to confirm the container build (Docker was
unavailable in this implementation session).

---

## 18. Technical Debt

- `SubmissionRecord`/`VerificationRecord`/`EscalationRecord` tables (Phase 2 schema) remain
  unpopulated — the workflow-transition timeline currently carries equivalent information via its
  per-hop `reason` text. Populating these dedicated tables is straightforward future work if
  structured querying of submissions/verifications/escalations independent of the transition log is
  needed later.
- `submit_authorization_request`'s payload still hardcodes `procedure_type="MRI_LUMBAR_SPINE"` and
  `requesting_physician="dr_attending"` regardless of the actual case (pre-existing from Phase 4,
  not changed here) — cosmetic only, since the synthetic portal's response is keyed by
  `submission_reference`, not by the payload contents.

---

## 19. Deviations

See §5 (four explicit, approved deviations) and §15 (one incidental bug fix). No other deviations
from the approved plan.

---

## 20. Final Audit Conclusion

```text
================================================================================
Phase Status:                  PASS
Implementation Status:         COMPLETE
Verification Status:           233/233 Python tests passing, 6/6 frontend tests passing
Architecture Compliance:       PASS (one documented, scoped exception — §5, item 3)
Security/Data-Safety Status:   PASS (synthetic-only, CORS scoped, no secrets committed)
Known Blockers:                NONE (two owner action items — §17)
Technical Debt:                Documented, non-blocking (§18)
Next Authorized Phase:         Post-MVP — live Bedrock/Anthropic demo run, public deployment,
                                RAG/pgvector, JWT auth, per-record persistence (§18)
================================================================================
```
