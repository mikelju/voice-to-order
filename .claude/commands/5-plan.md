# Skill: Planning and Documentation Protocol

This skill defines how to act when any change, improvement or fix is proposed in the project.

## Golden rule

**Before touching code, there is a documented plan.** If there is no plan, one is created. If there is a deviation, it is recorded. If the phase has no spec, run `/4-specify` first.

---

## Documentation structure

```
docs/plans/
├── 0_master_plan.md           # Global vision of all phases
├── phase_1/
│   ├── 1.spec.md              # Functional specification (WHAT + WHY)
│   ├── 1.0_phase_name.md      # Implementation plan (HOW)
│   ├── 1.tasks.md             # (Optional) Atomic tasks for complex phases
│   ├── 1.1_problem_X.md       # Deviation or problem found (sequential)
│   └── 1.2_adjustment_Y.md    # Another adjustment outside the main plan
├── phase_2/
│   ├── 2.spec.md
│   ├── 2.0_phase_name.md
│   └── ...
└── fixes/
    ├── fix-1_name.md          # One-off bug fix or corrective (globally sequential)
    └── fix-2_name.md
```

### File naming

| File | When to use it |
|---|---|
| `X.spec.md` | Functional specification. Created with `/4-specify` BEFORE the phase plan. |
| `X.0_name.md` | Main plan of phase X. Created when starting the phase, AFTER the spec. |
| `X.tasks.md` | Atomic tasks. OPTIONAL — only if the phase has >10 steps. |
| `X.Y_name.md` | Deviation, problem or adjustment outside the main plan. Y is sequential (1, 2, 3...). |
| `fixes/fix-N_name.md` | One-off bug fix or corrective between phases or within a phase. N is globally sequential. |

---

## When to update each document

### Functional Spec (`X.spec.md`)
- Created BEFORE the phase plan, via `/4-specify`.
- **NOT modified** during implementation unless the phase scope changes.
- If the scope changes → update the spec first, then propagate to the phase plan.

### Master Plan (`0_master_plan.md`)
- When a **new phase is added** that did not exist.
- When a phase **milestone is completed** (mark `[x]`).
- When a phase's **scope changes** substantially.
- NOT for implementation details — those go in the phase plan.

### Phase Plan (`X.0_name.md`) — the phase's source of truth
- There is **exactly one per phase** (`X.0_*.md`). It is the equivalent of the master plan but in the context of that specific phase.
- It is created **after the spec** and references it. The success criteria map 1:1 from the spec's acceptance criteria.
- It contains: objective, concrete steps, success criteria, affected files, technical notes.
- **It is always kept up to date** as a faithful reflection of the phase's real state:
  - Mark completed tasks (`[x]`) as the work progresses.
  - If a deviation (`X.Y`) changes the approach, steps or scope → update the `X.0` so it reflects the adopted decision.
  - If technical notes, gotchas or design decisions are discovered → add them to the `X.0`.
- **Propagation rule**: any substantial change in the phase plan (not simple `[x]` marks) must also be reflected in that phase's description within the master plan.

### Tasks (`X.tasks.md`) — OPTIONAL
- Only created when the phase has **more than 10 implementation steps**.
- It breaks the plan down into atomic tasks: each task = 1 commit, 3-5 files maximum.
- If it does not exist, the phase plan steps (`X.0`) serve that purpose.

### Deviation document (`X.Y_name.md`)
- Created when:
  - An **unexpected problem** appears that blocks or alters the plan.
  - A **change outside the plan** of the current phase is needed.
  - A fix or solution requires **more than 2-3 non-trivial steps**.
- It contains: problem description, root cause, adopted solution, impact.
- **Propagation obligation**: after creating or closing a deviation, update the phase plan (`X.0`) so it reflects the change. The deviation is the historical record of "what happened"; the phase plan is the reflection of "how things stand".

### One-off fix or corrective (`fixes/fix-N_name.md`)
- Created when a **bug or incorrect behavior** appears in already existing functionality,
  regardless of which phase the project is in.
- N is a **globally sequential** number (fix-1, fix-2...), independent of the phase.
- **Mandatory correlation rule**: the fix must always be referenced in the plan of the
  phase the affected functionality belongs to:
  - If the phase has a plan doc (`X.0_*.md`) → add an entry in that doc's "Fixes" section.
  - If the phase has no plan doc → add an entry in the master plan's "Fixes" section.
- It contains: bug description, root cause, adopted solution, modified files.

---

## Step-by-step protocol when receiving a new task

1. **Read the master plan** (`docs/plans/0_master_plan.md`) to understand the context.
2. **Determine which phase** the requested task belongs to.
   - If it fits an existing phase → continue.
   - If it is something new → propose adding it as a new phase to the master plan.
3. **Check whether the functional spec exists** (`docs/plans/phase_X/X.spec.md`).
   - If it does NOT exist and the task requires one → say: "There is no functional specification for this phase. Run `/4-specify` first to define WHAT is being built." Do not continue until it exists (or the user explicitly decides to skip it).
   - If it exists → read it to learn the acceptance criteria and contracts.
4. **Check whether the phase plan exists** (`docs/plans/phase_X/X.0_name.md`).
   - If it does not exist → create it now, referencing the spec. The success criteria must map from the spec's acceptance criteria.
   - If it exists → read it to understand the scope and the status.
5. **Present the plan to the user** for review and approval. Nothing is implemented until the user confirms.
6. **Indicate the next step**:
   > "Phase plan ready. Run `/6-implement` to start the implementation, or `/6-implement next` to go step by step."

---

## Templates

All documents generated by this protocol use the templates in `docs/templates/`:

| Document | Template |
|-----------|-----------|
| Phase plan | `docs/templates/X.0_phase_plan.md` |
| Tasks (optional, if >10 steps) | `docs/templates/X.tasks.md` |
| Deviation | `docs/templates/X.Y_deviation.md` |
| Fix | `docs/templates/fix-N_name.md` |

Read the corresponding template before generating each document.

---

## Now: apply the protocol

Read the master plan and the existing phase plans, determine where the project stands and tell the user:
1. The current status of each phase (pending / in progress / completed).
2. Whether the active phase has a spec (`X.spec.md`) or not.
3. What the next logical step would be according to the plan.
4. Whether the requested task fits the plan or requires updating it.
