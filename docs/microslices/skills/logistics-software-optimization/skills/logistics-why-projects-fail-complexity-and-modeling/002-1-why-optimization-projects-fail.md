---
id: skill-1-why-optimization-projects-fail-2d0be2898b
purpose: 1 why optimization projects fail
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-why-projects-fail-complexity-and-modeling/SKILL.md
requires: ["skill-0-routing-965104c790"]
links: ["skill-2-complexity-honestly-fcb56ba9f5"]
---

## §1. ⚠️ Why Optimization Projects Fail

**⚠️ Ranked roughly by how often I'd expect each to be the actual cause:**
```
1. ⚠️ THE DATA IS WRONG. Bad addresses, stale service times, wrong vehicle
   capacities, missing time windows. ⚠️ The optimizer faithfully optimizes
   a fiction and produces a confidently infeasible plan
2. ⚠️ HIDDEN CONSTRAINTS. "You can't send Dave to that site." "That customer
   must be first." "The forklift can't reach aisle 12 after 3pm."
   ⚠️ These live in people's heads and surface only when the plan is rejected
3. ⚠️ THE OBJECTIVE ISN'T WHAT THEY SAID. They said "minimize cost." They
   meant "don't upset the big customer, keep drivers on familiar routes,
   and never be late to the hospital"
4. ⚠️ NOBODY TRUSTS IT. A black box that outputs a different plan every day
   loses to a dispatcher's spreadsheet, even when it's better
5. ⚠️ NO FEASIBLE FALLBACK. Optimizer down or infeasible at 4am → operations
   halts. ⚠️ You need a degraded mode that always produces SOMETHING
6. Runtime doesn't fit the operational window
7. ⚠️ Then, occasionally, the algorithm
```
> **⚠️ GOTCHA — solution STABILITY is an unstated requirement in essentially every
> logistics deployment, and violating it kills more rollouts than poor objective
> values.** ⚠️ **Re-optimizing from scratch each night produces plans that differ wildly
> from yesterday's for a 0.3% gain.** **Drivers lose route familiarity, customers lose
> consistent delivery windows, and planners lose confidence.** **⚠️ Add an explicit
> penalty for deviation from the incumbent plan, and expose it as a tunable knob.**

**⚠️ What to do about it, in order**: **spend your first weeks on data profiling, not
modeling**; ⚠️ **build a feasibility checker and a plan EXPLAINER before you build the
optimizer** — **"why is this stop on this route?" is the question you'll be asked
daily**; **run shadow mode against human plans for weeks before switching**; **and
⚠️ measure against the CURRENT process, not against the theoretical optimum, because that
is the comparison that determines whether the project survives.**

---

# PART I — OPTIMIZATION FOUNDATIONS

---
