# Voice-to-Order — User Guide

> Dictate an order the way a field technician would, and the system turns it into a
> reviewed, sent order — matching every spoken line against a 31,000-article catalog.

---

## 📋 Table of contents

- [🚀 Getting started](#-getting-started)
- [🎙️ Step 1 — Dictate or pick an order](#️-step-1--dictate-or-pick-an-order)
- [📝 Step 2 — Check what was understood](#-step-2--check-what-was-understood)
- [🔍 Step 3 — Choose the right article](#-step-3--choose-the-right-article)
- [✅ Step 4 — Finalize the order](#-step-4--finalize-the-order)
- [📤 Step 5 — Send it](#-step-5--send-it)
- [🌐 Changing the language](#-changing-the-language)
- [❓ Frequently asked questions](#-frequently-asked-questions)
- [⚠️ Known limitations](#️-known-limitations)

---

## 🚀 Getting started

You need Docker, Python 3.12+ and Node 20+. Four commands, then everything runs on your machine.

1. Start the database: `docker-compose -f db/docker-compose.yml up -d`
2. Load the data: `python tools/load_database.py`
3. Start the application: `python serve.py`
4. Start the screen: `cd src/frontend && npm install && npm run dev`

Then open **http://localhost:5173**.

> 💡 No API keys, no accounts, no internet needed. Out of the box you are in **demo mode**,
> which replays 47 real orders that were actually dictated in the field.

---

## 🎙️ Step 1 — Dictate or pick an order

Three ways to start an order:

- **Recorded order** — pick one of the 47 real orders. Best way to see the whole flow.
- **Record with the microphone** — speak the order out loud.
- **Upload a file** — an audio file you already have (mp3, wav, m4a, ogg).

### What you should know

- 📦 Audio files are limited to **25 MB**; anything larger is rejected.
- 🔁 In demo mode, whatever you record or upload replays one of the 47 real orders — the
  point is to show the flow, not to transcribe your voice.
- 🗣️ The orders are dictated in Spanish, the way they are spoken on site: trade slang,
  measurements, abbreviations.

---

## 📝 Step 2 — Check what was understood

You will see what the system heard and what it extracted.

- The **transcription** of what was said.
- The **order number** and the **plant**. A green badge means the plant was confirmed
  against the ERP; without it, check it yourself.
- The **order lines**: quantity, the article as it was said, and a cleaned-up description.

### What you should know

- ⚠️ A **warnings banner** appears when something needs your attention (for example a
  missing order number).
- ✏️ Nothing is sent yet. If a line came out wrong, you fix it in the next step.

---

## 🔍 Step 3 — Choose the right article

This is the important screen. For each dictated line the system proposes catalog articles,
ordered best-first, and you pick.

### How to review a line

1. Read the dictated text on the left.
2. Open the dropdown and look at the proposals.
3. Pick the right article, or search the catalog yourself.
4. Adjust the quantity if it is wrong.

### What you should know

- ⭐ Proposals that come from the **learned memory** — something confirmed for this same
  spoken phrase before — are shown first. They are usually the right ones.
- 🔎 The dropdown is searchable: type several words and it filters by all of them.
- 🔍 **Search catalog** opens a manual search over all 31,000 articles. Type at least
  3 characters.
- 🚫 If nothing matches, the line shows `--- SIN OPCIONES ---`. Lines left like that are
  **not** included in the order.

---

## ✅ Step 4 — Finalize the order

Fill in the delivery details.

- **Deadline** — defaults to three days from today.
- **Plant** — checked as you type; you will see whether it was found.
- **Notes** — anything the supplier should know.
- **Deliver to site** — the order goes to the work site instead of the usual address.
- **Charge only** — record the order without requesting delivery.

### What you should know

- 🔁 Duplicate lines are flagged before you continue.
- 📋 You will see a summary of exactly what will be sent.

---

## 📤 Step 5 — Send it

The order goes out through three independent channels, and you get a light for each one.

| Light | Meaning |
|---|---|
| 🟢 **Order sent** | The order was processed and the PDF is ready |
| 🟢 **ERP** | Registered in the ERP |
| 🟢 **History** | Your choices were learned for next time |

### What you should know

- 📄 The **PDF opens automatically** — download it, it is a real document.
- 🔴 If the ERP light is red, the order is marked as failed. Use **Retry ERP**.
- 🟡 One channel failing does **not** cancel the others: the PDF and the email are
  independent of the ERP.
- 🧠 Every line you confirm is remembered. Next month the same dictated phrase will find
  its article faster and better.
- ➕ **New order** clears everything and starts again.

---

## 🌐 Changing the language

Use the **ES | EN** switch in the top-right corner. Your choice is remembered.

- The **interface** switches language.
- The **data** — dictated text, article descriptions — always stays in Spanish. That is
  the real content of the orders, and translating it would change what you are reviewing.

---

## ❓ Frequently asked questions

**Do I need API keys or an internet connection?**
No. Demo mode works completely offline. Keys are only needed if you switch to real mode.

**Is anything actually sent to a supplier?**
No. The PDF is real; the ERP and email channels are simulated and write their result into
the `.tmp/` folder.

**Is this real data?**
Yes, anonymized. Real catalog, real dictated orders, real learned memory — with every name,
phone number and part number removed or replaced. No audio is published.

**Why does it suggest an article I did not ask for?**
It proposes the closest matches from the catalog, and the catalog is written in supplier
shorthand. Read the description before accepting: `M10*50` is not `M10*25`.

**Can I change my mind after picking an article?**
Yes, at any point before sending. Nothing is final until the last step.

**Something failed. Did I lose the order?**
No. A failed channel is reported with its own light, and the ERP can be retried without
redoing the order.

---

## ⚠️ Known limitations

- 🔒 **Runs on your machine only.** There are no user accounts and no login. Do not put it
  on a network as it is.
- 🎭 **Demo mode does not really transcribe.** Transcription and extraction are replays of
  real validated orders; the catalog search, however, is genuinely running.
- 💸 **Real mode spends money.** With your own keys, roughly US$0.01 per order.
- 🇪🇸 **The data is Spanish.** The interface can be English; the orders cannot.
- 🖥️ **On Windows, start it with `python serve.py`**, not with `uvicorn` directly.
