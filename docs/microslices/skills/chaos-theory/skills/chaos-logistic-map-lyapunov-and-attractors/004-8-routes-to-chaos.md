---
id: skill-8-routes-to-chaos-d4c54ac808
purpose: 8 routes to chaos
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-logistic-map-lyapunov-and-attractors/SKILL.md
requires: ["skill-7-strange-attractors-4af5da0741"]
links: []
---

## §8. Routes to Chaos

**⚠️ Chaos does not arrive arbitrarily — there are a small number of characteristic
routes, and identifying which one you're on tells you what to expect.**
```
PERIOD-DOUBLING CASCADE   ⚠️ Feigenbaum. Infinite cascade in finite parameter range (§5)
QUASI-PERIODIC            ⚠️ Ruelle-Takens-Newhouse (1971): fixed point → limit cycle
                          → torus → chaos, after only a FEW bifurcations
                          ⚠️ This overturned Landau's picture of turbulence as an
                          infinite sequence of frequencies
INTERMITTENCY             ⚠️ long near-regular stretches interrupted by irregular bursts;
                          bursts become more frequent as the parameter increases
                          (Pomeau-Manneville types I, II, III)
CRISIS                    sudden expansion or destruction of an attractor
```
**⚠️ Intermittency is the one to recognize in real data** — **a system that looks periodic
most of the time with occasional bursts is not a periodic system with noise; it may be
chaotic, and the distinction has different implications for control.**
