# Command /prime — Initial context load

Run this full protocol at the start of every session, before any task.
The goal is to build an accurate mental map of the project in its current state.

---

## Phase 1: Project rules and architecture

Read `CLAUDE.md` at the project root.

Extract and memorize:
- Project name and what it does
- Tech stack and versions
- Development commands and how to start the project
- Architecture decisions and main patterns
- Agent permissions (ALWAYS / ASK / NEVER)
- Project anti-patterns
- Known gotchas
- Code conventions

---

## Phase 2: Master plan status

Read `docs/plans/0_master_plan.md`.

Identify:
- Which phases exist and what their status is (pending / in progress / completed)
- Which is the current active phase (the first uncompleted one)
- Whether phase subfolders have been created in `docs/plans/`

---

## Phase 3: Spec and plan of the active phase

For the active phase (the first uncompleted one):

1. **Check whether `X.spec.md` exists:**
   - If it exists → read it. Note pending vs completed acceptance criteria.
   - If it does NOT exist → mark as "⚠️ No functional spec".

2. **Read `X.0_*.md`** (the phase's main plan):
   - Determine which tasks are completed (`[x]`) and which are pending (`[ ]`).

3. **If `X.tasks.md` exists** → read it to learn the atomic task breakdown.

Only if the user wants specific information about a phase, additionally read:

4. `X.Y_*.md` files (deviations or adjustments).

---

## Phase 4: Recent change history

Run the following commands to understand what has changed recently:

```bash
git log --oneline -10
git status
```

Identify:
- The latest changes made to the project
- Whether there is uncommitted work in progress

---

## Phase 5: Key code files

`CLAUDE.md` (section "File structure") lists the project's main files. Read each of them.

If `CLAUDE.md` does not list files explicitly, infer the usual entry points for the stack (e.g. the main server, the frontend root component, the database configuration file, etc.).

Mentally note:
- Main functions and their purpose
- Any TODOs, technical-debt comments or provisional code

---

## Deliverable: Context report

After finishing the 5 phases, present a structured report to the user:

```
## Project status: [Project name]

### Active phase
[Name and number of the phase in progress]

### Functional spec
[✅ Available (X criteria pending out of Y total) | ⚠️ Does not exist — run /4-specify]

### Pending tasks in the active phase
- [ ] Task 1
- [ ] Task 2

### Recent changes (git)
[Last 3-5 relevant commits]

### Uncommitted work
[Modified files, if any]

### Suggested next step
[One single concrete, specific action]
```

Only after delivering this report, ask the user what they want to do.
