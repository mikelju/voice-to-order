# Command /7-verify

Verifies that the implemented code is aligned with the phase's functional specification.
It runs when a phase is finished, or mid-phase to check progress.

---

## When to use this command

- **When finishing a phase**: before marking the phase as completed in the master plan.
- **Mid-phase**: to check progress and detect drift early.
- **After a fix or deviation**: to verify that alignment has not been broken.

---

## Protocol

### Step 1: Load context

Read in this order:

1. **`CLAUDE.md`** → get the project's test command ("Development commands" section).
2. **`docs/plans/phase_X/X.spec.md`** → acceptance criteria, data contracts, anti-goals.
3. **`docs/plans/phase_X/X.0_name.md`** → plan status, affected files.

If no spec exists for the phase → say:
> "There is no spec for this phase. Alignment cannot be verified. Run `/4-specify` first."

If the user does not indicate a phase → verify the active phase (the first uncompleted one).

### Step 2: Run the tests

Run the project's test command (defined in `CLAUDE.md`).

Record:
- Which tests pass
- Which fail (with error message)
- Whether there are acceptance criteria with no associated test

If `CLAUDE.md` does not define a test command → ask the user how to run them.

### Step 3: Verify acceptance criteria

For EACH acceptance criterion in the spec:

1. **Is there at least one test that covers it?**
   - Look in the tests folder for a test that verifies this criterion.
   - If none exists → mark as `[ ] No test`.

2. **Does the test pass?**
   - If it passes → mark as `[x]`.
   - If it fails → mark as `[!] Test fails`.

### Step 4: Verify data contracts

If the spec defines data contracts (models, tables, endpoints):

1. **Models/Tables**: Do the fields, types and constraints in the code match those in the spec?
2. **Endpoints**: Do the routes, methods, request and response in the code match those in the spec?
3. If there is divergence → note what differs and in which file.

### Step 5: Verify anti-goals

Review the spec's "Anti-goals" section. Has anything been implemented that the spec explicitly excluded? If so → note it.

### Step 6: Generate the report

Present to the user:

```
## Verification: Phase X — [Name]

### Acceptance criteria
- [x] [criterion 1] — test: `tests/path/test_file::test_name`
- [!] [criterion 2] — test fails: [summarized error]
- [ ] [criterion 3] — no test

### Data contracts
- [x] Model `table` — fields match the spec
- [!] Endpoint `POST /path` — response differs: spec says X, code returns Y

### Anti-goals
- [x] [excluded thing] was not implemented
- [!] [thing the spec excluded] was implemented

### Result
[X of Y criteria verified] | [N pass, M fail, K without test]

### Pending actions
- [create test for criterion 3]
- [fix response of POST /path]
- ...
```

### Step 7: Resolve divergences

If there is drift (divergences between spec and code), ask the user:

> "There are divergences between the spec and the code. Do we update the spec to reflect the current code, or fix the code to comply with the spec?"

Apply the user's decision. If the spec is updated → propagate the changes to the phase plan.

### Step 8: Mark as completed

If all acceptance criteria pass:
- Mark criteria as `[x]` in the spec.
- Mark the corresponding steps as `[x]` in the phase plan.
- **Do NOT mark the phase as closed in the master plan yet**: the phase is closed after completing `/8-audit` + `/9-document`.
- Say:
  > "Phase X verified against the spec. Next step: `/8-audit` for the security audit.
  > If the phase does not touch security-relevant code (docs/assets/refactor only, with no behavior change), `/8-audit` itself will offer the escape hatch."

### Flow after verifying

Functional verification **does not close the phase**. The full flow is:

```
/7-verify → /8-audit → /9-document → mark phase in master plan
```

See `CLAUDE.md` / `CLAUDE_GLOBAL.md` → "Security audit" section for the phase-closure rules after the audit.
