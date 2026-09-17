---
name: homestead-services-sequencing-and-codes
description: "Use when sizing heating, ventilation, electrical or plumbing for a house, allocating ceiling void and services space, setting fire escape and detection provisions, ordering the trades from site preparation to certificate of occupancy, or preparing for plan review and inspections. Covers MEP coordination, structural fire resistance by material, the nine-stage build sequence, temporary works, IRC prescriptive versus engineered design, and the full house build checklist. Part 3 of the Building a Homestead reference."
---

# Services, Fire, Sequencing and Codes

> **Part 3 of 8** of the *Building a Homestead* reference (plugin `building-a-homestead`), covering
> §6–§7 — MEP, fire safety, the order the trades run in, permitting, and the house build checklist. Sibling skills:
> `homestead-site-structure-and-materials` (§1–§3 — ground investigation, solar orientation, the gravity and lateral systems, and choosing a structural material),
> `homestead-envelope-and-building-physics` (§4–§5 — the four control layers in priority order, drying potential, and the materials that make them up),
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

## §6 Building Services (MEP) and Fire Safety

MEP — mechanical, electrical, plumbing — is typically a large fraction of the cost and nearly all of
the coordination problem. A building is a multi-disciplinary system delivered by parties with
different contracts, different liabilities, and different incentives, and most building failures are
not engineering failures — they are coordination failures at the boundaries between disciplines and
between design and construction. MEP is where those boundaries are densest.

### 6.1 The three disciplines

| Discipline | Scope | The governing points |
|---|---|---|
| **Mechanical** | Heating (furnace, boiler, heat pump), cooling, ventilation | Heat pumps are the modern choice — they provide both heating and cooling and are the most efficient option in most climates. Ventilation is an indoor-air-quality requirement, not a comfort one. |
| **Electrical** | Supply capacity, distribution panel, lighting, emergency systems | Supply capacity sized for the loads including future EV charging. Distribution panel with enough circuits. Lighting LED throughout. Smoke detectors, GFCI/AFCI protection per code. |
| **Plumbing and drainage** | Gravity drainage, venting, water supply, hot water | Gravity drainage means falls. Every fixture needs a vent. Water supply needs adequate pressure. Hot water circulation or point-of-use heaters for long runs. |

**Mechanical.** Heat pumps provide both heating and cooling and are the most efficient option in most
climates. Ventilation is an indoor-air-quality requirement, not a comfort one — every occupied
building needs fresh air, and modern airtight construction makes mechanical ventilation (HRV or ERV)
essential. Airtightness is pursued for durability as well as energy (§4 → `homestead-envelope-and-building-physics`),
which is exactly why the fresh-air supply has to be designed rather than assumed.

**Electrical.** Plan for electrical demand rising with electrification of heating and transportation.
Size the supply for the loads including future EV charging; provide a distribution panel with enough
circuits; use LED lighting throughout; provide emergency systems — smoke detectors, and GFCI/AFCI
protection per code.

**Plumbing and drainage.** Gravity drainage means falls — the drainage layout constrains the plan
more than people expect, especially in basements and conversions. Every fixture needs a vent. Water
supply needs adequate pressure. Use hot water circulation or point-of-use heaters for long runs.
**Plan the plumbing early — it cannot be an afterthought.**

### 6.2 Spatial coordination — the ceiling void

> **SPATIAL COORDINATION — THE CEILING VOID**
>
> Ducts, pipes, cable trays, sprinklers, lighting, and structure all want the same **400mm** of
> ceiling void. Clash detection in BIM catches geometric clashes; it does not catch access for
> maintenance, installation sequence, or the fact that a valve is now above a fixed ceiling in a
> locked room. Plan services space from the start — it is notoriously under-allocated at concept and
> then fought over forever.

### 6.3 Fire safety for a house — escape and detection

For a house, fire safety is primarily about **means of escape and smoke detection**.

- Every **sleeping room** needs a smoke detector, **interconnected**, so one triggers all.
- **Bedrooms need an egress window or door directly to the exterior.**
- Travel distances to exits should be short.
- In larger or multi-story houses, consider a **residential sprinkler system** — the single most
  effective fire safety measure.

### 6.4 Structural fire resistance by material

| Material | Behaviour in fire | What that means for design |
|---|---|---|
| **Heavy timber** | Chars at a predictable rate (**~0.65mm/minute**) | The predictable char rate is how heavy timber is engineered for fire resistance. |
| **Light wood frame** | No usable char reserve in the members | Relies on **gypsum board** for its fire rating. |
| **Steel** | Loses strength rapidly when heated | Must be protected — **intumescent paint or board enclosure**. |
| **Concrete** | Spalls under intense heat | Retains strength longer than steel. |

*Computed from the source figure:* 0.65mm/minute is 39mm of char per hour of fire exposure — the
sacrificial depth a heavy timber member must carry above its structural section.

## §7 Construction Sequencing, Codes and Permitting

### 7.1 The construction sequence

The construction sequence for a house follows a critical path that **cannot be arbitrarily
compressed**.

| # | Stage | Work | Notes |
|---|---|---|---|
| 1 | **Site preparation** | Clear, grade, establish drainage, install temporary erosion controls | Set up utilities temporary connections. |
| 2 | **Foundations** | Excavate, place formwork, place reinforcement, pour concrete, strip formwork, cure | The curing time is not compressible — concrete needs **7–28 days** to reach design strength depending on the mix. |
| 3 | **Framing (structure)** | Erect the structural frame — floor joists, walls, roof | Install shear bracing and temporary lateral bracing. Fast in timber (days to weeks), slower in masonry (weeks to months). |
| 4 | **Enclosure (weatherproof)** | Install roof covering, wall sheathing, house wrap, windows, and doors | The building must be weather-tight before any moisture-sensitive interior work begins. This is the critical milestone — **"dried in."** |
| 5 | **Rough-in (services)** | Plumbing, electrical, HVAC rough-in — all concealed work inside walls and above ceilings | **Must be inspected before closing.** |
| 6 | **Insulation and air sealing** | Install insulation, seal all air leaks, install vapor retarders | Vapor retarders **per climate zone** (§4 → `homestead-envelope-and-building-physics`). |
| 7 | **Interior finishes** | Drywall, plaster, paint, trim, flooring, cabinets | — |
| 8 | **Finish services** | Electrical fixtures, plumbing fixtures, HVAC equipment, appliances | — |
| 9 | **Commissioning and handover** | Test all systems, verify operation, address defects (snagging/punch list) | Obtain **certificate of occupancy**. |

Sequence is also a structural matter: until the diaphragms and shear walls are in place a partially
built structure has no lateral resistance, so temporary bracing is not optional
(§3 → `homestead-site-structure-and-materials`).

### 7.2 Temporary works

> **TEMPORARY WORKS ARE ENGINEERED STRUCTURES**
>
> Formwork and falsework, shoring, scaffolding, excavation support, crane bases, propping during
> demolition — all carry real loads, often on a structure that is not yet capable of carrying itself.
> Formwork failures during concrete pours are a recurring and severe accident category — wet concrete
> is a fluid exerting hydrostatic pressure, and **pour rate is a design input**. Do not skip
> engineering on temporary works.

### 7.3 Codes: what they are and what they regulate

**Building codes are accumulated failure logs — every provision exists because something went wrong.**
For a house, the relevant code in the US is the **International Residential Code (IRC)**, which covers
one- and two-family dwellings. In other jurisdictions, equivalent codes apply.

| What the code regulates | Examples given |
|---|---|
| Structural design | Span tables, load requirements |
| Fire safety | Egress, detection, separation |
| Energy efficiency | Insulation levels, air sealing, window performance |
| Plumbing | — |
| Electrical | — |
| Mechanical | — |
| Accessibility | — |
| Site requirements | Setbacks, height limits |

### 7.4 Prescriptive versus performance

The IRC includes **prescriptive tables** (span tables, insulation tables) that you can follow without
engineering calculations. If your design exceeds the prescriptive limits — **long spans, unusual
shapes, high wind or seismic zones** — you need an engineered design **stamped by a licensed
structural engineer**.

### 7.5 The permitting process

Submit drawings to the local building department → plan review → permit issued → **inspections at
defined stages (foundation, framing, rough-in, insulation, final)** → certificate of occupancy.

Inspections exist because quality is verified, not assumed. Schedule inspections at the right stages —
covering up work before inspection means you may have to open it back up.

### 7.6 Practical advice for owner-builders

> **PRACTICAL ADVICE FOR OWNER-BUILDERS**
>
> Establish the planning constraints before spending on design. Treat pre-application engagement with
> the building department as cheap insurance. Build a **mock-up** of any critical detail — especially
> façade and waterproofing transitions — before committing to the full build. The mock-up is the
> single most effective quality tool: build it, test it, agree it, then it is the benchmark.

This follows from the cost-influence curve: the ability to influence cost is highest at the start and
collapses as design progresses (§1 → `homestead-site-structure-and-materials`).

### 7.7 House Build Checklist

Reproduced in full. This is the part to work from.

**BEFORE YOU BUILD**

- [ ] Get a soil test and geotechnical report.
- [ ] Check zoning, setbacks, height limits, and permitting requirements.
- [ ] Establish the brief: what rooms, what sizes, what performance.
- [ ] Orient for solar gain and natural ventilation.
- [ ] Design the structural grid to suit both parking (if any) and the façade module.
- [ ] Plan services space from the start — risers, plant space, ceiling voids.
- [ ] Resolve the four control layers (water, air, vapor, thermal) at every transition before
      construction.
- [ ] Engage a structural engineer for anything beyond prescriptive code tables.

**DURING CONSTRUCTION**

- [ ] Inspect foundations before pouring — verify reinforcement placement, cover, and formwork.
- [ ] Inspect framing before closing — verify load paths, lateral bracing, hold-downs.
- [ ] Inspect rough-in before closing walls — plumbing pressure test, electrical continuity, HVAC
      duct leakage.
- [ ] Blower-door test after insulation and air sealing.
- [ ] Inspect at every hold point the code requires.
- [ ] Keep concrete moist during curing.
- [ ] Protect wood from rain during construction.
- [ ] Do not cover up work before it passes inspection.

The four control layers named in the checklist are set out in priority order, and the concrete-curing
and wood-protection items are expanded, in §4–§5 → `homestead-envelope-and-building-physics`. The soil
test, geotechnical report, orientation and structural-grid items are set out in
§1–§3 → `homestead-site-structure-and-materials`.
