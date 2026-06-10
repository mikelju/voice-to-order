# Master Plan: [Product Name]

## What is this product?

[2-3 sentences: problem it solves, for whom, how it solves it]

## Documentation convention

Every modification, improvement or fix follows this protocol before touching code:

```
docs/plans/
├── 0_master_plan.md           # This file — global vision
├── phase_1/
│   ├── 1.spec.md              # Functional specification (WHAT + WHY) — /4-specify
│   ├── 1.0_phase_name.md      # Implementation plan (HOW) — /5-plan
│   ├── 1.tasks.md             # (Optional) Atomic tasks — complex phases only
│   └── 1.Y_name.md            # Sequential deviation/problem (Y = 1, 2, 3…)
├── phase_2/
│   └── ...
└── fixes/
    └── fix-N_name.md          # One-off bug fix (globally sequential)
```

- **`X.spec.md`** → Functional specification. Created with `/4-specify` BEFORE planning.
- **`X.0`** → Implementation plan. Created with `/5-plan` AFTER the spec.
- **`X.tasks.md`** → Atomic tasks. Optional, only if the phase has >10 steps.
- **`X.Y`** → Deviation, unexpected problem or adjustment outside the plan (Y sequential).

**Workflow per phase:** `/4-specify` → `/5-plan` → `/6-implement` → `/7-verify`

---

## Phase status

| Phase | Name | Spec | Status |
|------|--------|------|--------|
| 1 | [Name] | Pending | Pending |
| 2 | [Name] | Pending | Pending |
| 3 | [Name] | Pending | Pending |

---

## Phase 1: [Name]
- [ ] [Milestone 1]
- [ ] [Milestone 2]
- [ ] [Milestone 3]

## Phase 2: [Name]
- [ ] [Milestone 1]
- [ ] [Milestone 2]

## Phase 3: [Name]
- [ ] [Milestone 1]
- [ ] [Milestone 2]

---

## Fixes
[References to fix-N for functionality without its own phase plan]
