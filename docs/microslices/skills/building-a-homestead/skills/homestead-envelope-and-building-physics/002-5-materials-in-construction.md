---
id: skill-5-materials-in-construction-7b804cad89
purpose: 5 materials in construction
source: src/vibey_tools/skills/plugins/building-a-homestead/skills/homestead-envelope-and-building-physics/SKILL.md
requires: ["skill-4-envelope-and-building-physics-where-buildings-actually-fail-9c2c5ee806"]
links: ["skill-where-this-connects-f19fb024fc"]
---

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
