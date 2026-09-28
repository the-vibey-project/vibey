---
id: skill-3-combustion-chamber-cb88c806e3
purpose: 3 combustion chamber
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-equation-nozzles-and-combustion/SKILL.md
requires: ["skill-2-nozzle-thermodynamics-2d5121858c"]
links: []
---

## §3. Combustion Chamber

**[DURABLE] The chamber's job: complete combustion, uniformly, before the throat, without
destroying itself.**

**Characteristic length** `L* = V_c / A*` — chamber volume per throat area, a proxy for
residence time. **Typical: 0.8–1.3 m for kerolox, 0.6–0.9 m for hydrolox** (hydrogen
reacts faster). ⚠️ **Too short and you get incomplete combustion (low `c*`); too long and
you carry dead mass and extra cooled surface.**

**Residence time** `t_stay = L* / (c* · something)` ≈ **2–4 ms** typically. That is your
entire budget for atomization, vaporization, mixing, and reaction.

**Injectors** — the component that determines whether an engine works:
- **Impinging (like-on-like, unlike doublet/triplet)** — atomization by jet collision.
- **Coaxial swirl** — Russian preference; excellent mixing.
- **Shear coax** — standard for hydrogen (SSME).
- **Pintle** — ⚠️ **single central element, inherently stable, deeply throttleable; the
  Apollo LM descent engine and Merlin both use it.**

**⚠️ The injector sets stability.** Element spacing, momentum ratio, and impingement
distance determine whether the chamber couples with acoustic modes (§13.1 → `rocket-aerodynamics-structures-guidance-and-reentry`).

**Mixture ratio effects, beyond Isp**: running fuel-rich lowers `T_c`, which **protects the
wall** and lowers cooling load, and reduces oxidizing attack on the metal. ⚠️ **Most
engines run somewhat fuel-rich for reasons that are as much thermal as performance.**
