---
id: skill-35-method-4d9e2aa8bf
purpose: 35 method
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-reference/SKILL.md
requires: ["skill-34-quick-reference-512939f591"]
links: []
---

## §35. Method

**§1–§28 → `thermo-laws-entropy-property-relations-and-phase-behaviour`, `thermo-cycles-exergy-combustion-and-psychrometrics`, `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`, `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`, `thermo-heat-transfer-conduction-convection-radiation-and-exchangers` is settled science and engineering** — **the laws, property relations, cycles,
Navier-Stokes, boundary layer theory, the dimensionless groups, and the three modes of
heat transfer** — sourced from §33. ⚠️ **This is the most stable content in this series;
Carnot published in 1824 and none of it needed verification.**

**Two searches were run in August 2026**, on **CFD and turbulence modelling practice** and
**high-density thermal management** — ⚠️ **deliberately targeting PRACTICE rather than
theory, because the theory doesn't move and the practice genuinely has.**

**Confidence.** **High** throughout §1–§28 → `thermo-laws-entropy-property-relations-and-phase-behaviour`, `thermo-cycles-exergy-combustion-and-psychrometrics`, `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes`, `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`, `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`. ⚠️ **The sections I'd most want read are §4 → `thermo-laws-entropy-property-relations-and-phase-behaviour`,
§10 → `thermo-cycles-exergy-combustion-and-psychrometrics`, §16 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes` and §19 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery`.** **§10 → `thermo-cycles-exergy-combustion-and-psychrometrics` (exergy) because it is under-taught and it changes where you look
for losses; §16 → `thermo-fluid-statics-control-volume-bernoulli-and-navier-stokes` because the equal-transit-time lift myth is still in circulation and in
some textbooks; §19 → `thermo-dimensional-analysis-flows-turbulence-and-turbomachinery` because dimensional analysis tells you which physics dominates before
you compute anything, which is most of engineering judgement.**

**High** in §29.1's characterization. ⚠️ **The claim I'd emphasise is the sceptical one:
RANS remains dominant, ML turbulence models are explicitly described in 2026 sources as
"still largely in the research phase" with a 5–10 year horizon to mainstream tools, and
the obstacles include documented non-uniqueness in ML mappings and doubt that a universal
local model exists.** ⚠️ **The "1000× faster" framing in vendor and aggregator material
almost always refers to surrogates rather than solvers, and I've flagged that distinction
explicitly because it's the difference between a design-exploration tool and a
verification tool.** **The GPU speedup figures (10–100×) come from vendor and consultancy
sources and I've reported them as reported.**

**High** in §29.2's physics and threshold logic, moderate in the specific market numbers.
⚠️ **The 3,000–4,000× volumetric heat capacity ratio, the ~1,000 W+ chip TDPs, the
GB200 NVL72 at ~120 kW, and the 45°C Vera Rubin coolant specification are consistent
across sources and traceable to vendor specifications.** ⚠️ **The adoption percentages vary
substantially between sources (22% vs 37% for 2026) and I've presented them as
directional rather than picking one.** **⚠️ Sourcing caution: a significant share of the
liquid-cooling material comes from vendors, buying guides and consultancies with obvious
interests** — **I anchored the threshold logic on the ASHRAE TC 9.9 recommendation and on
the physics (which is checkable from §26 → `thermo-heat-transfer-conduction-convection-radiation-and-exchangers`'s h-magnitude table) rather than on any vendor's
recommended product.**

⚠️ **One judgement stated plainly**: **the warm-water cooling development in §29.2 is
presented as an exergy story (§10 → `thermo-cycles-exergy-combustion-and-psychrometrics`) rather than merely a product feature, and that framing
is mine.** **I think it's the right reading — eliminating a refrigeration cycle by raising
the acceptable coolant temperature is precisely "don't create a temperature gradient you
then have to spend work climbing" — but the connection is my analysis, not a citation.**
