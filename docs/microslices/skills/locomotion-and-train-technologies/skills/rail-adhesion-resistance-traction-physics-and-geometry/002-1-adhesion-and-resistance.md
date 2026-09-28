---
id: skill-1-adhesion-and-resistance-c0a0e6d6f5
purpose: 1 adhesion and resistance
source: src/vibey_tools/skills/plugins/locomotion-and-train-technologies/skills/rail-adhesion-resistance-traction-physics-and-geometry/SKILL.md
requires: ["skill-0-routing-ee1b6cc1dc"]
links: ["skill-2-traction-and-braking-6cc50082ed"]
---

## §1. ⚠️ Adhesion and Resistance

```
⚠️ ADHESION COEFFICIENT (steel on steel)
   ⚠️ Dry, clean rail:     ~0.20–0.35
   ⚠️ Wet rail:            ~0.15–0.20
   ⚠️ Contaminated (leaves, oil, frost): ⚠️ can fall below 0.05
   Compare rubber on dry road: ~0.7–0.9
⚠️ ROLLING RESISTANCE  roughly 1/10th that of road vehicles.
   ⚠️ THE reason rail exists
⚠️ CONTACT PATCH  about the size of a small coin, carrying tonnes.
   ⚠️ Contact stresses approach the yield strength of steel — which is
   why rail and wheels wear, spall and fatigue (§22)
```
**⚠️ The Davis equation** describes total train resistance:
```
⚠️ R = A + Bv + Cv²
   A  ⚠️ rolling and bearing resistance (roughly constant)
   Bv ⚠️ flange and track interaction, linear in speed
   Cv² ⚠️ AERODYNAMIC — dominates at high speed (§23)
```
⚠️ **The cubic power consequence: power required rises with the CUBE of speed in the
aerodynamic regime**, **which is why high-speed rail is far more about aerodynamics and
installed power than about track.**
> **⚠️ GOTCHA — the low friction cuts both ways and this is the master fact of railway
> operations.** ⚠️ **A freight train at 100 km/h may need well over a kilometre to stop —
> far beyond the driver's sighting distance.** **⚠️ THIS is why railways need signalling
> (§14 → `rail-signalling-interlocking-train-protection-and-safety`): the driver physically cannot see far enough ahead to stop, so the system must
> tell them what lies beyond.** **Road vehicles can drive on sight; trains fundamentally
> cannot.**

**⚠️ Sanding, and its limits**: ⚠️ **sand improves adhesion for traction and braking but is
finite, contaminates ballast, and can insulate track circuits** (§14 → `rail-signalling-interlocking-train-protection-and-safety`) — **a real
interaction failure where a train becomes invisible to the signalling.**
**⚠️ Low-adhesion season is a genuine engineering problem, not an excuse**: ⚠️ **crushed
leaf material forms a hard, slick pectin layer bonded to the railhead** — **it is not
"leaves on the line" in the trivial sense, and railheads are cleaned with water jets and
treated with friction modifiers.**

---
