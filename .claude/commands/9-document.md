# Command /9-document

Generates the application's user documentation. It is a practical guide for the person who will USE the application, not for the person developing it.

It runs when a phase is finished or at the end of the project, once the functionality is verified.

---

## Documentation principles

- **Audience**: end user, non-technical. They do not know what an API, an endpoint or a database is.
- **Brevity**: the minimum needed to use the application with confidence. If a sentence is superfluous, remove it.
- **Format**: bullet points whenever possible. Paragraphs only when essential.
- **Emojis**: use them to mark information types and ease visual scanning.
- **Searchable**: clear structure with sections and subsections to quickly find what you are looking for.
- **Examples**: include concrete examples when the textual explanation is not enough.

---

## Protocol

### Step 1: Load context

Read in this order:

1. **`CLAUDE.md`** → product name, what it does, who it is for.
2. **All completed specs** (`docs/plans/phase_X/X.spec.md`) → user stories and acceptance criteria.
3. **The code** → screens, routes, menus, forms, real error messages.

### Step 2: Determine scope

- If the user says "document phase 2" → only that phase's functionality.
- If they say "document everything" → the whole application.
- If they do not say → document all completed phases (with verified spec).

### Step 3: Extract functionality from the specs

For each completed spec:

1. Read the **user stories** (US-1, US-2...).
2. Turn each story into a guide section written from the user's perspective.
3. The **acceptance criteria** become behaviors the user must know (limits, validations, rules).
4. The **constraints** relevant to the user are included as notes.
5. The **anti-goals** are ignored (they are internal, the user does not care).

### Step 4: Review the real application

Do not document from the spec alone — verify against the real code:

- Which screens/views exist?
- Which forms are there and which fields do they have?
- Which error messages can the user see?
- Are there multi-step flows (wizards, processes)?
- Are there shortcuts or non-obvious features?

### Step 5: Generate the documentation

Write the file `docs/USER_GUIDE.md` (or the name the user indicates) following the structure below.

### Step 6: Review

Present it to the user for review:
> "User guide generated. Is anything incorrect, missing or superfluous?"

Incorporate corrections.

---

## User guide structure

```markdown
# [Application Name] — User Guide

> [1 sentence: what this application does and who it is for]

---

## 📋 Table of contents

- [Getting started](#getting-started)
- [Section per feature...]
- [Frequently asked questions](#frequently-asked-questions)

---

## 🚀 Getting started

[The 3-5 minimum steps to start using the application]

1. ...
2. ...
3. ...

---

## [Emoji] [Feature name]

[1 sentence: what you can do here]

### How to [main action]

1. [step]
2. [step]
3. [step]

### What you should know

- [important rule or limit — derived from acceptance criteria]
- [another rule]
- [another rule]

### Example

> [concrete usage example, if it helps understanding]

---

## ❓ Frequently asked questions

**[question the user would ask]?**
[brief answer]

**[another question]?**
[brief answer]

---

## ⚠️ Known issues

- [limitation the user should know about]
- [another limitation]
```

---

## Writing rules

### Do:
- Address the user directly and informally
- Verbs in the imperative: "Click", "Type", "Select"
- Concrete examples: "Type your email, for example: user@example.com"
- Emojis as section markers: 🚀 📋 ✏️ 🔍 📊 ⚠️ ❓ 💡 🔒
- Bullet points for lists of rules, steps or conditions
- Bold for key actions: "Click **Save**"
- Screenshots if the user provides them

### Do not:
- Do not use technical jargon: no "endpoint", no "request", no "OAuth authentication"
- Do not explain how it works internally — only how it is used
- Do not include information for developers
- Do not write long paragraphs — if it is more than 3 lines, turn it into a list
- Do not document features that are not implemented and verified
