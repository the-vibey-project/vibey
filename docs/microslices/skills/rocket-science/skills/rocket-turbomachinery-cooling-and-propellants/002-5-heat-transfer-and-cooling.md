---
id: skill-5-heat-transfer-and-cooling-8143ab0d31
purpose: 5 heat transfer and cooling
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-turbomachinery-cooling-and-propellants/SKILL.md
requires: ["skill-4-turbomachinery-and-cycles-2456b436fc"]
links: ["skill-6-propellants-cd15890d4a"]
---

## §5. Heat Transfer and Cooling

**[DURABLE] Chamber wall heat flux is the highest sustained flux in routine engineering.**

**Typical: 10–160 MW/m² at the throat.** ⚠️ **For comparison, a domestic hob is ~0.05 MW/m².**
The throat is the peak because that's where velocity is highest and the boundary layer
thinnest.

**Gas-side heat transfer** via the **Bartz correlation**:
```
h_g = (0.026/D*^0.2) · (μ^0.2 c_p / Pr^0.6) · (p_c/c*)^0.8 · (D*/R_c)^0.1 · (A*/A)^0.9 · σ
```
where σ corrects for property variation across the boundary layer. ⚠️ **Note
`h_g ∝ p_c^0.8`** — **raising chamber pressure raises heat flux nearly proportionally**,
which is the real constraint on high-p_c engines, not structural strength.

**Cooling approaches:**
- **Regenerative** — propellant through milled channels or brazed tubes before injection.
  ⚠️ **The heat isn't lost — it's returned to the chamber**, so the penalty is pressure
  drop (pump work), not energy.
- **Film / curtain cooling** — a fuel-rich boundary layer at the wall. ⚠️ **Costs Isp
  directly** (that propellant burns poorly), typically 1–3%, but often unavoidable at the
  throat.
- **Ablative** — sacrificial charring liner. Simple, single-use-ish, mass-heavy.
- **Radiative** — for nozzle extensions where `q` is low: `q = εσT⁴`, needing niobium or
  carbon-carbon at 1,300–1,800 K.
- **Transpiration** — porous wall, ultimate performance, rarely used.

**⚠️ The channel design trade**: narrower channels raise coolant velocity and `h_c`,
improving cooling, but raise pressure drop as roughly `Δp ∝ v²`. **And the coolant-side
limit is nucleate-to-film boiling transition** — cross it and heat transfer *collapses* and
the wall burns through in milliseconds.

---
