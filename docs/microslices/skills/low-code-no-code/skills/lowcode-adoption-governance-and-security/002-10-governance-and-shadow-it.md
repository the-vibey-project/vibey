---
id: skill-10-governance-and-shadow-it-7cf26db979
purpose: 10 governance and shadow it
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-adoption-governance-and-security/SKILL.md
requires: ["skill-9-when-to-use-and-when-not-to-496245990d"]
links: ["skill-11-licensing-and-cost-traps-7f2c804c01"]
---

## §10. Governance and Shadow IT

**[DURABLE] Low-code doesn't create shadow IT — it makes it fast, and it makes it look
sanctioned.**

**The problems that show up 6–18 months in**: nobody knows how many apps exist; the builder
left; there's no test environment; it processes PII nobody catalogued; it holds credentials
in plain text; it's now load-bearing for a business process; it duplicates three other
apps; **and it has no owner.**

**[DURABLE] A governance model that actually works**, rather than the two failure modes of
*ban everything* (drives it underground) and *allow everything* (the list above):

```
TIER 1  Personal productivity     → free rein, no data leaving, no shared dependency
TIER 2  Team tools                → registered, named owner, reviewed data access
TIER 3  Business-critical         → IT-managed, backed up, tested, DR plan,
                                    and a documented escape hatch (§13)
```
**Plus**: a **Centre of Excellence** with templates and patterns rather than gatekeeping;
**an environment strategy** (dev/test/prod — ⚠️ **most citizen development has none**);
**a data-classification rule** that's actually enforced; **a connector allowlist**;
**mandatory ownership records with a review cadence**; and **an offboarding process that
catches orphaned apps** — because that is how they become unowned.

---
