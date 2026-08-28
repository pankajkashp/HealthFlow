# AI Engineering Rules

**Project:** HealthFlow
**Status:** LOCKED
**Authority:** Product Requirements Specification v1.0

These rules govern the behavior of all coding agents working on HealthFlow.
Violation of any rule must be treated as a blocker and reported immediately.

---

## Mandatory Pre-Implementation Steps

1. **Read the applicable specification before writing any code.**
   The specification is located at `docs/product/PRODUCT_REQUIREMENTS.md`.
   Do not begin implementation until the specification has been read and understood.

2. **Implement only the authorized phase.**
   Each phase document in `docs/phases/` defines exact scope.
   Do not implement work from a phase that has not been explicitly approved.

---

## Specification Integrity

3. **Do not modify locked requirements.**
   `docs/product/PRODUCT_REQUIREMENTS.md` is LOCKED.
   It may not be altered, reformatted, reinterpreted, or silently changed by any agent.

4. **Do not invent requirements.**
   If the specification does not describe something, it does not exist.
   Do not assume, extend, or add scope.

---

## API and Interface Integrity

5. **Do not invent APIs.**
   Only implement endpoints and interfaces described in an approved specification or contract document.

6. **Do not invent database fields.**
   Only persist fields explicitly required by an approved specification.

7. **Do not invent workflow states.**
   Workflow states are defined by the specification.
   Do not introduce intermediate states that have not been approved.

8. **Do not invent agent tools.**
   Agent tools must correspond to explicitly authorized capabilities.
   The LLM must not receive tools that grant unauthorized access to systems.

---

## Technology and Architecture

9. **Do not change the technology stack without explicit approval.**
   The locked technology stack is defined in Section 17 of the Product Requirements Specification.
   Substitutions require explicit project-owner approval.

10. **Do not add dependencies without explicit approval.**
    Dependency additions are governed by `docs/engineering/DEPENDENCY_POLICY.md`.

11. **Do not silently redesign architecture.**
    If an architectural decision must be made that is not covered by approved documentation,
    stop and report it.

12. **Do not rename established modules without approval.**
    Module names communicate domain responsibility.
    Renames require explicit approval and must be documented.

13. **Do not create duplicate abstractions.**
    Before creating a new abstraction, verify that an equivalent does not already exist.

---

## Safety and Permissions

14. **Do not bypass safety controls.**
    Safety gates, validation steps, and verification mechanisms are non-negotiable.
    They may not be skipped, mocked without appropriate test context, or removed.

15. **Do not bypass permissions.**
    Agent actions must be checked against explicit permissions.
    The agent must operate with least privilege at all times.

16. **Do not allow the LLM unrestricted system access.**
    The LLM must only receive tool access to systems authorized for the current workflow.
    Unrestricted database access, filesystem access, and network access are prohibited.
    (Ref: Product Requirements Specification §19)

---

## Data Safety

17. **Do not use real healthcare data.**
    All development, testing, benchmarking, and demonstration must use synthetic data only.
    Real patient data is prohibited at every stage.
    (Ref: Product Requirements Specification §4)

18. **Do not make clinical decisions.**
    HealthFlow is an administrative workflow system.
    The agent must not diagnose, recommend treatments, or override physician judgment.
    (Ref: Product Requirements Specification §8)

---

## Honesty and Verification

19. **Do not claim tests passed unless tests were actually executed.**
    Test results must reflect actual execution output.
    Qualitative claims about passing tests are prohibited.
    (Ref: Product Requirements Specification §15)

20. **Do not claim functionality exists unless it actually exists.**
    Do not describe features as complete unless they have been implemented and verified.

21. **Stop and report ambiguity instead of guessing.**
    If a requirement is unclear, contradictory, or incomplete, stop immediately.
    Report the exact issue and wait for resolution.
    Do not invent a solution.

---

## Phase Discipline

22. **Stop after completing the assigned phase.**
    Do not begin subsequent phases without explicit approval.
    Each phase has defined acceptance criteria that must be met before proceeding.

23. **Report deviations explicitly.**
    Any deviation from approved specifications or these rules must be documented
    in the final phase report. Silent deviations are prohibited.

---

## Phase Walkthrough Policy

24. **Automatically create a phase walkthrough for every phase.**

    This rule is **GLOBAL**. It applies to every future HealthFlow phase and does not need to be
    repeated in individual phase prompts. It may only be suspended by explicit project-owner
    instruction.

    ### Location

    At the completion of every development or specification phase, the implementation agent MUST
    create the following file:

    ```
    docs/phases/PHASE_<PHASE_ID>_WALKTHROUGH.md
    ```

    ### Required Content

    The walkthrough MUST describe the **actual repository state** and MUST include:

    - What was actually completed in this phase
    - Files created (with paths)
    - Files modified (with paths and description of change)
    - Summary of work performed
    - Verification performed and actual results
    - Actual test or check results (do not summarize; report exact output where relevant)
    - Dependencies added (or "None")
    - Deviations from the phase specification (or "None")
    - Blockers encountered (or "None")
    - What remains explicitly out of scope
    - Phase status: **PASS** or **FAIL**

    ### Prohibited Content

    The walkthrough MUST NOT:

    - Invent implementation that was not performed
    - Invent requirements
    - Invent test results
    - Claim functionality that does not exist
    - Describe future work as completed
    - Claim tests passed unless tests were actually executed and output was observed
    - Modify or restate the Product Requirements Specification

    ### Specification-Only Phases

    For phases that produce only specification artifacts (documents, structure, governance),
    the walkthrough must describe those artifacts accurately.
    It must not pretend that application functionality was implemented.

    ### Implementation Phases

    For phases that produce application code, the walkthrough must describe the actual
    implementation and the verification steps that were actually executed, with real results.
