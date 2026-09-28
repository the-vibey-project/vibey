---
id: skill-27-quick-reference-d410b1915a
purpose: 27 quick reference
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-reference/SKILL.md
requires: ["skill-26-books-13fbc1337b"]
links: ["skill-28-method-60183a105e"]
---

## §27. Quick Reference

### 27.1 Picker
| Problem | Where |
|---|---|
| Cycle time too long | ⚠️ **Little's Law: reduce WIP or raise throughput** (§12 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Team is busy but nothing ships | ⚠️ **Utilization near 100%. Queues** (§12 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Added people, got slower | ⚠️ **You didn't add them at the constraint** (§13 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Which improvement to make first? | ⚠️ **Find the bottleneck. Everything else is a mirage** (§13 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Metric moved — investigate? | ⚠️ **Only if outside control limits** (§15 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| System falls over under load | ⚠️ **Design ductile: shed load, degrade** (§4 → `civil-loads-safety-factors-materials-and-foundations`) |
| Reliability target across services | ⚠️ **Series multiplies. Budget explicitly** (§19 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Improve availability cheaply | ⚠️ **Usually MTTR, not MTBF** (§19 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Security backlog prioritization | ⚠️ **Hierarchy of controls. Eliminate > train** (§20 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Post-incident, "human error" | ⚠️ **Ask what made the error likely** (§18 → `civil-reliability-safety-and-what-transfers-to-software`, §20 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Retries causing cascade | ⚠️ **Bullwhip. Backoff with jitter** (§17 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Estimate a large project | ⚠️ **Reference class forecasting, not bottom-up** (§23.2) |
| Arguing for tech-debt investment | ⚠️ **Build the asset register first** (§10 → `civil-codes-licensure-failure-analysis-and-construction`, §23.1) |
| Change looks like a detail | ⚠️ **Hyatt Regency. Re-derive the assumption** (§8 → `civil-codes-licensure-failure-analysis-and-construction`) |

### 27.2 The transferable checklist
- [ ] ⚠️ **WIP is limited somewhere explicit** (§12 → `civil-industrial-engineering-queueing-toc-and-lean`)
- [ ] ⚠️ **The current constraint is identified and named** (§13 → `civil-industrial-engineering-queueing-toc-and-lean`)
- [ ] Utilization is deliberately below capacity (§12 → `civil-industrial-engineering-queueing-toc-and-lean`)
- [ ] ⚠️ **The system degrades gracefully rather than failing suddenly** (§4 → `civil-loads-safety-factors-materials-and-foundations`)
- [ ] Reliability budgeted across the whole path, not per-service (§19 → `civil-reliability-safety-and-what-transfers-to-software`)
- [ ] ⚠️ **Controls chosen from the top of the hierarchy, not the bottom** (§20 → `civil-reliability-safety-and-what-transfers-to-software`)
- [ ] ⚠️ **Normal variation is not being reacted to** (§15 → `civil-industrial-engineering-queueing-toc-and-lean`)
- [ ] Estimates anchored to a reference class of completed work (§23.2)
- [ ] ⚠️ **Someone can stop the line without permission** (§14 → `civil-industrial-engineering-queueing-toc-and-lean`, §20 → `civil-reliability-safety-and-what-transfers-to-software`)

---
