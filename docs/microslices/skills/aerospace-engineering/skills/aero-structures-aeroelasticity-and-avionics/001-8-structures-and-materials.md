---
id: skill-8-structures-and-materials-771f1c25fe
purpose: 8 structures and materials
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-structures-aeroelasticity-and-avionics/SKILL.md
requires: []
links: ["skill-9-aeroelasticity-2131fc5f83"]
---

## §8. Structures and Materials

**⚠️ Aerospace structures are the discipline of removing material safely.**
**Semi-monocoque** — skin carries shear, stringers carry bending, frames maintain shape.
**Wing box** as primary structure; spars, ribs.

**⚠️ Loads**: limit load (max expected in service), **ultimate = 1.5 × limit** —
⚠️ **a factor of safety of 1.5, against 3–5 in civil engineering.** **The structure must
not fail at ultimate, but permanent deformation is allowed above limit.**

**⚠️ Fatigue is the dominant structural concern in transport aircraft, not static
strength.**
> **⚠️ GOTCHA — the Comet accidents (1954) established this the hard way.** ⚠️ **Fatigue
> cracks initiated at stress concentrations around cutouts and propagated to catastrophic
> failure after a modest number of pressurization cycles.** **The consequences are
> permanent: rounded windows, damage-tolerant design, mandatory inspection intervals, and
> fail-safe multiple load paths.**
- **⚠️ Safe-life vs damage-tolerant**: retire at a set life, versus assume cracks exist and
  ensure they're detected before reaching critical length. **Damage tolerance is the
  modern default for transports.**
- **⚠️ Aloha Airlines 243 (1988)** — multi-site fatigue damage in a high-cycle,
  salt-exposed fuselage, **and the aircraft flew on because fail-safe design worked partly
  as intended.**

**Materials**: **aluminium alloys** (2024, 7075 — ⚠️ **cheap, well-understood, inspectable**),
**titanium** (⚠️ **strength at temperature, and expensive to machine**), **steel** for
landing gear, **composites** (⚠️ **CFRP: excellent specific strength and fatigue behaviour,
tailorable directionally — and prone to barely-visible impact damage and delamination,
which makes inspection genuinely harder than for metal**), superalloys (§7 → `aero-performance-stability-and-propulsion`).

---
