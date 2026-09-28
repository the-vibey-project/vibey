---
id: skill-4-thermodynamics-683f09e075
purpose: 4 thermodynamics
source: src/vibey_tools/skills/plugins/biology-chemistry-foundations/skills/biochem-thermodynamics-kinetics-and-equilibrium/SKILL.md
requires: []
links: ["skill-5-kinetics-b5ed0c30d7"]
---

## §4. Thermodynamics

### 4.1 The laws and the central equation
```
0th  thermal equilibrium is transitive → temperature exists
1st  ΔU = q − w                        energy conserved
2nd  ΔS_universe > 0 for any spontaneous process
3rd  S → 0 as T → 0 for a perfect crystal
```
**Enthalpy** `H = U + PV`, so `ΔH = q_p` at constant pressure.
**Gibbs free energy** — ⚠️ **the master equation:**
```
ΔG = ΔH − TΔS
ΔG < 0  spontaneous (exergonic)     ΔG > 0  non-spontaneous     ΔG = 0  equilibrium
```

> **⚠️ GOTCHA — the four things ΔG does not tell you.**
> 1. **Nothing about rate.** ⚠️ **Diamond → graphite has ΔG < 0 and takes geological
>    time.** Spontaneous ≠ fast (§5).
> 2. **"Spontaneous" is a technical term meaning thermodynamically favourable**, not
>    "happens by itself quickly."
> 3. **⚠️ ΔG° (standard state) ≠ ΔG (actual).** `ΔG = ΔG° + RT ln Q`. **Cells operate far
>    from standard state, and reactions with unfavourable ΔG° run forward routinely
>    because Q is held low by consuming the product** (§12 → `biochem-biomolecules-cells-and-evolution`).
> 4. **Exothermic ≠ spontaneous.** ⚠️ **Ice melting above 0 °C is endothermic and
>    spontaneous** — TΔS wins.

**Entropy is not "disorder"** — ⚠️ **it's the number of accessible microstates**,
`S = k_B ln W`. **The disorder metaphor fails badly** for the hydrophobic effect (§3.2 → `biochem-atoms-bonding-and-intermolecular-forces`),
where aggregation *increases* total entropy.

**Coupling**: an unfavourable reaction runs if coupled to a more favourable one sharing an
intermediate. ⚠️ **This is the entire logic of ATP in metabolism** (§12 → `biochem-biomolecules-cells-and-evolution`).

**Hess's law**: ΔH is path-independent. **`ΔG° = −RT ln K`** connects thermodynamics to
equilibrium (§6), and **`ΔG° = −nFE°`** connects it to redox (§7).

---
