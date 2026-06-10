# Spec Phase X: [Phase Name]

> Functional specification — WHAT to build and WHY.
> The HOW is defined in the phase plan (X.0_name.md).
> The acceptance criteria are verified with `/7-verify` when the phase is finished.

---

## Problem and objective

**Problem**: [1-2 sentences: what user problem this phase solves]

**Objective**: [1 sentence: what success looks like when this phase is finished]

---

## User stories

### US-1: [Descriptive name]
**As** [type of user],
**I want** [action],
**so that** [benefit].

**Acceptance criteria:**
- [ ] [measurable condition — passes or does not pass]
- [ ] [measurable condition]
- [ ] [measurable condition]

### US-2: [Descriptive name]
**As** [type of user],
**I want** [action],
**so that** [benefit].

**Acceptance criteria:**
- [ ] [measurable condition]
- [ ] [measurable condition]

---

## Data contracts

<!-- Omit this section in small phases (<1 day of work) -->

### [Main model / table / schema]

| Field | Type | Constraints |
|-------|------|---------------|
| id | UUID/INT | PK, auto |
| ... | ... | ... |

**Invariants:**
- [Business rule that must always hold for this data]

### Endpoints

<!-- Omit if the phase exposes no API -->

**[METHOD] [path]**
- Description: [what it does]
- Request: `{ field: type }`
- Response 200: `{ field: type }`
- Error response: `{ error: "message", code: "CODE" }`

---

## Constraints

- [Technical constraint: existing DB, external API, performance...]
- [Business constraint: regulation, data format, limitations...]

---

## Anti-goals (what this phase does NOT do)

- NOT [functionality that could be confused with the scope but is out]
- NOT [another thing explicitly out of scope]

---

## Existing code context

<!-- Omit if it is a new project with no prior code -->

- `path/file` — [what exists and how it relates to this spec]
- `path/other` — [relevant dependency the agent must know about]

<!--
LEVEL-OF-DETAIL GUIDE:

Small phase (<1 day): Problem + objective, 1-2 user stories with criteria, anti-goals.
Medium phase (1-5 days): All sections. Contracts with main fields.
Large phase (>5 days): All sections with maximum detail. Explicit JSON schemas.

Rule: if the phase touches >5 files, include complete data contracts.
-->
