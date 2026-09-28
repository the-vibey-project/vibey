---
id: skill-18-capacity-and-lifecycle-8074d2ddd7
purpose: 18 capacity and lifecycle
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-endpoints-continuity-itsm-and-vendor-risk/SKILL.md
requires: ["skill-17-governance-frameworks-f2cbd96993"]
links: ["skill-19-vendor-and-third-party-risk-920c443b19"]
---

## §18. Capacity and Lifecycle

**Capacity planning**: **trend, model, plan** — ⚠️ **and remember the queueing result from
§3 → `itgov-infrastructure-layers-compute-storage-and-networking` of an operations context: high utilization means long waits, so planning to 100%
utilization guarantees poor performance.**
**Hardware lifecycle**: **refresh cycles, warranty, end-of-support** (⚠️ **which is a
security deadline, not a suggestion — unsupported systems stop receiving patches**).
**⚠️ Technical debt in infrastructure compounds quietly**: **the unsupported OS running the
one critical application nobody will fund replacing is the standard shape of it**, and
⚠️ **it should be on the risk register with a named owner, not tolerated silently.**

---
