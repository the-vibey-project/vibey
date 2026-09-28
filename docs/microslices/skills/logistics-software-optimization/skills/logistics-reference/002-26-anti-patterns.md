---
id: skill-26-anti-patterns-b8c3562f0a
purpose: 26 anti patterns
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-reference/SKILL.md
requires: ["skill-25-what-s-live-verified-august-2026-c2fd83c536"]
links: ["skill-27-misconceptions-5ee43cf33f"]
---

## §26. ⚠️ Anti-Patterns

```
⚠️ Building the optimizer before profiling the data (§1)
⚠️ No independent feasibility checker — the optimizer exploits every
   modeling gap and it looks fine until a driver tries it (§12)
⚠️ All-hard constraints, so the answer at 4am is "infeasible" (§5)
⚠️ No bound — you cannot say whether you're 2% or 40% off (§9)
⚠️ Re-optimizing from scratch nightly and destroying route stability (§1)
⚠️ Optimizing the objective operations doesn't actually care about (§1)
⚠️ Big-M set to 1e9 "to be safe" — weak relaxation, numerical garbage (§5)
⚠️ Straight-line distance in the production plan (§22)
⚠️ Flat service time for every stop (§21)
⚠️ Naive full n² distance matrix rebuild every night (§22)
⚠️ Bolting driver hours-of-service on after routing (§12)
⚠️ Routing and load planning solved independently with no iteration (§13)
⚠️ Building a MIP for something that was min-cost flow (§10)
⚠️ Reaching for a genetic algorithm because it's familiar, not because
   it's better — try LNS first (§7, §8)
⚠️ No degraded fallback mode when the optimizer fails (§1)
⚠️ Buying a commercial solver licence before proving solve time is the
   binding constraint (§24)
⚠️ Believing published solver benchmarks apply to your models (§25.1)
⚠️ Piloting quantum optimization instead of tuning your LNS (§25.2)
⚠️ Chasing forecast accuracy while ignoring forecast BIAS (§18)
⚠️ Treating the bullwhip effect as a forecasting problem (§17)
```

---
