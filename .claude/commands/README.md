# Command quick reference

## `/prime`
**When to use it:** At the start of every session, before any task.

Loads the full project context: reads `CLAUDE.md`, the master plan, the active phase's spec and plan, the git history and the main code files. Delivers a report with the active phase, spec status, pending tasks, latest commits and the suggested next step.

---

## `/1-create-master-plan`
**When to use it:** When starting a new project, before writing code.

Conducts a conversation to understand what is being built, for whom and in which phases. Uses the template `docs/templates/0_master_plan.md`.

**Generates:** `docs/plans/0_master_plan.md`

---

## `/2-scaffold`
**When to use it:** After creating the master plan, before `/3-init-project`.

Creates the base project structure by running the chosen ecosystem's scaffold commands (npm create, uv init, etc.). Asks about project type and stack. Creates the framework folders (`docs/`, `tests/`, etc.).

**Generates:** Initialized project with real code

---

## `/3-init-project`
**When to use it:** Once the project has code (after the scaffold).

Reads the project's real code (`package.json`, main files, `.env.example`, configurations) and generates the `CLAUDE.md` with the real architecture, stack, commands, conventions, agent permissions, anti-patterns and gotchas. Uses the template `docs/templates/CLAUDE_project.md`.

**Requires existing code** — it cannot be generated from scratch.

**Generates:** `CLAUDE.md` at the project root

---

## `/4-specify`
**When to use it:** Before starting each new phase.

Generates the functional specification (`X.spec.md`) for a phase of the master plan. Defines WHAT to build and WHY through a discovery conversation with the user. Uses the template `docs/templates/X.spec.md`.

**Generates:** `docs/plans/phase_X/X.spec.md`

---

## `/5-plan`
**When to use it:** After the spec, before coding.

Reads the phase's spec, generates the implementation plan and presents it for approval. Uses the templates in `docs/templates/`.

**Generates:**
- `docs/plans/phase_X/X.0_name.md` — the phase's main plan
- `docs/plans/phase_X/X.tasks.md` — atomic tasks (optional, if >10 steps)

---

## `/6-implement`
**When to use it:** After the plan is approved, to execute the steps.

Executes the phase plan steps following the test-first cycle: write the test, verify it fails, write the code, verify it passes, mark the step `[x]`. Handles deviations if they appear.

**Modes:**
- `/6-implement` — executes all pending steps
- `/6-implement 3` — executes only step 3
- `/6-implement 3-5` — executes steps 3 through 5
- `/6-implement next` — executes the next pending step

---

## `/7-verify`
**When to use it:** When finishing a phase, or mid-phase to check progress.

Verifies the alignment between the spec and the code: runs the project's tests, checks that every acceptance criterion has a test and passes, compares the data contracts against the real code and reviews that no anti-goals have been implemented. Generates a report with the status of each criterion.

**Generates:** Verification report (does not create a file, shows the result in the console)

---

## `/8-audit`
**When to use it:** When closing each phase (after `/7-verify` and before `/9-document`), before any release, after a critical fix or when a security review is requested.

Professional security audit backed by the `audit-code` skill. It goes through the 5 phases (scope, automated scanning, manual review, exploitability reasoning, report). It covers Python (primary) and React/frontend (secondary), maps OWASP Top 10 + CWE and produces a report with severity, file:line and a proposed fix.

Includes an **escape hatch**: if the active phase does not touch security-relevant code (docs only, assets or pure refactor with no behavior change), the command asks whether to skip the audit and records the exemption in the report.

**Modes:**
- `/8-audit` — audits the **active phase**'s files (default)
- `/8-audit phase X` — audits a specific phase
- `/8-audit full` — audits all of `src/` (release gate)
- `/8-audit quick` — automated scanning only (bandit, pip-audit, etc.)
- `/8-audit deps` — dependencies only
- `/8-audit secrets` — hardcoded credentials search only
- `/8-audit <path>` — scope restricted to a path/file/glob

**Generates:** `docs/security/audit-YYYY-MM-DD-<mode>.md`

---

## `/9-document`
**When to use it:** When finishing a phase (after `/8-audit`) or at the end of the project.

Generates the application's user guide (`docs/USER_GUIDE.md`). It reads the completed specs, turns the user stories into practical instructions and verifies against the real code. Brief documentation, with bullet points and emojis, for non-technical users.

**Generates:** `docs/USER_GUIDE.md`

---

## Full flow

```
NEW PROJECT
1. /1-create-master-plan → define what you build and in which phases
2. /2-scaffold           → create the project (npm create, uv init, etc.)
3. /3-init-project       → generate CLAUDE.md from the real code

EACH PHASE
4. /4-specify            → define WHAT to build (functional spec)
5. /5-plan               → define HOW to implement it (phase plan)
6. /6-implement          → code + tests (test-first cycle per step)
7. /7-verify             → spec ↔ code alignment + mark [x]
8. /8-audit              → security audit (phase or full)
9. /9-document           → user guide (when finishing phase or project)

RELEASE GATE (before packaging / deploying / publishing)
/8-audit full            → full-project audit to catch cross-cutting issues

EACH SESSION
/prime                   → load context before working
```
