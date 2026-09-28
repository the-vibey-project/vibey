---
id: skill-13-packing-and-loading-2605610209
purpose: 13 packing and loading
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-routing-packing-scheduling-and-network-design/SKILL.md
requires: ["skill-12-vehicle-routing-the-core-problem-7dceb87c5c"]
links: ["skill-14-assignment-and-matching-065baa1dc2"]
---

## §13. Packing and Loading

```
1D BIN PACKING   ⚠️ First-Fit Decreasing is within 11/9 of optimal and takes
   ten lines. Excellent effort/quality ratio
2D / 3D PACKING  ⚠️ containers, pallets, parcels. Much harder
CUTTING STOCK    ⚠️ the classic column generation application (§4)
KNAPSACK         ⚠️ pseudo-polynomial DP; fine for realistic sizes
```
**⚠️ Real 3D loading constraints that make published algorithms inapplicable**: **load
bearing (⚠️ what can stack on what), orientation restrictions, stability (no floating
boxes), ⚠️ LIFO/unloading sequence tied to the route order (§12), axle weight
distribution, and hazmat separation.**
⚠️ **The route and the load are coupled** — **the best route may be unloadable** — **and
most systems handle this by iterating between a router and a loader rather than solving
them jointly.**

---
