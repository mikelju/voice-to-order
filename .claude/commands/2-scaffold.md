# Command /2-scaffold

Creates the base project structure by running the scaffold commands of the chosen ecosystem.
It runs AFTER `/1-create-master-plan` and BEFORE `/3-init-project`.

---

## When to use this command

- **New project**: the master plan already exists but there is no code yet.
- **Stack change**: the project needs to be reinitialized with a different technology.

---

## Protocol

### Step 1: Verify that a master plan exists

Check whether `docs/plans/0_master_plan.md` exists.

- If it exists → read it to understand what is going to be built.
- If it does NOT exist → say:
  > "There is no master plan. Run `/1-create-master-plan` first to define the project phases."

### Step 2: Ask about the project type

If the project type cannot be clearly inferred from the master plan, ask:

> "What type of project is it?"
> 1. Python backend (FastAPI, Flask, Django)
> 2. Web frontend (React, Vue, Svelte, vanilla)
> 3. Fullstack (Next.js, Nuxt, SvelteKit)
> 4. API / microservice
> 5. CLI / Python script
> 6. Other (describe it)

Wait for an answer before continuing.

### Step 3: Ask about stack details

Depending on the chosen type, ask the necessary details **one at a time**:

**If Python:**
1. "Which framework?" (FastAPI, Flask, Django, none)
2. "Dependency manager?" (uv, poetry, pip)
3. "Python version?" (3.11, 3.12, 3.13 — suggest the most recent stable one)
4. "Database?" (PostgreSQL, SQLite, MongoDB, none)
5. "Testing framework?" (pytest — suggest as default)

**If Node/TypeScript:**
1. "Which framework?" (Express, Next.js, Nuxt, SvelteKit, Vite, other)
2. "Package manager?" (npm, pnpm, bun)
3. "TypeScript?" (yes/no — suggest yes)
4. "Database?" (PostgreSQL + Prisma, SQLite, MongoDB, none)
5. "Testing framework?" (Vitest, Jest — suggest Vitest)

**If another type:**
Ask which scaffold commands are needed and what structure is expected.

**Common questions (all types):**
- "Do you need Docker?" (yes/no)
- "Linting/formatting?" (suggest the ecosystem standard: Ruff for Python, ESLint for JS/TS)

If the user has no clear preferences, use the suggested defaults without asking further.

### Step 4: Run the scaffold

Run the ecosystem's standard commands. Examples by type:

**Python with uv + FastAPI:**
```bash
uv init [project-name]
cd [project-name]
uv add fastapi uvicorn
uv add --dev pytest ruff mypy
```

**Python with pip + FastAPI:**
```bash
mkdir [project-name] && cd [project-name]
python -m venv .venv
pip install fastapi uvicorn
pip install -r requirements-dev.txt  # pytest, ruff, mypy
```

**Node with Next.js:**
```bash
npx create-next-app@latest [project-name] --typescript --tailwind
```

**Node with Vite + React:**
```bash
npm create vite@latest [project-name] -- --template react-ts
cd [project-name]
npm install
```

Adapt the commands to the specific stack chosen. Do not invent — use each ecosystem's official scaffolds.

### Step 5: Create the documentation structure

After the scaffold, make sure the framework folders exist:

```bash
mkdir -p docs/plans/fixes
mkdir -p docs/security
mkdir -p docs/templates
mkdir -p docs/refs
mkdir -p tests
mkdir -p data
mkdir -p .tmp
```

`docs/security/` hosts the `/8-audit` reports + the consolidated findings catalog (`docs/security/README.md`). It is created at scaffold time so the first audit finds its destination ready.

If `docs/templates/` is empty and a source of templates exists (this framework), copy them.

### Step 6: Create .gitignore if it does not exist

If the scaffold did not generate a `.gitignore`, create one appropriate for the stack:

- Python: `.venv/`, `__pycache__/`, `.env`, `.tmp/`, etc.
- Node: `node_modules/`, `dist/`, `.env`, `.tmp/`, etc.
- Common: `credentials.json`, `token.json`, `.env.*`, `!.env.example`

### Step 7: Initialize git if it does not exist

```bash
git init  # only if .git/ does not exist
```

### Step 8: Next step

Tell the user:
> "Scaffold created. Run `/3-init-project` to generate CLAUDE.md by reading the project's real code."
