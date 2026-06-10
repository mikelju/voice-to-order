# Tasks Phase X: [Phase Name]

> Spec: `X.spec.md` | Plan: `X.0_name.md`
> This file is OPTIONAL — only for phases with >10 implementation steps.

<!--
Each task must be:
- Atomic: corresponds to ~1 commit
- Small: affects 3-5 files at most
- Verifiable: has clear "done" criteria
- Ordered: respects dependencies between tasks

Markers:
- [Story: US-X] → links to the spec's user story
- [depends on TX] → cannot start until TX is completed
- [P] → can run in parallel with other tasks
-->

---

## T1: [Descriptive name] [Story: US-1]

- **Files**: `path/file1.ts`, `path/file2.ts`
- **Action**: [what to do concretely in this task]
- **Verification**:
  - [ ] [how to check that it works]
  - [ ] [specific test that must pass]

## T2: [Descriptive name] [Story: US-1] [depends on T1]

- **Files**: `path/file.ts`
- **Action**: [what to do concretely]
- **Verification**:
  - [ ] [check]

## T3: [Descriptive name] [Story: US-2] [P]

- **Files**: `path/file.ts`, `tests/file.test.ts`
- **Action**: [what to do concretely]
- **Verification**:
  - [ ] [check]
  - [ ] [check]

## T4: [Descriptive name] [Story: US-2] [depends on T2, T3]

- **Files**: `path/file.ts`
- **Action**: [what to do concretely]
- **Verification**:
  - [ ] [check]

---

## Status summary

| Task | Story | Status |
|-------|-------|--------|
| T1 | US-1 | Pending |
| T2 | US-1 | Pending |
| T3 | US-2 | Pending |
| T4 | US-2 | Pending |
