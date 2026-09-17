---
name: homestead-envelope-and-building-physics
description: "Use when detailing a wall, roof, window or any penetration and you need the four control layers in the right priority order, when an assembly keeps getting wet or cannot dry, or when specifying concrete, wood, steel or masonry for a house. Covers the rainscreen principle, air leakage as a moisture path, vapor retarder placement by climate, flashing, drying potential, roof falls, and the material properties that actually govern durability. Part 2 of the Building a Homestead reference."
---

# Envelope and Building Physics

> **Part 2 of 8** of the *Building a Homestead* reference (plugin `building-a-homestead`), covering
> §4–§5 — the four control layers in priority order, drying potential, and the materials that make them up. Sibling skills:
> `homestead-site-structure-and-materials` (§1–§3 — ground investigation, solar orientation, the gravity and lateral systems, and choosing a structural material),
> `homestead-services-sequencing-and-codes` (§6–§7 — MEP, fire safety, the order the trades run in, permitting, and the house build checklist),
> `homestead-livestock-digestion-nutrition-and-species` (§8–§10 — why cattle are different, the nutrient requirements that follow, and picking a species),
> `homestead-livestock-housing-health-and-grazing` (§11–§14 — fencing and shelter, biosecurity, reproduction, and the grazing systems with their trade-offs),
> `homestead-soil-and-fertility` (§15–§16 — what soil actually is and how to feed it without wrecking it),
> `homestead-crops-rotation-pests-and-water` (§17–§22 — crop production, why rotation does several jobs at once, IPM, irrigation methods, and an honest look at farming systems),
> `homestead-reference` (§23–§24 — the terms of art across all three domains, and the books that actually teach this),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Building work is governed by local codes and inspection, and livestock by
> local animal-health rules; this reference tells you what to design for and what to ask, not what
> your jurisdiction permits.

## §4 Envelope and building physics — where buildings actually fail

> **WATER DESTROYS MORE BUILDINGS THAN STRUCTURAL FAILURE**
>
> Envelope and moisture management cause the overwhelming majority of building defects,
> claims, and premature failures. This is the least glamorous part of building and the one
> that matters most. Get the envelope right or everything else is wasted.

That framing is the section. The structure gets attention because failure there is dramatic; the
envelope gets the failures. Everything below is ordered by how much damage getting it wrong does.

### The four control layers (in order of importance)

**The ordering is the content.** Water first, then air, then vapor, then thermal — read it as a
priority list, not a list of four equal concerns. Thermal is last, and insulation is the one layer
with a headline number attached to it; do not let that number set the design order.

| # | Layer | Controls | The governing rule | How it fails |
|---|---|---|---|---|
| 1 | **Water** | Bulk liquid water at every surface, penetration and transition | Rainscreen: accept that the outer skin leaks; drain and ventilate behind it | Perfect-barrier design; first sealant failure lets water in with nowhere to go |
| 2 | **Air** | Air leakage, which carries far more moisture into assemblies than vapor diffusion does | Continuous air barrier, every penetration sealed, verified by blower door | Leaks deposit moisture inside walls, where it condenses and rots the structure |
| 3 | **Vapor** | Moisture diffusion through the assembly | Retarder on the warm-in-winter side in heating climates; on the exterior in hot-humid climates | A detail copied from the wrong climate zone traps moisture inside the assembly and rots it |
| 4 | **Thermal** | Heat flow | Continuity, not just thickness | Thermal bridging: heat loss plus local cold surfaces where condensation forms |

**1. Water control** — the most important and the most botched. The building must shed water at
every surface, penetration, and transition. The **rainscreen principle**: accept that the outer skin
leaks; provide a drained and ventilated cavity and a drainage plane behind it. "Perfect barrier"
designs fail at the first sealant failure — and sealant is a maintenance item that degrades. Design
for the sealant being gone, because eventually it is.

**2. Air control** — air leakage carries far more moisture into wall assemblies than vapor diffusion
does. This surprises people and is why airtightness matters for **durability**, not just energy. Air
leaks deposit moisture inside walls where it condenses and rots the structure. Seal every
penetration, use a continuous air barrier, and test with a blower door.

**3. Vapor control** — vapor retarders manage moisture diffusion through assemblies. The vapor
retarder goes on the **warm-in-winter side in heating climates**. In **hot-humid climates the logic
inverts** — the retarder goes on the exterior. Copying a detail from the wrong climate zone traps
moisture inside the assembly and rots it. There is no universally correct wall section; there is a
correct wall section for your climate zone.

**4. Thermal control** — insulation. Not just thickness but **continuity**. Thermal bridging (a
continuous conductive path through insulation, like a steel beam or a balcony slab) causes both
heat loss and local cold surfaces where condensation forms — so a thermal defect becomes a
moisture defect. **Continuous exterior insulation is the most effective way to break thermal
bridges.** (Term of art: *thermal bridge*, §23 → `homestead-reference`.)

Resolve all four layers at every transition **before** construction — that is a design task, and it
is on the pre-build checklist (§7 → `homestead-services-sequencing-and-codes`).

### Flashing

At every penetration and transition — windows, doors, roof intersections, plumbing vents,
chimneys — flashing directs water **out and down**.

- Lap flashing **shingle-fashion**, so water is always directed outward and downward.
- **The rule: if water gets in, it must have a path out.**
- **Two impermeable layers with no drainage between them is a moisture trap.** Adding a second
  impermeable layer to a wall that was drying in that direction removes its drying direction — see
  *Drying potential* below.

Flashing transitions are the detail to build as a mock-up and test before committing to the full
build; the mock-up then becomes the benchmark (§7 → `homestead-services-sequencing-and-codes`).

### Drying potential

Assemblies get wet **during construction and in service** — this is assumed, not a defect.
Therefore: **design so they can dry in at least one direction.**

| Assembly | Dries | Verdict |
|---|---|---|
| Exterior insulation + vapor-permeable sheathing | Inward | Works — has a drying direction |
| Vapor barrier on **both** sides | Neither direction | **Cannot dry at all and will fail** |

The second row is the whole point. An assembly with no drying direction has no tolerance for the
wetting that is certain to happen, so its service life is set by the first leak rather than by the
materials in it.

### Roofs

Roofs are **not flat** — even "flat" roofs have falls (**minimum 2% slope**) to drains.

- **Ponding is a design failure.** Blocked outlets have collapsed roofs under water load — water is
  heavy, it accumulates, and the failure is sudden.
- **Provide overflow provision at every roof drain.** The overflow is what keeps a blocked primary
  outlet from becoming a structural load case.
- **Upstands at parapets and penetrations must be detailed correctly.**
- For residential roofs, **pitched roofs with eaves that overhang the walls** protect the walls from
  water and are **the most forgiving detail** available. A generous overhang is cheap insurance for
  the wall assembly below it.

*(2% is 1 in 50 — about 20 mm of fall per metre of run, or roughly 1/4 inch per foot. Computed from
the source figure, not stated in it.)*

## §5 Materials in construction

Four materials, and for each one a property that governs durability more than the headline number
does. For choosing a **structural system** — timber frame vs masonry vs reinforced concrete vs mass
timber vs steel, with pros and cons — see §3 → `homestead-site-structure-and-materials`.

| Material | The critical property | Most often shortchanged |
|---|---|---|
| Concrete | Water-to-cement ratio; cover to reinforcement | Placement, consolidation, and **curing** |
| Wood | Moisture content, and movement across the grain | Protection from wetting during construction |
| Steel | Connection method and corrosion protection | Fire protection of structural beams |
| Masonry | Compression-only behavior; movement | Movement joints; mortar made stronger than the units |

### Concrete

- The **water-to-cement (w/c) ratio governs strength and durability** — more water means weaker and
  more permeable concrete.
- A typical residential mix is **3000–4000 psi (20–28 MPa)** for foundations and slabs.
- **Placement, consolidation (vibration to remove air pockets), and curing are the steps most often
  shortchanged.**
- **Curing determines durability far more than mix strength** — keep concrete moist for **at least 7
  days** after pouring.
- **Cover to reinforcement is the single most important durability parameter.** Inadequate cover
  lets chlorides and carbonation reach the steel, which rusts and spalls the concrete.

Curing time is also not compressible on the program: concrete needs **7–28 days** to reach design
strength depending on the mix (§7 → `homestead-services-sequencing-and-codes`).

### Wood

- **Moisture content is the critical property.** Wood at **equilibrium moisture content (EMC)** in
  service is typically **8–12% in most climates**.
- Wood moves dimensionally with moisture changes — **across the grain, not along it**. The order of
  movement is **tangential > radial > longitudinal**. This movement is why panels split, joints
  open, and doors stick.
- **Design to accommodate movement, not to resist it.**
- **Pressure-treated lumber for ground contact. Kiln-dried lumber for framing** (dimensionally
  stable).
- **Protect wood from wetting during construction** — this is a genuine program risk, **especially
  for mass timber**.

### Steel

- **Bolted connections are preferred over site welding** — welding is slower, weather-dependent, and
  harder to inspect.
- **Galvanized or stainless steel for corrosion protection** in exposed locations.
- **Light-gauge steel framing** is an alternative to wood framing in some markets.
- **Structural steel beams need fire protection** (see §6 → `homestead-services-sequencing-and-codes`
  for how steel, timber, and concrete behave in fire).

### Masonry

- **Compression only** — it carries gravity well but **cannot span or resist tension without
  reinforcement**.
- **Movement joints are mandatory.** **Brick expands over time, concrete block shrinks, and they
  move in opposite directions** — so a wall combining them is moving against itself.
- **Mortar should be weaker than the units**, so cracks occur in the joint where they can be
  repointed, rather than in the brick or block itself.

## Where this connects

| You need | Go to |
|---|---|
| Whether to build in timber, masonry, concrete, mass timber or steel | §3 → `homestead-site-structure-and-materials` |
| Groundwater, basement waterproofing and tanking | §3 → `homestead-site-structure-and-materials` |
| Fire behavior of timber, steel and concrete; MEP and ceiling voids | §6 → `homestead-services-sequencing-and-codes` |
| When in the build the envelope closes in ("dried in"), and insulation and air sealing order | §7 → `homestead-services-sequencing-and-codes` |
| Definitions of *rainscreen* and *thermal bridge*; Lstiburek on envelope and moisture | §23–§24 → `homestead-reference` |
