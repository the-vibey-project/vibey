---
id: skill-10-content-and-ux-writing-da276c49a0
purpose: 10 content and ux writing
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-writing-forms-research-and-ethics/SKILL.md
requires: []
links: ["skill-11-forms-onboarding-and-conversion-7db671e793"]
---

## §10. Content and UX Writing

**[DURABLE] The interface is mostly words.** Most "confusing UI" is confusing *language*
wearing a layout.

### 10.1 Principles

- **Clarity beats cleverness. Always.** Nobody has ever been delighted by a witty error
  message they couldn't act on.
- **Front-load the meaningful words.** Users scan the first two words of a link, heading,
  or bullet. "Download the annual report (PDF)" not "Click here to download…"
- **Use the user's vocabulary**, sourced from research, support tickets, and search logs —
  not the database schema and not marketing.
- **Be consistent.** One concept, one word, everywhere. If it's a "workspace" in nav it's
  not a "team" in settings.
- **Active voice, present tense, second person.** "Your changes are saved" not "Changes
  have been saved by the system."
- **Sentence case** for UI labels reads faster than Title Case and is the modern convention
  on every major platform.
- **Numbers, dates, and units are localized.** `1,234.56` vs `1.234,56` is a real bug.

### 10.2 The high-value surfaces

**Buttons** — a verb naming the outcome. "Save changes", "Create account", "Delete
project". Never "OK", "Submit", "Yes/No" for consequential choices. The button label must
match the heading that preceded it.

**Error messages** — three parts, in this order:
1. **What happened**, plainly. ("We couldn't process your payment.")
2. **Why**, if you know and it's actionable. ("Your card was declined by your bank.")
3. **What to do next.** ("Try another card, or contact your bank.")
Never blame the user, never expose a stack trace or code as the only content (a support
reference code *in addition* is fine and useful), never say "invalid input" without saying
which input and what would be valid.

**Empty states** — the most under-designed screen in most products, and a first-run user's
first impression. It should: explain what belongs here, why it's empty, and give one clear
action to fill it. Distinguish *first-use empty* (teach), *user-cleared empty* (celebrate or
reassure), *no-results empty* (offer alternatives and a way to broaden), and *error empty*
(diagnose).

**Loading and progress** — say what's loading. "Loading your invoices" beats a spinner.

**Confirmation and success** — name what happened and offer the next step. This is the
"end" in peak-end (§1.4 → `ui-ux-cognition-heuristics-and-navigation`) and it's cheap to do well.

**Microcopy on inputs** — a persistent hint below the field (not a placeholder) explaining
format requirements *before* the user fails, not after.

### 10.3 Localization affects design, not just strings

- **Text expansion**: German/Finnish run 30–40% longer than English; some languages 100%+
  for short strings. Fixed-width buttons break. Design for expansion or use flexible
  layouts and test with pseudo-localization.
- **RTL (Arabic, Hebrew, Farsi)** mirrors the entire layout — navigation, icons with
  directionality (back arrows, progress), and reading order. Use *logical* properties
  (`margin-inline-start`, not `margin-left`) and test with a force-RTL flag.
- **Never concatenate translated fragments.** Word order differs; use positional format
  strings.
- **Plurals need real plural rules** (Arabic has six categories), not `if (n === 1)`.
- **CJK** has different line-breaking, no spaces between words, and different comfortable
  line-heights; ideographs need more vertical space.
- **Names, addresses, phone formats, honorifics, and date orders are not universal.** A
  required "First name / Last name" split is wrong for a large fraction of the world.

---
