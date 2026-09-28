---
id: skill-little-s-law-and-wip-limits-4810acb33c
purpose: little s law and wip limits
source: src/vibey_tools/skills/plugins/agile-delivery/skills/delivery-velocity/SKILL.md
requires: ["skill-wsjf-weighted-shortest-job-first-7d77493bd3"]
links: ["skill-pipelined-timeboxes-the-throughput-multiplier-d170db2450"]
---

## Little's Law and WIP Limits

### Little's Law

```
Cycle Time = Work in Progress / Throughput
```

This is not a heuristic or a model — it is a **mathematical identity** (proven by John Little in 1961). If throughput stays constant, halving WIP halves cycle time. This relationship holds for any stable system.

**Empirical confirmation:** Sjøberg et al. (ESEM 2018) analyzed **8,000+ work items across 5 teams over 4 years** and confirmed empirically that "WIP correlates with lead time; lower WIP indicates shorter lead times."

### Why Large Batches Are Dangerous

Reinertsen's analysis: with 25 changes in one batch, assuming a 1% base error rate per change interaction, there is an **88% chance of at least one error**. Debugging complexity grows **quadratically** with batch size.

**TrainHeroic case study:** Reduced batch size from 10+ tickets per release to 1.25 tickets per release → **330% increase in deployment frequency per engineer**.

### WIP Limit Recommendations

- Set WIP limits at **~2/3 of team size** (Featureban simulations across ~90 teams)
- Example: 9-person team → WIP limit of 6
- When prioritizing which WIP item to advance, **always pick the oldest in-progress item first** (this causal mechanism reduced cycle time in the Featureban data, not just correlation)
- Break all work into items deliverable in **1–3 days**

### MoSCoW with WIP Discipline
- **Must-Have**: capped at 60% of sprint effort; these enter WIP first
- **Should-Have**: 20% of effort; pulled in only when Must-Haves clear
- **Could-Have**: the scope release valve — cut when time pressure appears
- **Won't-Have**: explicitly out; documented to prevent scope creep

---
