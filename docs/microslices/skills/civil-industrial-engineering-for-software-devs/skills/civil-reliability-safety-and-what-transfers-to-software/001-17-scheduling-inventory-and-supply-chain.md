---
id: skill-17-scheduling-inventory-and-supply-chain-dab8c099fd
purpose: 17 scheduling inventory and supply chain
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-reliability-safety-and-what-transfers-to-software/SKILL.md
requires: []
links: ["skill-18-human-factors-and-ergonomics-bc131ff60b"]
---

## §17. Scheduling, Inventory and Supply Chain

**Job shop vs flow shop; ⚠️ scheduling rules (SPT minimizes average flow time — the
shortest-job-first result software knows from schedulers; EDD minimizes maximum lateness);
⚠️ and the fact that most scheduling problems are NP-hard, so practice runs on heuristics.**
**Inventory**: **EOQ, safety stock, ⚠️ reorder points, and the newsvendor problem
(⚠️ single-period stocking under uncertainty — the maths behind capacity provisioning
decisions).**
**⚠️ The BULLWHIP EFFECT is the one to know**: ⚠️ **demand variability AMPLIFIES as it
propagates upstream through a supply chain, caused by batching, lead times, and each stage
reacting to its immediate signal rather than true demand.**
**⚠️ The software analogue is retry storms and cascading failure** — ⚠️ **each layer
reacting to its immediate upstream signal, amplifying it, until the whole system
oscillates.** **Exponential backoff with jitter is the damping mechanism, and it's the same
problem.**

---
