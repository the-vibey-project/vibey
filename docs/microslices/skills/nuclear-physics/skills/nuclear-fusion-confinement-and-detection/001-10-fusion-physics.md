---
id: skill-10-fusion-physics-9faa027cb1
purpose: 10 fusion physics
source: src/vibey_tools/skills/plugins/nuclear-physics/skills/nuclear-fusion-confinement-and-detection/SKILL.md
requires: []
links: ["skill-11-magnetic-confinement-8391164954"]
---

## §10. Fusion Physics

**⚠️ The Coulomb barrier is the whole problem.** Nuclei must approach to ~1 fm against
electrostatic repulsion. **Quantum tunnelling helps, but you still need ~10–15 keV
(~100–150 million K).**

**The candidate reactions:**
```
D + T → ⁴He (3.5 MeV) + n (14.1 MeV)     ⚠️ HIGHEST cross section at LOWEST temperature.
                                          The only near-term option — and 80% of the
                                          energy is in a neutron (§13)
D + D → two branches                      ⚠️ no tritium needed, much harder
D + ³He → ⁴He + p                         ⚠️ aneutronic-ish, but ³He is essentially
                                          unavailable and it needs far higher temperature
p + ¹¹B → 3 ⁴He                           ⚠️ truly aneutronic; enormous temperature
                                          and bremsstrahlung losses. Very hard
```
**⚠️ Why D-T despite the neutron problem**: its cross section peaks about 100× higher and
at roughly a quarter the temperature of the alternatives. **Everything else is a much
harder physics problem in exchange for an easier engineering one.**

**⚠️ Lawson criterion / triple product** — the condition for net energy:
```
n · T · τ_E  ≳ 3×10²¹ keV·s·m⁻³   (D-T ignition)
```
**Density × temperature × energy confinement time.** ⚠️ **The two confinement approaches
attack different factors: magnetic confinement uses low density and long `τ_E` (seconds);
inertial uses enormous density and vanishing `τ_E` (nanoseconds). Both must reach the same
product.**

**⚠️ `Q` definitions are a recurring source of confusion and inflated claims:**
- **`Q_scientific`** — fusion energy out / **energy delivered to the plasma or target.**
- **`Q_engineering`** — ⚠️ **electricity out / total electricity in, including the whole
  facility.** **This is the one that matters for a power plant.**
- **⚠️ Ignition** — the alpha particles alone sustain the burn.
**⚠️ NIF's reported gains are scientific `Q` against laser energy delivered to the target,
not against the wall-plug energy drawn by the laser system, which is far larger** (§16.1 → `nuclear-reference`).

---
