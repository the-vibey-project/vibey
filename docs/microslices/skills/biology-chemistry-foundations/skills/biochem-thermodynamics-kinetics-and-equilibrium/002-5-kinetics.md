---
id: skill-5-kinetics-b5ed0c30d7
purpose: 5 kinetics
source: src/vibey_tools/skills/plugins/biology-chemistry-foundations/skills/biochem-thermodynamics-kinetics-and-equilibrium/SKILL.md
requires: ["skill-4-thermodynamics-683f09e075"]
links: ["skill-6-equilibrium-and-acid-base-6b427f6150"]
---

## §5. Kinetics

**Rate laws** are experimental, not stoichiometric: `rate = k[A]^m[B]^n`.
⚠️ **Order is determined by the mechanism, specifically the rate-determining step — you
cannot read it off the balanced equation.**

```
Zero order:   [A] = [A]₀ − kt         t½ = [A]₀/2k
First order:  ln[A] = ln[A]₀ − kt     ⚠️ t½ = ln2/k — INDEPENDENT of concentration
Second order: 1/[A] = 1/[A]₀ + kt     t½ = 1/(k[A]₀)
```
**⚠️ The concentration-independent half-life of first-order kinetics is why radioactive
decay and most drug elimination have a fixed t½** (see a biomedical-engineering
reference §8).

**Arrhenius**: `k = A·e^(−Ea/RT)`, or `ln k = ln A − Ea/RT`.
⚠️ **The exponential dependence is why a 10 °C rise roughly doubles many reaction rates**,
and why small Ea reductions produce enormous rate increases.

**Transition state theory**: reaction proceeds through a maximum-energy configuration.
`ΔG‡` is the activation barrier, and `k ∝ e^(−ΔG‡/RT)`.

> **⚠️ GOTCHA — catalysts and equilibrium.** A catalyst **lowers ΔG‡, accelerating forward
> and reverse reactions equally.** ⚠️ **It cannot change ΔG, K, or the equilibrium
> position.** Any claim that a catalyst "drives" a reaction to completion is wrong — what
> drives it is removing product (§4.1, Le Chatelier §6).

---
