# CLAUDE.md — [Project Name]

Project rules and context for the agent. Always read before making changes.

---

## What is this project?

[2-3 sentences: what it does, who it is for, current development status]

---

## Development commands

```bash
[dev-command]       # Start in development mode
[test-command]      # Run tests
[build-command]     # Build for production
[lint-command]      # Linting and formatting
[db-command]        # Database migrations (if applicable)
```

**To start:** `[exact command]` — opens `[URL]`

---

## Architecture

### File structure

```
src/
├── [folder]/       # [description of what it contains]
├── [folder]/       # [description]
├── [folder]/       # [description]
└── [file]          # [description]
tests/
└── [structure]     # [mirror of src/ or convention used]
```

### [Main architectural pattern]

[Explanation of the pattern the project follows (MVC, Router→Service→DataClient,
hexagonal layers, etc.) and why it was chosen]

### [Other relevant patterns]

[Other important patterns: how state is managed, how DB connections
are handled, how routes are structured, etc.]

---

## Tech Stack

| Layer | Technology | Version |
|------|-----------|---------|
| Runtime | [e.g. Node.js] | [e.g. 20 LTS] |
| Framework | [e.g. Express] | [e.g. 4.18] |
| Language | [e.g. TypeScript] | [e.g. 5.3] |
| Database | [e.g. PostgreSQL + Prisma] | [e.g. 16 / 5.x] |
| Tests | [e.g. Vitest] | [e.g. 1.x] |
| Deployment | [e.g. Docker + Cloud Run] | — |

---

## Environment variables

```env
DATABASE_URL=        # Database connection
[VARIABLE]=          # [what it is used for]
[VARIABLE]=          # [what it is used for]
```

---

## Code conventions

- [Convention observed in the real code — e.g. "async/await functions, never callbacks"]
- [Convention — e.g. "Named exports, never default export"]
- [Convention — e.g. "camelCase for variables, PascalCase for components"]
- [Convention — e.g. "Tests placed in tests/ mirroring the src/ structure"]

---

## Agent permissions

✅ **ALWAYS** (do without asking):
- [e.g. Run tests before declaring a task complete]
- [e.g. Follow the project's naming conventions]
- [e.g. Type all new functions]

⚠️ **ASK FIRST** (pause and request confirmation):
- [e.g. Modify the database schema]
- [e.g. Add new dependencies to package.json]
- [e.g. Change CI/CD or deployment configuration]

🚫 **NEVER** (forbidden without exception):
- [e.g. Commit secrets or credentials]
- [e.g. Delete tests without resolving them first]
- [e.g. Edit files in node_modules/ or generated files]
- [e.g. Write business logic directly in controllers/routers]

---

## Project anti-patterns

🚫 [Forbidden pattern] — [why it is forbidden and what to do instead]
🚫 [Forbidden pattern] — [correct alternative]
🚫 [Forbidden pattern] — [correct alternative]

---

## Known gotchas

1. [Non-obvious thing that, if the agent does not know it, will lead to a mistake]
2. [Counterintuitive configuration and why it exists]
3. [Active temporary workaround and when it can be removed]
4. [Known limitation that cannot be solved now]

---

## Evolution plan

The full roadmap is in `docs/plans/0_master_plan.md`.

**Before any change:**
- New phase → `/4-specify` → `/5-plan` → `/6-implement` → `/7-verify` → `/8-audit` → `/9-document`
- Bug fix → `/5-plan` (if not trivial) → `/6-implement` → `/7-verify` → `/8-audit` (if it touches auth, crypto, external input, subprocess or deserialization)
- Before packaging/release → `/8-audit full` as the release gate

Invoke `/prime` at the start of every session to load the context.

---

## Security audit

The `/8-audit` command (`audit-code` skill in `.claude/skills/`) runs a professional security audit before `/9-document`. It is a **mandatory** step of the phase flow when the code touches:

- Authentication / authorization
- Cryptography or credential storage
- External input (email, web, user-uploaded files)
- `subprocess` / command execution
- Deserialization (pickle, yaml.load, json.loads on unvalidated input)
- New or updated dependencies

The audit produces a report in `docs/security/audit-YYYY-MM-DD-<mode>.md` with severity, CWE, OWASP, file:line and a proposed fix. Each blocking finding (Critical/High) is resolved with a `fix-N` before closing the phase. The consolidated catalog lives in `docs/security/README.md`.

See `CLAUDE_GLOBAL.md` → "Security audit" section for the detailed rules.
