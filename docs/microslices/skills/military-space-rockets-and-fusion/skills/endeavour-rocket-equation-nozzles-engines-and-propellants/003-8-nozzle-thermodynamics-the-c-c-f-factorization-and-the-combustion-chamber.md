---
id: skill-8-nozzle-thermodynamics-the-c-c-f-factorization-and-the-combustion-chamber-eaf6cdcfc6
purpose: 8 nozzle thermodynamics the c c f factorization and the combustion chamber
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-rocket-equation-nozzles-engines-and-propellants/SKILL.md
requires: ["skill-7-the-rocket-equation-staging-and-thrust-859667a789"]
links: ["skill-9-turbomachinery-engine-cycles-and-cooling-ca34e541a4"]
---

## §8 Nozzle thermodynamics, the c*/C_F factorization, and the combustion chamber

Treat the chamber as a **stagnation reservoir** at p_c, T_c. For isentropic expansion of a
calorically perfect gas, the exit velocity is:

    v_e = √( (2γ/(γ−1)) · (R_u T_c / M_w) · [1 − (p_e/p_c)^((γ−1)/γ)] )

> **READ THAT EQUATION — IT DICTATES PROPELLANT CHOICE.** v_e is proportional to the square root of
> (T_c / M_w). **Molecular weight is as important as temperature.** This is why hydrogen wins despite
> burning cooler than kerolox: H₂/O₂ runs fuel-rich to leave free H₂ in the exhaust, dropping M_w to
> **~10–13 kg/kmol** against kerolox's **~22**. The optimum mixture ratio for Isp is therefore **not
> stoichiometric** — it is fuel-rich, trading flame temperature for lower molecular weight. LOX/LH₂
> stoichiometric is **O/F = 8**; engines run **5.5–6.0**.

### The clean factorization

    F = C_F · p_c · A*        c* = p_c · A* / ṁ        Isp · g_0 = c* · C_F

- **c\* (characteristic velocity)** measures **combustion quality only** — how well you converted
  chemical energy to hot, low-molecular-weight gas. Typical: **1,800 m/s (kerolox) to 2,350 m/s
  (hydrolox)**.
- **C_F (thrust coefficient)** measures **nozzle quality only** — how well you expanded it. Typical:
  **1.5–1.9**.

They are separately measurable, so **a hot-fire tells you whether your problem is the injector or the
nozzle**. A c\* efficiency of **96–99%** is the practical range; below that, your injector is not
mixing.

### Expansion ratio and flow separation

Optimum expansion is **p_e = p_a**. Sea-level first-stage nozzles have area ratios of **10–25**,
constrained by separation. Vacuum upper stages reach **40–200+**.

**Flow separation is the hard sea-level limit.** If over-expanded too aggressively, the boundary
layer separates *asymmetrically*, generating side loads that can destroy the nozzle. The
**Summerfield criterion** puts separation near **p_e ≈ 0.4·p_a**. This is why first-stage nozzles
look "stubby" — they are deliberately **under-expanded at sea level to stay attached**.

### The combustion chamber

The chamber's job: **complete combustion, uniformly, before the throat, without destroying itself.**

**Characteristic length** L\* = V_c / A\* — chamber volume per throat area, a proxy for residence
time. Typical: **0.8–1.3 m for kerolox, 0.6–0.9 m for hydrolox** (hydrogen reacts faster). Residence
time is approximately **2–4 ms** — the entire budget for atomization, vaporization, mixing and
reaction.

**Injectors are the component that determines whether an engine works.**

| Injector family | Mechanism and where it is used |
|---|---|
| Impinging (like-on-like, unlike doublet/triplet) | Atomizes by jet collision |
| Coaxial swirl | The Russian preference; excellent mixing |
| Shear coax | Standard for hydrogen (SSME) |
| Pintle | A single central element; inherently stable, deeply throttleable — Apollo LM descent engine and Merlin both use this design |

**The injector sets stability**: element spacing, momentum ratio and impingement distance determine
whether the chamber couples with acoustic modes. What happens when it does — combustion instability,
and how long it took to tame on the F-1 — is §16 →
`endeavour-orbits-ascent-structures-and-reentry`.
