---
id: skill-6-building-services-mep-and-fire-safety-8bf3a323cc
purpose: 6 building services mep and fire safety
source: src/vibey_tools/skills/plugins/building-a-homestead/skills/homestead-services-sequencing-and-codes/SKILL.md
requires: []
links: ["skill-7-construction-sequencing-codes-and-permitting-723e9e9178"]
---

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
