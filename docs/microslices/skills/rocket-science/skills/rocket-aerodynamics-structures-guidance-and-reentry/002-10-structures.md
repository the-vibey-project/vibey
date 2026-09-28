---
id: skill-10-structures-df4fb486f4
purpose: 10 structures
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-aerodynamics-structures-guidance-and-reentry/SKILL.md
requires: ["skill-9-aerodynamics-and-loads-02ebf59191"]
links: ["skill-11-guidance-and-control-dec9815c71"]
---

## §10. Structures

**[DURABLE] The governing failure mode is buckling, not yielding.**

**Euler column buckling**: `P_cr = π²EI/(KL)²`.
**Thin-walled cylinder axial buckling** — the practically important case:
```
σ_cr = γ · E · t/(R·√(3(1−ν²)))
```
⚠️ **γ is a knockdown factor of 0.15–0.65** because real cylinders are exquisitely sensitive
to imperfections. **Classical theory over-predicts buckling strength by up to 5×** — this
is one of the few places in engineering where linear theory is dramatically wrong, and
NASA SP-8007 empirical knockdowns are still the working design basis.

**Pressure stabilization**: internal pressure adds a tensile stress that raises the
effective buckling threshold. ⚠️ **Atlas's balloon tanks took this to the limit — the
vehicle would collapse under its own weight if depressurized.** Structurally brilliant,
operationally demanding.

**Hoop and longitudinal stress** in a thin cylinder: `σ_h = pR/t`, `σ_l = pR/(2t)`.
⚠️ **Hoop is twice longitudinal** — which is why cylindrical tanks fail along a longitudinal
seam and why weld orientation matters.

**Stiffening**: **isogrid** (equilateral triangular pockets machined from plate — high
efficiency, expensive), **orthogrid**, **skin-stringer**, **sandwich**.

**Load cases that size the structure:**
```
Max-Q            bending + axial, mid-atmosphere
Max-g            late in burn — ⚠️ vehicle nearly empty, high acceleration
Liftoff release  transient twang
Landing (if reusable)  ⚠️ an entirely additional load path
```

**Common bulkhead** between tanks saves length and mass but ⚠️ **must handle a large ΔT
across it** (LOX at 90 K, RP-1 at ambient) and any pressure reversal.

**⚠️ POGO**: a closed-loop instability coupling structural longitudinal modes → feedline
pressure oscillation → thrust oscillation → structure. **Nearly destroyed Apollo 13's
S-II.** Suppressed with **gas-filled accumulators in the feedlines** that detune the
hydraulic resonance.

---
