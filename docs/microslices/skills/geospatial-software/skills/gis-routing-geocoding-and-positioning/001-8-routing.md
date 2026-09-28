---
id: skill-8-routing-b4fb25541a
purpose: 8 routing
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-routing-geocoding-and-positioning/SKILL.md
requires: []
links: ["skill-9-geocoding-7d5fa67ffd"]
---

## §8. Routing

**⚠️ Road networks are directed graphs with turn restrictions, and the turn restrictions
are what make naive graph libraries insufficient.**

**Algorithms:**
```
Dijkstra                exact, slow on large graphs
A*                      ⚠️ heuristic-guided; the heuristic must be admissible
                        (never overestimate) or you lose optimality
Contraction Hierarchies ⚠️ heavy preprocessing → millisecond continental queries.
                        The standard for static road networks (OSRM)
Multi-Level Dijkstra    ⚠️ better for dynamic costs — traffic, live updates (Valhalla)
Time-dependent          departure-time-varying edge weights
```
**⚠️ CH's limitation is the important one**: **preprocessing bakes in the cost function, so
changing weights means re-preprocessing.** **That's why traffic-aware systems favour MLD
or customizable CH.**

**Engines**: **OSRM** (⚠️ **fast, CH-based**), **Valhalla** (⚠️ **tiled, dynamic costing,
multimodal**), **GraphHopper**, **pgRouting**, and commercial APIs.

**⚠️ Map matching** — snapping noisy GPS traces to the road network — ⚠️ **is usually a
hidden Markov model over candidate road segments, not nearest-neighbour snapping.**
**Naive snapping fails badly on parallel roads, overpasses and tunnels.**
**Isochrones**, **the travelling salesman and vehicle routing problems** (⚠️ **NP-hard —
use OR-Tools or a heuristic, not an exact solver, beyond trivial sizes**).

---
