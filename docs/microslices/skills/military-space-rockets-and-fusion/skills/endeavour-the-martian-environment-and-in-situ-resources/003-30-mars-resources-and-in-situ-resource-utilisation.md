---
id: skill-30-mars-resources-and-in-situ-resource-utilisation-861d2a4f7b
purpose: 30 mars resources and in situ resource utilisation
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-the-martian-environment-and-in-situ-resources/SKILL.md
requires: ["skill-29-the-martian-environment-engineering-parameters-34a90f1f1b"]
links: ["skill-cross-references-78ff51f6b5"]
---

## §30 Mars resources and in-situ resource utilisation

### Water — the most valuable resource, in three reservoirs

| Reservoir | What is there | Accessibility |
|---|---|---|
| **Polar ice caps** | North cap primarily water ice, **~2 million km³** in the residual cap, with a seasonal CO₂ frost layer; south cap has a larger CO₂ component with water ice beneath | Concentrated, but polar |
| **Subsurface ice** | Present within **1–2 m** of the surface at mid-to-high latitudes; **above ~50° latitude likely within centimetres** | Confirmed by Phoenix (excavated ice, 2008) and by crater impacts exposing bright ice that then sublimated |
| **Hydrated minerals** | Clay minerals, sulfates and opaline silica in ancient terrains hold structurally bound water | Requires high-temperature processing |

**Mid-latitude subsurface ice is the accessible feedstock** — drill, excavate, melt, electrolyze.
Water yields hydrogen for propellant, oxygen for life support and propellant, and drinking water for
crews. It is also why landing-site selection is a resource decision as much as a safety one, and why
it collides with planetary protection's special regions
(§28 → `endeavour-satellites-flight-software-and-instruments`).

### The CO₂ atmosphere as feedstock

The atmosphere is ~95% CO₂ at 610 Pa. Thin, but a feedstock.

- **MOXIE demonstrated solid-oxide electrolysis** on Perseverance: **2CO₂ → 2CO + O₂**, producing
  pure oxygen directly from the atmosphere. Its demonstrated output and energy cost are §21 →
  `endeavour-mission-architecture-and-spacecraft-subsystems`.
- The **CO byproduct** can be used directly as a low-grade fuel, or processed via the **reverse
  water-gas shift (CO₂ + H₂ → CO + H₂O)** combined with electrolysis to produce methane by
  **Sabatier: CO₂ + 4H₂ → CH₄ + 2H₂O**.

**The full ISRU propellant chain for a Mars ascent vehicle:**

    mine water ice → electrolyze to H₂ and O₂ → Sabatier with atmospheric CO₂ → CH₄ + H₂O
        → split the water again → liquefy to LCH₄ and LOX

That is **methalox** — the same combination Starship uses, and a propellant whose Isp, bulk density
and common-bulkhead advantages are §10 → `endeavour-rocket-equation-nozzles-engines-and-propellants`
— produced **entirely from Martian resources**.

> **ENERGY, NOT CHEMISTRY, IS THE BINDING CONSTRAINT**
> Producing **~30 tonnes of O₂ and ~8 tonnes of CH₄** for a crewed ascent requires roughly **1–2 MWe
> continuously for 16–26 months**. None of the chemistry is exotic; the power plant is. This is why
> **fission surface power sits in the critical path of most Mars architectures**
> (§31 → `endeavour-mars-mission-design-and-settlement`) — the reaction is easy, the
> megawatt-months are not.

### Regolith for construction

Regolith is the most available construction material: **radiation shielding** (1–2 m bermed over
habitats), **thermal insulation** (low thermal conductivity), and **feedstock**. The techniques
investigated:

| Technique | How it works | What it needs |
|---|---|---|
| **Additive construction** | 3D printing regolith plus a binder, or sintering regolith | Concentrated solar or microwave energy, or an imported binder |
| **Compressed regolith blocks** | Natural cohesion of packed fines under pressure | Press energy only |
| **Sulfur concrete** | Molten sulfur as binder | Sulfur is available on Mars, and this requires **no water** |
| **Polymer-regolith composites** | Plastic matrix with regolith filler | Depends on producing plastics from atmospheric CO₂ |

**The structural challenge is that none of this is characterized.** Mars regolith in vacuum is not
well understood geotechnically, and any construction method must work **in 0.38 g, at 610 Pa external
pressure, and through temperatures that cycle to −60 °C nightly**. Treat published construction
concepts as concepts.

### Other resources

- **Nitrogen is scarce.** The atmosphere is only **2.8% N₂ at 610 Pa**, a partial pressure of about
  **17 Pa**. Nitrogen is essential for agriculture and fixing it from an atmosphere that dilute is
  energy-intensive. **This is one of the harder ISRU problems for self-sufficient settlement: the
  feedstock exists, but it is extremely dilute.** The same scarcity becomes the missing nitrogen
  cycle in any terraforming scenario (§36 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics`).
- **Argon** (2% of the atmosphere) is available as a buffer gas.
- **Metals** — iron, aluminium, titanium — are present in regolith but require high-temperature
  smelting: energy-intensive, but feasible with sufficient power.
- **No concentrated ore deposits have been identified.** Mining would start from bulk basaltic
  regolith, which has low ore grades. Every mass-production estimate for a Martian
  industrial base should be read against that.

---
