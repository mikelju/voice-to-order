# Command /8-audit

Professional security audit of the code. It relies on the `audit-code` skill (`.claude/skills/audit-code/`) and produces a reproducible report with findings, severity, CWE, OWASP and a proposed fix for each issue.

It is step **8** of the phase flow: it runs **after** `/7-verify` (when the tests already pass and the code is aligned with the spec) and **before** `/9-document` (so the documentation reflects the final, secure state).

---

## When to use this command

- **Mandatory when closing a phase** that touches security-relevant code (authentication, cryptography, user input, external dependencies, file handling, subprocess, deserialization).
- **Mandatory before any release** (`full` mode).
- **Recommended after a fix** in sensitive modules.
- **Ad-hoc** when the user asks for a security review.

It does not replace `/7-verify` (which validates functionality against the spec). This command validates **security**.

---

## Modes

The default mode is **active phase**: only what was modified in the current phase is audited (bounded scope, fast feedback, integrated into the SDD flow).

| Mode | What it audits | When to use it |
|------|-----------|---------------|
| `/8-audit` (no arguments) | Files of the **active phase** (detected from the master plan) | When closing each phase |
| `/8-audit phase X` | Files of the specific phase X | One-off re-audit of an earlier phase |
| `/8-audit full` | All of `src/` — release gate | Before packaging, deploying, publishing |
| `/8-audit quick` | Automated scanning only (no manual review) | Light check or CI |
| `/8-audit deps` | Dependencies only (pip-audit, safety, npm audit) | After adding/updating dependencies |
| `/8-audit secrets` | Hardcoded credentials search only | After a leak or as a routine pass |
| `/8-audit <path>` | Free-form path (file, directory, glob) | Custom scope |

---

## Protocol

### Step 1: Load skill and context

1. Invoke the `audit-code` skill (or read `.claude/skills/audit-code/SKILL.md` in full).
2. Read the project's `CLAUDE.md`: stack, commands, gotchas.
3. Read `docs/plans/0_master_plan.md`: identify the **active phase** (first uncompleted one).
4. If the mode is `phase X` (or default) → read `docs/plans/phase_X/X.spec.md` and `X.0_*.md` to learn which files were touched in that phase.

### Step 2: Escape hatch — does this phase need an audit?

First of all, check whether the active phase is auditable. If **any** of these holds, ask the user whether to skip it:

- The phase does not touch any file under `src/` (docs only, cosmetic configuration, assets).
- The phase is a pure refactor with no behavior change (note: a refactor that touches auth, crypto or input parsing is **NOT** exempt — audit anyway).
- The phase is a file/structure migration with no new logic.

Phrase the question like this:

```
Phase {{X}} — "{{name}}" appears to contain no security-relevant code
(reason: {{docs only / refactor with no functional change / assets…}}).

Do we skip the audit for this phase?
- If you answer "yes" → I record the note "Phase X exempt — reason: ..." in the report
  and continue with /9-document.
- If you answer "no" → I proceed with the full audit anyway.
```

If the user confirms the exemption, **create a mini-report** in `docs/security/audit-YYYY-MM-DD-phase-X.md` with the documented reason (leave a trace — an exempt phase is not simply an unaudited phase, it is a recorded, conscious decision).

If the phase DOES touch sensitive code, never offer the escape hatch.

### Step 3: Define and communicate scope

Present to the user:

```
## Audit — Scope

- **Scope:** {{specific files of phase X, or "all of src/" if `full` mode}}
- **Mode:** {{phase / full / quick / deps / secrets / custom path}}
- **Assumed threat model:** {{inferred from the project's CLAUDE.md}}
- **Detected stack:** {{Python 3.11, …}}
- **Locally available tools:** bandit [yes/no], pip-audit [yes/no], semgrep [yes/no], gitleaks [yes/no], ruff [yes/no]
```

If the user confirms or stays silent → continue. If they correct the scope/threat model → adjust.

### Step 4: Run the skill's 5 phases

Follow **Phase 1 → Phase 5** of `SKILL.md`:

1. **Phase 1 — Scope & Context**: already done in Step 3.
2. **Phase 2 — Automated Scanning**: probe which tools are installed (`references/tools-integration.md`) and run the available ones. **Do NOT install anything without authorization.**
3. **Phase 3 — Manual Review**: read `references/python-security.md` in full. If there is React/JS/TS code, also `references/react-security.md`. Apply the 10 questions per file.
4. **Phase 4 — Exploit Reasoning**: for each finding, reason about exploitability and write a conceptual PoC (never execute).
5. **Phase 5 — Report**: generate the report following `references/report-template.md`.

In reduced modes (`quick`, `deps`, `secrets`), run only the corresponding phase:
- `quick` → Phases 1, 2 and 5 (skip Manual Review).
- `deps` → dependency scan only + partial report.
- `secrets` → secrets scan only + partial report.

### Step 5: Coverage Self-Check

Before presenting the final report, run the coverage checklist from `SKILL.md`. If any item was not covered → state it explicitly in the report's §5 Coverage section.

### Step 6: Publish the report

Path depending on mode:
- `phase X` mode / default → `docs/security/audit-YYYY-MM-DD-phase-X.md`
- `full` mode → `docs/security/audit-YYYY-MM-DD-full.md`
- `quick`, `deps`, `secrets` modes → `docs/security/audit-YYYY-MM-DD-<mode>.md`

- If `docs/security/` does not exist → create the folder.
- If a report already exists for the same date+mode combination → suffix `-2`, `-3`, etc.
- If the user prefers inline → show it in chat without writing a file (but persisting is still recommended).

Tell the user:
```
Audit complete. Report at: docs/security/audit-YYYY-MM-DD-<mode>.md

Summary:
- Critical: N (immediate fix)
- High: N (before release)
- Medium: N
- Low: N
- Info: N

Top 3 to fix first:
1. [SEC-001] — <title>
2. [SEC-002] — <title>
3. [SEC-003] — <title>
```

### Step 7: Remediation offer and phase closure

**Do not modify code during the audit.** When finished, ask:

> "Do you want me to start applying the fixes? I can tackle them in severity order (Critical → High → Medium). For each non-trivial fix I will create a `fix-N` in `docs/plans/fixes/` following the project's protocol."

If the user says yes → switch from "auditor" mode to "remediator" mode:
- Trivial fixes (one line, one import) → apply directly.
- Non-trivial fixes → follow the SDD flow: create `docs/plans/fixes/fix-N_name.md` with a minimal plan, then implement.
- Rotate compromised credentials **before** touching anything else (the user does this; you wait for confirmation).

**Phase closure:**
- If there are no **Critical or High** findings → the phase can be closed. Move on to `/9-document`.
- If there are Critical or High findings → the phase **is not closed** until they are resolved or an explicit decision to defer is recorded with justification in the master plan.

---

## Non-negotiable rules

1. **Never install tools** (`pip install`, `npm install`) without explicit authorization.
2. **Never run payloads** against the code itself or against external systems. The PoC is descriptive.
3. **Never dump complete secrets** into the report — always redact (`sk-abcd...`).
4. **Never say "the code is secure"** — use "no critical findings within the reviewed scope".
5. **False positives > false negatives**. When in doubt, report as HIGH; the user downgrades if appropriate.
6. **Confirm every automated finding by reading the code** before including it in the report.
7. **Do not modify code during the audit** — only after the report and with an explicit green light.
8. **Escape hatch** only applies to phases with no security-relevant code. Never skip a phase that touches auth, crypto, external input, subprocess or deserialization.

---

## Expected output

- File: `docs/security/audit-YYYY-MM-DD-<mode>.md` following the template in `.claude/skills/audit-code/references/report-template.md`.
- Summary in chat with per-severity counters and top-3 priorities.
- Remediation offer following the project's fix protocol.
- Phase closure decision (can be closed / cannot be closed + reason).
