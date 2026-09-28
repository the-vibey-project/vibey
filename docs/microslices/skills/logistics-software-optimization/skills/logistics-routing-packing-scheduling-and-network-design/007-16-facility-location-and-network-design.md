---
id: skill-16-facility-location-and-network-design-43d135b9f3
purpose: 16 facility location and network design
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-routing-packing-scheduling-and-network-design/SKILL.md
requires: ["skill-15-scheduling-4d6c60f463"]
links: []
---

## §16. Facility Location and Network Design

```
p-median / p-center   ⚠️ minimize average vs minimize WORST distance —
   these give very different answers, and picking the wrong one is a
   real and common error
UFLP / CFLP           uncapacitated / capacitated facility location
HUB LOCATION          ⚠️ hub-and-spoke vs point-to-point
NETWORK DESIGN        ⚠️ the strategic layer: how many DCs, where, serving what
```
**⚠️ These are strategic (annual) rather than operational (daily), which changes
everything about how you should build them**: **run times of hours are fine; ⚠️ what
matters instead is SCENARIO ANALYSIS and robustness.** **The output people act on is
"how does this decision perform across demand scenarios," not a single optimal
configuration.** ⚠️ **Present a frontier, not an answer.**
