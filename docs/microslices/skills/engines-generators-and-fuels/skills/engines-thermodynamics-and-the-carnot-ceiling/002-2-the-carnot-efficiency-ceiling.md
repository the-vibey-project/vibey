---
id: skill-2-the-carnot-efficiency-ceiling-419b437e89
purpose: 2 the carnot efficiency ceiling
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-thermodynamics-and-the-carnot-ceiling/SKILL.md
requires: ["skill-1-the-four-laws-of-thermodynamics-14c635f97b"]
links: ["skill-3-working-fluid-properties-and-phase-behaviour-6b9f4504d6"]
---

## §2 The Carnot efficiency ceiling

**The most important equation in all of engine engineering:**

    η_Carnot = 1 − T_C / T_H

where T_C and T_H are the **ABSOLUTE** temperatures (Kelvin) of the cold and hot reservoirs.

This is the **maximum possible efficiency of any heat engine operating between those two
temperatures, regardless of design, materials, or engineering skill.** It is a limit set by the
temperatures alone.

- Use Kelvin. Every time. Celsius in this equation produces nonsense, including negative and
  greater-than-unity "efficiencies".
- It is a ceiling, not a target. Real cycles fall well below it; see §4–§6 → `engines-rankine-steam-engines-and-turbines` and
§7–§11 → `engines-otto-diesel-brayton-stirling-and-combined-cycles` for how far, and why.

> **CRITICAL CONSEQUENCE.** This is why raising T_H is the perennial goal in power generation. Every
> improvement in engine efficiency throughout history — higher compression ratios, superheated
> steam, reheat cycles, regenerative cycles, combined cycles — is ultimately an attempt to move heat
> addition to a higher *average* temperature or heat rejection to a lower one. **There is no other
> lever.**

### Why efficiency is a MATERIALS problem

The Carnot limit is also why a **materials** problem — finding metals that survive higher
temperatures — is often the binding constraint on engine efficiency, **not** a thermodynamics
problem. The thermodynamics has been settled since Carnot; what changes is what an alloy will
tolerate at temperature. When an efficiency programme stalls, look first at the hot-section metal,
not at the cycle diagram (§18–§20 → `engines-rebuilding-engines-materials-and-tolerances`).

### Reading the ceiling (editor-computed; no source figures below)

| T_H | T_C = 300 K | T_C = 320 K | T_C = 350 K |
|---|---|---|---|
| 600 K | 50.0% | 46.7% | 41.7% |
| 900 K | 66.7% | 64.4% | 61.1% |
| 1200 K | 75.0% | 73.3% | 70.8% |

Two consequences follow directly from `η = 1 − T_C/T_H`:

- **Returns on T_H diminish.** The ceiling rises with T_H but asymptotically toward 1; each
  additional kelvin at the hot end buys less than the last.
- **A kelvin off the cold end is worth more than a kelvin onto the hot end.** Differentiating,
  ∂η/∂T_C = −1/T_H while ∂η/∂T_H = T_C/T_H²; the ratio of their magnitudes is T_C/T_H, which is
  always less than 1. Cold-end improvements are cheap in thermodynamic terms — which is exactly why
  condenser vacuum matters as much as boiler pressure (§4–§6 →
  `engines-rankine-steam-engines-and-turbines`).
