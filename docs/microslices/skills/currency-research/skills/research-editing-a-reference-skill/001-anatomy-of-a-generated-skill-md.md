---
id: skill-anatomy-of-a-generated-skill-md-d79fb44212
purpose: anatomy of a generated skill md
source: src/vibey_tools/skills/plugins/currency-research/skills/research-editing-a-reference-skill/SKILL.md
requires: []
links: ["skill-the-cross-reference-rule-a7168b3a36"]
---

## Anatomy of a generated SKILL.md

```
---
name: <matches the directory name>
description: "<the trigger — what makes Claude load this skill>"
---

# <Plugin short name>: <Part title>

> **Part 3 of 6** of the *<Display Name>* reference (plugin `<plugin>`), covering §13–§18.
> Sibling skills: `x` (§0–§5), `y` (§6–§12), … . Section numbers are shared across the set;
> a reference written as §N → `skill` points into that sibling skill.
>
> **Currency:** <one or two sentences>. See §27 → `foo-reference` for <what moved>.

> <the document's own scope blockquote — identical in every skill of the plugin>

---

## §13. <Section title>
…
---

## §14. <Section title>
…
```

Three consequences:

- **The header blockquote is generated,** not authored. Do not hand-edit the `Part i of n`
  line or the sibling list; they are derived from the split.
- **The scope blockquote is duplicated across every skill in the plugin.** If a currency edit
  touches it, it must be changed identically in all of them or the plugin becomes inconsistent.
- **Section numbers are shared across the whole plugin**, not per skill. `§14` means the same
  section whichever skill you are reading.

---
