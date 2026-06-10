# Command /1-create-master-plan

Generates the `docs/plans/0_master_plan.md` file for a new project, or updates it if it already exists.
This is the **first command to run** in any new project, before writing a single line of code.

---

## Fundamental rule

**The master plan is only updated after testing and verifying that things work.** It is not touched when creating tools, planning or writing code — only when the work has been executed and confirmed to work correctly. The master plan reflects verified real state, not intentions.

## When to use this command

- **New project**: you have an idea but there is no code yet. This command defines what you are going to build.
- **Existing project without a plan**: there is already code but the roadmap is undocumented.
- **Roadmap review**: the product has evolved and the master plan is outdated. Only update with changes that have already been tested.

---

## Protocol

### Step 1: Gather existing information

Before asking questions, check whether any context already exists:

- Does `docs/plans/0_master_plan.md` exist? → read it to avoid repeating what is already defined.
- Does `CLAUDE.md` exist? → read it to learn the stack and architecture already decided.
- Does `package.json` exist? → read it to infer the actual tech stack.
- Are there git commits? → run `git log --oneline -5` to understand what has already been built.

### Step 2: Discovery conversation

Ask the following questions **one at a time**, waiting for an answer before continuing.
Do not ask them all at once — the goal is a conversation, not a form.

1. **What problem does this product solve?** (in one sentence)
2. **Who uses it?** (type of user, company or person)
3. **What is the minimum MVP that would already be useful?** (what does it have to do to be useful on day one)
4. **What is the long-term vision?** (where do you want to be in 6-12 months)
5. **What tech stack will you use?** (if they do not know yet, propose options based on the project type)
6. **Are there natural phases in the product's evolution?** (e.g. core functionality first, then multi-user, then payments)

If the project already has code or a `CLAUDE.md`, skip the questions whose answers you already know.

### Step 3: Propose the phases

Based on the answers, propose a breakdown into phases with these criteria:
- Each phase must be usable on its own (not depend on the next one to have value).
- Phase 1 must always be the smallest possible functional MVP.
- Maximum 6-7 phases. If there are more, group them.

Present the phase proposal to the user and **ask for confirmation before writing the file**.

### Step 4: Generate the file

Read the template `docs/templates/0_master_plan.md` and use it as the base to generate `docs/plans/0_master_plan.md`. Fill in the phases confirmed by the user.

### Step 5: Next step

After creating the file, tell the user:

> "The master plan is ready. The next steps are:
> 1. **Create the project scaffold** (e.g. `npm create vite@latest`) if there is no code yet
> 2. **`/3-init-project`** to generate the `CLAUDE.md` from the real code
> 3. **`/4-specify`** to create the functional spec for Phase 1
> 4. **`/5-plan`** to create the implementation plan for Phase 1"
