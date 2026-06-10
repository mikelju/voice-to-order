# Command /6-implement

Executes the phase plan steps following the test-first cycle: write the test, verify it fails, write the code, verify it passes, mark the step as completed.

---

## Usage modes

```
/6-implement              → executes all pending steps of the active phase
/6-implement 3            → executes only step 3
/6-implement 3-5          → executes steps 3, 4 and 5
/6-implement next         → executes the next pending step
```

---

## Protocol

### Step 1: Load context

Read in this order:

1. **`CLAUDE.md`** → project rules, test command, conventions, permissions.
2. **`docs/plans/phase_X/X.spec.md`** → acceptance criteria and data contracts.
3. **`docs/plans/phase_X/X.0_name.md`** → implementation steps and current status.
4. **`docs/plans/phase_X/X.tasks.md`** (if it exists) → atomic tasks.

If no spec exists → say:
> "There is no spec for this phase. Run `/4-specify` first."

If no phase plan exists → say:
> "There is no plan for this phase. Run `/5-plan` first."

### Step 2: Determine which steps to execute

Depending on the invocation mode:

- **No argument**: all steps marked `[ ]` in the phase plan.
- **Number** (`3`): only that step. Verify that it exists and is pending.
- **Range** (`3-5`): steps 3 through 5. Verify that they exist.
- **`next`**: the first step marked `[ ]`.

Tell the user which steps will be executed before starting:
> "I am going to execute steps X, Y, Z of the phase plan. Do you confirm?"

### Step 3: Execute each step (test-first cycle)

For each step to execute, follow this cycle:

**3a. Identify the acceptance criterion.**
Which spec criterion does this step cover? If the step is not linked to any criterion, note it.

**3b. Write the test.**
Create the test that verifies the acceptance criterion. The test must:
- Live in the project's tests folder (per the structure in `CLAUDE.md`).
- Clearly name which criterion it verifies.
- Be runnable with the project's test command.

**3c. Verify that the test fails (red).**
Run the test command. The new test MUST fail because the code does not exist yet.
- If the test passes without code → the test verifies nothing useful. Rewrite it.
- If other previously passing tests now fail → stop, there is a problem. Investigate before continuing.

**3d. Write the code.**
Implement the code that makes the test pass, following:
- The conventions in `CLAUDE.md`.
- The spec's data contracts (fields, types, constraints).
- The forbidden anti-patterns.

**3e. Verify that the test passes (green).**
Run the test command.
- If the new test passes and the rest keep passing → continue.
- If the new test fails → fix the code and run again.
- If other previously passing tests now fail → stop. Something broke. Fix it before continuing.

**3f. Mark the step as completed.**
- Mark `[x]` in the phase plan (`X.0_name.md`).
- If `X.tasks.md` exists, mark it there too.

**3g. Report progress.**
> "Step X completed. Test passes. [Brief description of what was implemented]."

### Step 4: Handle deviations

If an unexpected problem appears while executing a step:

1. **Stop** — do not continue to the next step.
2. **Tell** the user what happened and what impact it has.
3. **Create a deviation** (`X.Y_name.md`) using the template `docs/templates/X.Y_deviation.md`.
4. **Wait for confirmation** from the user if the impact is significant.
5. **Update the phase plan** to reflect the adopted decision.
6. If the change alters the requirements → **update the spec** and propagate.
7. Resume execution when the problem is resolved.

### Step 5: When finished

Once all requested steps have been executed:

1. **Update the phase plan**: verify that all executed steps are marked `[x]`.
2. **Report a summary**:

```
## Implementation summary

### Executed steps
- [x] Step 3: [description] — test: `tests/path/test_file.py`
- [x] Step 4: [description] — test: `tests/path/test_file.py`
- [x] Step 5: [description] — test: `tests/path/test_file.py`

### Phase status
[X of Y steps completed]

### Tests
[N new tests created, all passing]

### Next action
[Next pending step | Run /7-verify if the phase is complete]
```

3. If **all the phase's steps are completed** → suggest:
   > "All the plan's steps are completed. Run `/7-verify` to check spec ↔ code alignment before closing the phase."
