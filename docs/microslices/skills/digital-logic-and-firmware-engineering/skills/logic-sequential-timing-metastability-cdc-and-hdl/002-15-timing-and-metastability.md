---
id: skill-15-timing-and-metastability-ebeef6451d
purpose: 15 timing and metastability
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-sequential-timing-metastability-cdc-and-hdl/SKILL.md
requires: ["skill-14-latches-and-flip-flops-cf61d674e2"]
links: ["skill-16-state-machines-0d3b707caf"]
---

## §15. ⚠️ Timing and Metastability

> **⚠️ §1 → `logic-devices-transistors-cmos-gates-and-power`'s second organizing idea. This is what actually makes digital hardware fail.**
```
⚠️ ⚠️ THE TWO CONSTRAINTS, and they fail differently
   ⚠️ SETUP TIME  data must be stable BEFORE the clock edge.
      ⚠️ Violated by a path being TOO SLOW.
      ⚠️ FIXABLE BY SLOWING THE CLOCK
   ⚠️ HOLD TIME  data must remain stable AFTER the edge.
      ⚠️ Violated by a path being TOO FAST.
      ⚠️ NOT FIXABLE BY SLOWING THE CLOCK — ⚠️ a hold violation
      is a broken chip at any frequency, which is why hold
      failures are far more serious
⚠️ THE PATH EQUATION  ⚠️ clock period ≥ clock-to-Q + logic delay
   + wire delay + setup time − clock skew
⚠️ CLOCK SKEW  ⚠️ arrival time difference between flops.
   ⚠️ It can HELP setup on one path while HURTING hold on
   another — which is why clock tree synthesis targets balance
⚠️ SLACK  ⚠️ the margin. Negative slack = failure. ⚠️ The
   CRITICAL PATH is the worst one, and it sets the frequency
⚠️ ⚠️ METASTABILITY  ⚠️ if setup/hold is violated, the flop can
   enter a state between 0 and 1 and stay there for an
   UNBOUNDED time before resolving randomly
   ⚠️ THERE IS NO CIRCUIT THAT ELIMINATES IT. ⚠️ You can only
   make it ARBITRARILY UNLIKELY by allowing resolution time —
   which is what a two-flop synchronizer buys
   ⚠️ MTBF is the metric, and it improves EXPONENTIALLY with
   the time allowed — which is why adding one more flop stage
   helps so much
```

---
