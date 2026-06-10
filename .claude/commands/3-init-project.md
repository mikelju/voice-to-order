# Command /3-init-project

Generates or updates `CLAUDE.md` **by reading the project's real code**.

> This command requires that code already exists. If the project is empty, first run
> `/1-create-master-plan` to define the product, then create the project scaffold
> (e.g. `npm create vite@latest`, `npx create-next-app`, etc.) and then run `/3-init-project`.

---

## Why CLAUDE.md cannot be written by hand from scratch

`CLAUDE.md` is not a document of intentions — it is a **mirror of the real code**.
It contains the exact commands from `package.json`, the architecture that actually exists in the files,
the gotchas that are only discovered by reading the code, and the conventions already in use.

Inventing it before the code exists produces a CLAUDE.md full of assumptions that later
diverges from reality and confuses the agent instead of helping it.

**The correct order is always:**
```
/1-create-master-plan  →  project scaffold  →  /3-init-project
```

---

## Protocol

### Step 1: Verify that there is code

Check that at least one of these files exists:
- `package.json` (Node/JS/TS project)
- `requirements.txt` or `pyproject.toml` (Python)
- `Cargo.toml` (Rust)
- `go.mod` (Go)
- Any source code file

If none exists, stop and say:
> "The project has no code yet. Create the project scaffold first and run `/3-init-project` again."

### Step 2: Read the sources of truth

Read in this order:

1. **`package.json`** (or equivalent) → name, version, scripts, dependencies and devDependencies.
2. **`.env.example`** (if it exists) → required environment variables.
3. **`docs/plans/0_master_plan.md`** (if it exists) → product description and phases.
4. **Configuration files**: `tsconfig.json`, `vite.config.ts`, `next.config.js`, etc.
5. **Main code files**: backend and frontend entry points (infer from the folder structure).
6. **`README.md`** (if it exists) → project description.
7. **`git log --oneline -10`** → recent history to understand the state.

### Step 3: Infer the architecture

From the code you read, determine:

- **Server pattern**: Plain Express? Express + Vite middleware? Next.js? API separate from the frontend?
- **State/session management**: cookies? JWT? in-memory session? database?
- **Database**: which ORM or driver? Is it configured or just installed?
- **Authentication**: OAuth? JWT? NextAuth? custom?
- **External APIs**: which third-party services are used?
- **Observed code conventions**: naming, folder structure, repeated patterns.

### Step 4: Identify gotchas

Gotchas are the things that are **only known by reading the code** and that, if the agent does not know them, lead to mistakes.

Actively look for:
- Temporary solutions or comments explaining why something is done in a non-obvious way.
- Dependencies installed but not used yet (planned debt).
- Environment variables with non-standard names or default-value logic.
- Known limitations documented in comments.
- Counterintuitive configurations (e.g. `trust proxy`, `noEmit: true`, etc.).

### Step 5: Define agent permissions and anti-patterns

This step defines the agent's autonomy limits and forbidden practices. It is done through a brief conversation with the user.

**Question 1** (if not inferable from the code):
> "Are there actions I should ALWAYS do without asking? For example: running tests, following naming conventions, typing everything..."

**Question 2:**
> "Are there actions where I should STOP and ask you for confirmation before executing? For example: changing the DB schema, adding dependencies, touching CI/CD..."

**Question 3:**
> "Are there patterns or practices that are FORBIDDEN in this project? For example: try-catch with rethrow, business logic in controllers, raw SQL without an ORM..."

If the user has no clear preferences, propose these defaults:

```
✅ ALWAYS: run tests, follow CLAUDE.md conventions, type functions
⚠️ ASK: DB schema changes, new dependencies, infra/CI changes
🚫 NEVER: commit secrets, delete tests without resolving them, edit generated files
```

Ask for confirmation before including them.

### Step 6: Propose security tooling for the stack

Before generating `CLAUDE.md`, propose to the user the security dependencies that complement the `/8-audit` command and the CI workflow (`.github/workflows/security.yml`). If the user accepts, add them to the project manifest as optional dependencies.

**Python** (detected via `pyproject.toml` / `requirements.txt`):

```toml
# Add to pyproject.toml -> [project.optional-dependencies] -> security
security = [
    "bandit[toml]>=1.7",       # SAST (insecure patterns in the AST)
    "pip-audit>=2.7",          # CVEs in dependencies
    "detect-secrets>=1.5",     # hardcoded secrets
    "safety>=3.2",             # second opinion on CVEs
]
```

Installation: `pip install -e ".[security]"`.

**JS/TS** (detected via `package.json`):

```json
"devDependencies": {
    "eslint-plugin-security": "^3.0",
    "audit-ci": "^7.1"
}
```

`npm audit` ships with npm; nothing extra needs to be installed.

**Both cases:** mention to the user that the workflow `.github/workflows/security.yml` already runs these scanners in CI, so installing them locally is optional for development (it enables `/8-audit` with automated scanning in the skill's Phase 2).

If the user declines or prefers to postpone, document it in CLAUDE.md in the gotchas section ("security tooling postponed — pending installation").

### Step 7: Generate CLAUDE.md

Read the template `docs/templates/CLAUDE_project.md` and use it as the base to generate `CLAUDE.md` at the project root. Fill in each section with the information obtained in the previous steps.

### Step 8: Confirmation and next step

After writing the file, present a summary of what was documented and ask:
> "Is there anything I inferred incorrectly or anything you want to add?"

Incorporate the corrections and confirm that CLAUDE.md is ready.

Tell the user:
> "CLAUDE.md generated. From now on:
> - Run `/prime` at the start of each session to load the context.
> - Run `/4-specify` before starting each new phase.
> - Run `/5-plan` to create the implementation plan after the spec."
