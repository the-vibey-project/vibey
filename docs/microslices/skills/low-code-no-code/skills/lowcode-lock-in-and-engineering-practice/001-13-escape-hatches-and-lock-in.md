---
id: skill-13-escape-hatches-and-lock-in-ec9dfa5390
purpose: 13 escape hatches and lock in
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-lock-in-and-engineering-practice/SKILL.md
requires: []
links: ["skill-14-engineering-practice-inside-low-code-0dc3dc6b0c"]
---

## §13. Escape Hatches and Lock-In

**[DURABLE] The question to ask before adoption, not after: how do I get out?**

**The gradient runs**:
```
LOW LOCK-IN   Code you own, in your repo, on your infrastructure
              Standard languages behind a visual editor (dbt: it's just SQL)
              Exportable definitions (JSON/YAML workflows — n8n, Node-RED)
              ⚠️ Proprietary format, documented semantics
HIGH LOCK-IN  Proprietary runtime, proprietary data store, no export
```

**⚠️ The questions to ask a vendor before signing**, and the answers to insist on:
1. **Can I export my logic in a form that means something outside the platform?**
2. **Where does my data live and can I get it out in bulk?**
3. **Can I run this myself if the vendor disappears or triples the price?**
4. **What does the migration path look like — has anyone actually done it?**
5. **⚠️ What's the product's retirement history?** (§2.1 → `lowcode-landscape-automation-and-ai-generation` — LEGO's answer would have been
   informative.)

**[DURABLE] The practical mitigations**: **keep business logic in the data layer where
possible** (a database view or a stored procedure survives the tool); **document what the
workflow does in prose**, because a screenshot of a canvas is not documentation;
**export definitions into version control on a schedule** even if the tool doesn't
integrate properly; **prefer tools whose output is a standard artifact**; and
**⚠️ set a review trigger** — "when this exceeds N users or becomes business-critical, we
reassess" — because the decision to rebuild never gets made without one.

---
