---
id: skill-3-structural-systems-and-material-selection-a9d3b32f2f
purpose: 3 structural systems and material selection
source: src/vibey_tools/skills/plugins/building-a-homestead/skills/homestead-site-structure-and-materials/SKILL.md
requires: ["skill-2-orientation-and-solar-design-aed6bf3bc2"]
links: ["skill-before-you-commit-to-a-design-8b4cdd6c4c"]
---

## §3 Structural Systems and Material Selection

A structure does two jobs: **carry gravity down, and resist lateral load without falling over. The
second is what usually governs the design.**

### Foundations — where the load path terminates

Shallow versus deep is decided by what is at depth, not by preference. The foundation transfers the
building's load to competent ground.

- **Shallow foundations:** pad or spread footings under individual columns; strip footings under
  load-bearing walls; or a raft/mat foundation that spreads the entire building load across the
  footprint (used on weak or variable ground). Most houses on decent soil use strip footings or a
  raft slab.
- **Deep foundations:** driven piles (displacement, noisy, good verification from driving records)
  or bored piles (quiet, large capacity, harder to verify) — used when the upper soil layers cannot
  support the load and you need to reach stronger material at depth.

**The scale of the thing, for a house on ordinary ground:** strip footings in the region of
**600–900 mm wide and 300–450 mm deep**, bearing on undisturbed soil **below the local frost line**,
with a **150–200 mm** reinforced concrete ground beam. On expansive clay, a stiff raft or
post-tensioned slab. On slopes, stepped footings or a split-level design.

> **THOSE NUMBERS ARE AN ILLUSTRATION, NOT A DESIGN**
> Read them as the order of magnitude a house foundation lands in, and nothing more. Footing width
> follows the load above divided by the allowable bearing pressure of *your* soil; depth follows
> frost penetration, the groundwater table and the depth at which competent material actually
> starts; reinforcement and ground-beam sizing follow the spans, the variability of the ground and
> the seismic and wind demand the building must carry down. Any one of those can move the answer by
> a factor, in either direction — and an under-designed foundation is a differential-settlement or
> collapse problem, not a snagging item. **"Reasonable ground" is not a soil report.** The bearing
> capacity comes from a geotechnical investigation of the site, the dimensions come from a
> structural engineer working to your local code, and both are checked by the authority that
> inspects the work.

> **WATER IS THE RECURRING FOUNDATION PROBLEM**
> Buoyancy and uplift on basements (a lightweight basement can literally float), dewatering and its
> effect on neighbors' settlement, and waterproofing. If you have a basement, waterproofing is not
> optional — it is a design discipline. Use tanking (external waterproofing), a drained cavity
> system, or water-resistant concrete, and plan for the case where the water table is higher than
> you think.

### The gravity system

**The load path: roof → walls → floor → beams → columns → foundation.** Every load needs a
continuous route to the ground. An interrupted path — a removed wall, a beam that nobody designed,
an opening cut without a header — is how buildings fail. **Trace every load from roof to ground
before you build.**

For a typical house the gravity system is: roof trusses or rafters spanning onto exterior and
interior load-bearing walls; floor joists spanning onto walls or beams; walls carrying load down to
the foundation.

- **Timber frame:** dimensional lumber (2x4, 2x6, 2x8, 2x10, 2x12) sized by span tables in the
  building code.
- **Masonry:** the walls carry the load in compression.

### The lateral system

**Wind and seismic loads are the ones that govern structural design.** For a house, the lateral
system is typically **shear walls** — plywood or OSB sheathing nailed to the wall framing, which
resists racking forces and transfers them to the foundation. **Metal straps and hold-downs anchor
the walls to the foundation against uplift and overturning.**

> **A PARTIALLY BUILT STRUCTURE HAS NO LATERAL SYSTEM**
> Until the diaphragms (floor and roof sheathing) and shear walls are in place, the structure has no
> lateral resistance. **Temporary bracing is not optional during construction.** Steel frames must be
> braced during erection. This is why building sequencing matters — you cannot skip steps.

### Material selection for a house

| System | Typical Use | Pros | Cons |
|---|---|---|---|
| Timber frame | Most US houses | Fast, familiar, renewable, easy to modify | Fire and moisture sensitive, span limitations |
| Masonry (brick/block) | UK, Europe, much of world | Durable, thermal mass, fire-resistant | Compression only, needs lateral system, labor-intensive |
| Reinforced concrete | Foundations, slabs, some walls | Strong, durable, fire-resistant | Embodied carbon, needs formwork, curing time |
| Mass timber (CLT) | Growing in residential | Renewable, fast erection, fire-resistant (chars predictably) | Moisture protection during construction, cost |
| Steel frame | Spans, connections | Long spans, fast erection, precise | Needs fire protection, corrosion protection, cost |

The material properties behind these trade-offs — concrete w/c ratio and cover, wood moisture
content and movement, steel connections and corrosion, masonry movement joints — are in
§5 → `homestead-envelope-and-building-physics`. Structural fire resistance by material is in
§6 → `homestead-services-sequencing-and-codes`.

### Serviceability

**A structure can be strong enough and still be unusable.** Deflection (floors bouncing or sagging),
vibration (floor vibration in long spans is a common and expensive complaint), crack control, and
drift limits all govern.

Size floor joists for **deflection and vibration, not just strength** — the code span tables do this
for you, but if you are engineering custom spans, check both. Anything beyond the prescriptive code
tables needs an engineered design stamped by a licensed structural engineer
(§7 → `homestead-services-sequencing-and-codes`).
