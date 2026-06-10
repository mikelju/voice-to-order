# Agent instructions

This document defines how the agent must operate in any project. It contains the file structure, the available commands, the documentation system, the testing rules, the coding rules and, optionally, the WAT framework for projects that need it.

**Always read this document in full before starting to work on any project.**

---

## Project file structure

Every project follows this base structure. Not every project uses every folder — the ones marked as optional are created only when needed.

```
my-project/
├── CLAUDE.md                          # Project constitution — always read before acting
├── .claude/
│   ├── commands/                      # Cross-cutting commands (shared across projects)
│   │   ├── prime.md
│   │   ├── 1-create-master-plan.md
│   │   ├── 2-scaffold.md
│   │   ├── 3-init-project.md
│   │   ├── 4-specify.md
│   │   ├── 5-plan.md
│   │   ├── 6-implement.md
│   │   ├── 7-verify.md
│   │   ├── 8-audit.md
│   │   └── 9-document.md
│   ├── skills/                        # Reusable skills (SKILL.md + references/)
│   │   └── audit-code/                # Professional security audit (Python + React)
│   ├── settings.local.json
│   └── README.md
├── src/                               # Application source code
├── tests/                             # Automated tests
├── data/                              # Temporary data files (CSV, Excel, JSON...)
├── docs/
│   ├── plans/                         # SDD documentation system + plans
│   │   ├── 0_master_plan.md           # Global vision — phases, status, decisions
│   │   ├── phase_1/
│   │   │   ├── 1.spec.md             # Functional specification (WHAT + WHY)
│   │   │   ├── 1.0_phase_name.md     # Implementation plan (HOW)
│   │   │   ├── 1.tasks.md            # (Optional) Atomic tasks — complex phases only
│   │   │   └── 1.Y_deviation.md      # Deviation or adjustment outside the plan (sequential)
│   │   └── fixes/
│   │       └── fix-N_name.md         # One-off bug fix (globally sequential)
│   ├── security/                      # Security audit reports (/8-audit)
│   │   ├── README.md                  # Catalog of SEC/DEF/OBS findings
│   │   └── audit-YYYY-MM-DD-*.md      # Reports per phase / release gate
│   ├── templates/                     # Document templates (spec, plan, tasks, CLAUDE.md...)
│   ├── refs/                          # Immutable reference documentation (PDFs, manuals, etc.)
│   └── learnings/                     # (WAT only) Lessons per workflow
├── output/                            # (Optional) Generated deliverables
├── workflows/                         # (WAT only) Project-specific SOPs
├── tools/                             # (WAT only) Deterministic execution scripts
├── .tmp/                              # Temporary files — regenerable, disposable
├── .env                               # API keys and environment variables (NEVER anywhere else)
└── .gitignore
```

---

## Cross-cutting commands (.claude/commands/)

The cross-cutting commands are reusable tools that work in every project. They live in `.claude/commands/` and are invoked with `/`. They manage the project's documentation, planning and context.

| Command | When to use it | What it generates |
|---------|---------------|------------|
| `/prime` | At the start of every session | Project context report |
| `/1-create-master-plan` | When creating a new project | `docs/plans/0_master_plan.md` |
| `/2-scaffold` | After creating the master plan | Base project structure |
| `/3-init-project` | After creating the project scaffold | `CLAUDE.md` (by reading real code) |
| `/4-specify` | Before starting each new phase | `docs/plans/phase_X/X.spec.md` |
| `/5-plan` | After the spec, before coding | `docs/plans/phase_X/X.0_name.md` |
| `/6-implement` | After the plan, to execute the steps | Code + tests (test-first cycle) |
| `/7-verify` | When finishing a phase (or mid-phase to check) | Spec ↔ code alignment report |
| `/8-audit` | Before closing a phase, before a release, after a critical fix | `docs/security/audit-YYYY-MM-DD-<mode>.md` |
| `/9-document` | When finishing a phase or the project | `docs/USER_GUIDE.md` |

### New project flow

```
/1-create-master-plan → /2-scaffold → /3-init-project
```

### Flow for each phase

```
/4-specify → /5-plan → /6-implement → /7-verify → /8-audit → /9-document → mark [x]
```

### Release gate (before packaging / deploying / publishing)

```
/8-audit full   → full-project audit to catch cross-cutting issues
```

### Flow for each work session

```
/prime → (load context) → work
```

---

## Project documentation system (SDD + Plans)

The project uses **Spec-Driven Development (SDD)** integrated with a hierarchical plan system. The combination ensures that each phase has a precise definition of WHAT to build (spec), a plan for HOW to implement it (phase plan) and a record of everything that happens during execution (deviations, fixes).

### Document types

| File | What it contains | When it is created | Who creates it |
|---------|-------------|----------------|---------------|
| `0_master_plan.md` | Global vision, phases, status | At project start | `/1-create-master-plan` |
| `X.spec.md` | Functional specification: WHAT + WHY | Before each phase | `/4-specify` |
| `X.0_name.md` | Implementation plan: HOW | After the spec | `/5-plan` |
| `X.tasks.md` | Atomic tasks (optional) | Only if the phase has >10 steps | `/5-plan` or manual |
| `X.Y_name.md` | Deviation or adjustment outside the plan | When a problem appears | Manual |
| `fix-N_name.md` | One-off bug fix | When a bug is detected | Manual |

### Templates

The templates for each document type live in `docs/templates/`. The commands (`/4-specify`, `/5-plan`, `/1-create-master-plan`, `/3-init-project`) use them as a reference when generating new documents.

| Template | What it is for |
|-----------|----------|
| `CLAUDE_project.md` | Template for each project's CLAUDE.md |
| `0_master_plan.md` | Master plan template |
| `X.spec.md` | Functional specification template |
| `X.0_phase_plan.md` | Phase plan template |
| `X.tasks.md` | Atomic tasks template (optional) |
| `X.Y_deviation.md` | Template for deviations or adjustments outside the plan |
| `fix-N_name.md` | One-off bug fix template |

### Golden rule

**Before touching code, there is a documented spec and plan.** If there is no spec, run `/4-specify`. If there is no plan, run `/5-plan`.

### Mandatory rule: specify and plan before coding

**Before implementing any change, follow this order:**

1. **If it is a new phase** → run `/4-specify` to define WHAT is being built
2. **Then** → run `/5-plan` to document HOW it is being built
3. **Do not touch code** (do not create files, do not edit anything) until the spec + plan are written and the user confirms them

**Exceptions that require NEITHER spec NOR plan:**
- One-line fixes (typos, broken imports)
- Running existing workflows or tools without modifying code

**Exceptions that require a plan but NO spec:**
- Bug fixes that require more than one trivial change (they go into `fix-N`)
- Changes affecting 1-2 files without altering functional behavior

**Exceptions that require a spec but only a minimal plan:**
- Small changes that alter functional behavior (new fields, new endpoint) — quick spec with objective + acceptance criteria

### Update rules

- **Spec**: NOT modified during implementation. If the scope changes → update the spec first, then propagate to the plan.
- **Master plan**: Only updated after verifying that things work, not when planning.
- **Phase plan**: Always kept as a faithful reflection of the real state. If a deviation changes the approach → update.
- **Propagation**: Everything flows upward — deviations update the phase plan, substantial changes in the phase plan are reflected in the master plan.

### Spec-in-code rule

Every process (manual or automated) that produces or modifies code must:
1. Read `CLAUDE.md` (project constitution)
2. Read the active phase's spec (`docs/plans/phase_X/X.spec.md`) if it exists
3. Verify that the result meets the spec's acceptance criteria

If no spec exists for the active phase, run `/4-specify` first.

---

## Testing and verification against specifications

These rules apply to all projects, regardless of the stack or testing framework used.

### General testing rules

1. **Every acceptance criterion in the spec must have at least one associated test.** If the spec says "two appointments cannot be booked in the same slot", a test that verifies it must exist.

2. **Tests are written BEFORE or AT THE SAME TIME as the implementation**, never after. If the phase plan has a step "Create POST /api/appointments endpoint", the step must include creating the corresponding test.

3. **A task cannot be marked as completed `[x]` unless its tests pass.** If the tests do not pass, the task remains pending.

4. **Never delete failing tests without solving the problem.** If a test fails, fix the code or document why the test is no longer valid (updating the spec if appropriate).

5. **When finishing a phase, verify the spec's acceptance criteria one by one.** Each criterion is marked `[x]` only if a test that validates it exists and that test passes.

### Spec ↔ code alignment verification

Before declaring a phase complete, check:

- Do all the spec's acceptance criteria have tests? → If any is missing, create it.
- Do the data contracts (models, endpoints) in the code match those in the spec? → If they diverge, update the spec or fix the code.
- Is there implemented functionality that is not in the spec? → If it is useful, add it to the spec. If it is not, remove it from the code.
- Are the spec's anti-goals respected? → Verify that nothing the spec explicitly excluded has been implemented.

### Testing framework

The concrete testing framework (Jest, Vitest, Pytest, etc.) is defined in each project's `CLAUDE.md`, along with the execution commands. The rules in this section apply regardless of the chosen framework.

---

## Security audit

Every project integrates a structured security audit as a step of the phase flow. It relies on the `audit-code` skill (`.claude/skills/audit-code/`), which contains the protocol, the vulnerability catalog (Python, React, OWASP Top 10, secret patterns) and the report template.

### When to audit

- **Mandatory when closing a phase** that touches security-relevant code (authentication, cryptography, user input, external dependencies, file handling, subprocess, deserialization).
- **Mandatory before any release** (`full` mode — release gate).
- **Recommended after a fix** in sensitive modules.
- **Ad-hoc** when a security review is requested.

### Escape hatch

If the active phase does not touch relevant security code (docs only, assets, or pure refactor with no behavior change), `/8-audit` asks whether to skip the audit and records the exemption in `docs/security/` for traceability. Never skip phases that touch auth, crypto, external input, subprocess or deserialization.

### Severity rubric

Five levels consistent with the skill's catalog:

| Severity | What it means in practice |
|-----------|------------------------------|
| Critical | Exploitable without conditions; stop and fix today. |
| High | Exploitable under realistic conditions; fix before release. |
| Medium | Exploitable under specific conditions, or with limited impact. Fix within the sprint. |
| Low | Defense in depth, not exploitable on its own. Backlog. |
| Info | Observation, no direct risk. |

Each finding gets a `SEC-NNN` ID (the hundreds digit indicates the phase: `1xx`=Phase 1, `3xx`=Phase 3, etc.), a CWE tag and an OWASP category.

### Phase closure after the audit

- If there are no **Critical or High** findings → the phase can be closed. Move on to `/9-document`.
- If there are Critical or High findings → the phase **is not closed** until they are resolved or an explicit decision to defer is recorded with justification in the master plan.
- Each closed SEC is resolved with a `fix-N` in `docs/plans/fixes/` following the project's protocol.

### Centralized catalog

Each project maintains `docs/security/README.md` as the single index of findings (pending, closed, deferred by business decision). This file is the entry point to review the security status without having to open all the per-phase reports.

### CI automation

The template includes `.github/workflows/security.yml`. It automatically detects the stack (Python / Node) and runs **bandit**, **pip-audit**, **detect-secrets** or **npm audit** as appropriate, on every push and pull request against `main`/`master`.

It works as a **safety net complementary to `/8-audit`**: if a developer forgets to run the manual audit, the CI will at least catch the vulnerabilities that automated scanners detect (SAST + dependencies + secrets). `/8-audit` is still required for manual review and exploitability reasoning — the CI does not replace human analysis, it reinforces it.

If a CI finding is a false positive, document the exception in `docs/security/` instead of silently suppressing it.

### Non-negotiable rules during the audit

1. Never install tools (`pip install`, `npm install`) without explicit authorization.
2. Never run payloads against the code itself or external systems — the PoC is descriptive.
3. Never dump complete secrets into the report — always redact (`sk-abcd...`).
4. Never say "the code is secure" — use "no critical findings within the reviewed scope".
5. False positives > false negatives. When in doubt, report as HIGH and let the human downgrade.
6. Do not modify code during the audit — only after the report and with an explicit green light.

---

## Reusable skills

The skills in `.claude/skills/` encapsulate specialized protocols that trigger automatically when their description matches the user's intent (or explicitly with `/<skill-name>`). They live in the project (versioned) so the whole team shares them.

Structure of a skill:

```
.claude/skills/<name>/
├── SKILL.md              # Frontmatter with name + description + triggers + main content
└── references/           # (Optional) auxiliary files loaded on demand
```

Skills included by default in the template:

| Skill | What it is for |
|-------|----------|
| `audit-code` | Professional security audit (see previous section) |

When a skill grows, keep the SKILL.md short and move the catalogs into `references/*.md`, loaded only when the flow needs them.

---

## Coding rules

### Python: Unicode characters

**Do not use special Unicode characters in Python code.** The backend runs in Docker (Gunicorn) and on Google Cloud Run, where `stdout` may use codecs like `charmap` that do not support characters outside extended ASCII. This causes errors like `'charmap' codec can't encode character`.

**Forbidden in print(), logging, code strings:**
- Emojis: ✓ ✗ ✔ ✘ 💻 👉 📜 🚀 🏗️ and similar
- Unicode arrows: → ← ↑ ↓
- Special symbols: • ■ □ ★

**Use instead:**
- `[OK]` instead of `✓`
- `[ERROR]` instead of `✗`
- `[WARN]` instead of `⚠`
- `->` instead of `→`
- `-` or `*` instead of `•`

**Exception:** Documentation `.md` files MAY use these characters because they do not go through Python's stdout.

### Project-specific conventions

The specific naming, formatting, pattern and anti-pattern conventions are defined in each project's `CLAUDE.md` (generated by `/3-init-project`). They include:

- Code style (with example snippets)
- Agent permissions (ALWAYS / ASK / NEVER)
- Forbidden anti-patterns (with alternatives)
- Known gotchas

---

## WAT framework (optional)

The **WAT** framework (Workflows, Agents, Tools) is a system that separates work instructions (workflows) from deterministic execution (tools). **Not every project needs it.** It is activated when the project has repeatable tasks that benefit from reusable scripts (scraping, reporting, data pipelines, integrations with external APIs, etc.).

### When to use WAT

- **DO use** when the project has repeatable processes that run many times (e.g. weekly scraping, report generation, data synchronization).
- **DO NOT use** when the project is a standard web application or API where the code IS the product. In that case, the SDD documentation system + plans is enough.

### How it works

**Layer 1: Workflows (the instructions)**
- Markdown files in `workflows/` that describe processes step by step.
- Each workflow defines: objective, required inputs, which tools to use, expected outputs and how to handle errors.
- They are project-specific: a scraping workflow, a reporting workflow, a data processing workflow...

**Layer 2: Agent (the coordinator)**
- Your role as the agent. You read the workflow, run the tools in the right order, handle errors and ask for clarification when needed.
- You connect intent with execution without trying to do everything yourself directly.
- Example: if you need data from a website, do not attempt it directly. Read `workflows/scrape_website.md`, identify the required inputs, and run `tools/scrape_single_site.py`.

**Layer 3: Tools (the execution)**
- Python scripts in `tools/` that do the real work.
- API calls, data transformations, file operations, database queries.
- Credentials and API keys live in `.env`.
- They are consistent, testable and fast.

**Why does this separation matter?** When the AI tries to handle every step directly, accuracy drops fast. If each step has a 90% success rate, after five steps you are at 59%. By delegating execution to deterministic scripts, the agent focuses on what it does well: coordination and decision-making.

### WAT folders

If the project uses WAT, these folders are added to the base structure:

```
workflows/          # Project SOPs (Markdown) — process instructions
tools/              # Execution scripts (Python) — deterministic action
docs/learnings/     # Lessons learned per workflow
```

**`docs/learnings/`** captures what worked and what did not in each workflow run. When a workflow finishes, it is reviewed with the user and the corresponding learnings file is updated. It is the institutional memory that makes every run better than the previous one.

### Operating rules with WAT

**1. Look for existing tools first.**
Before building something new, check `tools/` based on what the workflow requires. Only create new scripts when nothing exists for that task.

**2. Learn and adapt when something fails.**
When an error occurs:
- Read the full error message and the trace.
- Fix the script and try again (if it uses paid API calls, check with the user before running again).
- Document what was learned in the workflow (rate limits, timing, unexpected behavior).

**3. Keep workflows up to date.**
Workflows must evolve as you learn. When better methods, constraints or recurring problems are found, update the workflow. That said, do not create or overwrite workflows without asking the user unless explicitly instructed.

### Self-improvement loop

Every failure is an opportunity to strengthen the system:
1. Identify what broke
2. Fix the tool or workflow
3. Verify that the fix works
4. Update the workflow with the new approach
5. Capture the lesson in `docs/learnings/`
6. Continue with a more robust system

---

## Behavior summary

You sit between what the user wants (documented in specs, plans and workflows) and what actually runs (code and tools). Your job is to read the instructions, make intelligent decisions, execute or delegate to the right tools, recover from errors, verify against the specs, and continuously improve the system.

Be pragmatic. Be reliable. Keep learning.
