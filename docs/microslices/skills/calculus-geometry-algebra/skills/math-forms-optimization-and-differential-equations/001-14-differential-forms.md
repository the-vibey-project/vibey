---
id: skill-14-differential-forms-9e8062eada
purpose: 14 differential forms
source: src/vibey_tools/skills/plugins/calculus-geometry-algebra/skills/math-forms-optimization-and-differential-equations/SKILL.md
requires: []
links: ["skill-15-constrained-optimization-b8623736d5"]
---

## §14. Differential Forms

**⚠️ The unification, and it repays the effort.**
```
0-form   function f
1-form   ω = f dx + g dy + h dz         ⚠️ integrate over curves
2-form   ω = f dx∧dy + ...              integrate over surfaces
3-form   f dx∧dy∧dz                     integrate over volumes
```
**Wedge product `∧`** — ⚠️ **antisymmetric: `dx∧dy = −dy∧dx`, so `dx∧dx = 0`.** **The
antisymmetry is what encodes orientation and signed volume — the same fact as §3 → `math-linear-algebra-foundations`'s
determinant.**
**Exterior derivative `d`** — ⚠️ **`d² = 0` always**, which reproduces both identities in
§13 → `math-calculus-and-vector-calculus` at once.

**⚠️ Generalized Stokes theorem:**
```
∫_∂M ω = ∫_M dω
```
⚠️ **That single line contains the FTC, Green's, Stokes' and the divergence theorem.**
**"The integral of `dω` over a region equals the integral of `ω` over its boundary."**
**⚠️ And the notational suggestiveness is real: `d` and `∂` are adjoint, which is the
germ of de Rham cohomology — closed forms (`dω = 0`) modulo exact forms (`ω = dη`) measure
the topology of the space.** **That's how the punctured-plane counterexample in §13 → `math-calculus-and-vector-calculus`
becomes a theorem rather than a curiosity.**

---
