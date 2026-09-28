---
id: skill-scoping-a-run-50588e8e57
purpose: scoping a run
source: src/vibey_tools/skills/plugins/currency-research/skills/research-currency-audit-method/SKILL.md
requires: ["skill-the-decision-procedure-9c3879bc89"]
links: ["skill-what-this-audit-is-not-338071cd8b"]
---

## Scoping a run

**Audit only the plugins the run was given.** The rotation exists so that each run is small
enough to do properly; widening it to "while I was in there" turns a reviewable pull request
into an unreviewable one.

Within a plugin, work outward from the currency anchor:

1. the section named in the `> **Currency:**` line — always;
2. any section whose text contains an explicit date, version number, price, percentage or
   "as of" — these are self-identifying;
3. sections covering fast-moving subject matter even when undated — regulation, product
   landscapes, adoption, tooling;
4. everything else — only if something in steps 1–3 turned up a contradiction that implicates it.

**A reasonable run touches one to three claims per plugin, and often none.** If you find
yourself proposing a dozen edits to one plugin, stop and ask whether the plugin was actually
stale or whether you have drifted into rewriting it to your own taste.

---
