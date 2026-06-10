# Command /4-specify

Generates the functional specification file (`X.spec.md`) for a phase of the master plan.
It runs BEFORE `/5-plan` to define WHAT to build and WHY, without getting into the HOW.

---

## When to use this command

- **New phase**: before starting to implement any phase of the master plan.
- **Scope change**: when a phase's requirements have changed and the previous spec no longer reflects reality.
- **Retroactive spec**: when something was implemented without a spec (vibe coding, prototype) and you want to formalize it before continuing.

---

## Protocol

### Step 1: Load context

Read in this order:

1. **`CLAUDE.md`** → project rules, stack, agent permissions.
2. **`docs/plans/0_master_plan.md`** → identify the phase and its current description.
3. **Related existing code** (if any) → read the main files affecting this phase so you do not specify things that already exist or contradict the reality of the code.

### Step 2: Identify the phase

- If the user says "specify phase 3" → phase 3.
- If no phase is indicated → the first phase WITHOUT an `X.spec.md` file.
- Verify that the folder `docs/plans/phase_X/` exists. If it does not, create it.

### Step 3: Specification conversation

Ask the following questions **one at a time**, waiting for an answer before continuing.
Do not ask them all at once — the goal is a conversation, not a form.

1. **"What problem does this phase solve for the end user?"**
   → Defines the "Problem and objective" section

2. **"Who interacts with this functionality and what can they do?"**
   → Defines the user stories

3. **"How will we know it is done right? What conditions must be met?"**
   → Defines the acceptance criteria

4. **"What data does it handle? What goes in and what comes out?"**
   → Defines the data contracts (models, endpoints, formats)

5. **"What must this phase NOT do? What is out of scope?"**
   → Defines the anti-goals

6. **"Are there technical constraints I should know about?"**
   → Defines constraints (existing DB, external API, performance, regulation...)

**Conversation rules:**
- If the information is already clear from the master plan, CLAUDE.md or the prior conversation, do NOT repeat the question. Use what you already know.
- If the user gives short answers, propose details yourself and ask for confirmation instead of forcing long answers.
- If the phase is small (< 4h of work), simplify: only questions 1, 3 and 5. The rest are inferred.

### Step 4: Generate the draft

Read the template `docs/templates/X.spec.md` and use it as the base to generate the file `docs/plans/phase_X/X.spec.md`.

**Level of detail by phase size:**

| Phase size | What to include |
|---|---|
| **Small** (< 1 day) | Objective + acceptance criteria + anti-goals. No detailed contracts. |
| **Medium** (1-5 days) | Full template. Data contracts with main fields. |
| **Large** (> 5 days) | Full template with maximum detail. Explicit JSON schemas. All endpoints. |

**Rule of thumb**: if the phase touches >5 files, it deserves explicit data contracts. If it touches 1-3 files, user stories and acceptance criteria are enough.

### Step 5: Review and approval

Present the full draft to the user and ask:
> "Is anything incorrect, missing or superfluous?"

Incorporate the corrections. The file is then locked: it is not modified during implementation unless the phase scope changes.

### Step 6: Next step

After saving the file, say:
> "Spec for Phase X is ready. Run `/5-plan` to create the implementation plan."
