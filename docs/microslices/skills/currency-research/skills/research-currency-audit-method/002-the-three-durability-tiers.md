---
id: skill-the-three-durability-tiers-ae599ef06b
purpose: the three durability tiers
source: src/vibey_tools/skills/plugins/currency-research/skills/research-currency-audit-method/SKILL.md
requires: ["skill-the-default-answer-is-no-change-bdce511c63"]
links: ["skill-what-counts-as-a-finding-e29459d6e8"]
---

## The three durability tiers

References in this marketplace tag claims by how durable they are. The tier determines
whether a claim is even a candidate for the audit.

| Tier | What it is | Audit treatment |
|---|---|---|
| **Stable fundamentals** | Physical law, mathematics, settled mechanism, historical fact | **Do not audit.** If you think one changed, you have misread it or found a genuinely extraordinary result — treat with proportionate scepticism. |
| **Versioned specifics** | Standard versions, API surfaces, product tiers, regulatory thresholds, prices, market shares, adoption figures | **The main target.** These have a shelf life measured in months. |
| **Contested questions** | Live scientific or scholarly disputes, replication status, unsettled policy | **Audit the state of the dispute, not the answer.** The correct update is usually "the balance of evidence shifted" or "a major replication landed", not "the question is now settled". |

A plugin's `> **Currency:**` header line names the section holding its dated claims. That
line is the brief — it tells you what the author already knew would age first.

---
