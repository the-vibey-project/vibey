---
id: skill-2-nozzle-thermodynamics-2d5121858c
purpose: 2 nozzle thermodynamics
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-equation-nozzles-and-combustion/SKILL.md
requires: ["skill-1-the-rocket-equation-f7a680a92e"]
links: ["skill-3-combustion-chamber-cb88c806e3"]
---

## §2. Nozzle Thermodynamics

### 2.1 Isentropic flow

**[DURABLE]** Treat the chamber as a stagnation reservoir at `p_c`, `T_c`. For isentropic
expansion of a calorically perfect gas:

```
T/T_c = (p/p_c)^((γ−1)/γ)
A/A* = (1/M)·[ (2/(γ+1))·(1 + (γ−1)/2 · M²) ]^((γ+1)/(2(γ−1)))
```

**Choking at the throat** (M = 1) sets the mass flow:
```
ṁ = (A* · p_c / √T_c) · √(γ/R) · [2/(γ+1)]^((γ+1)/(2(γ−1)))
```
⚠️ **Mass flow is set entirely by throat area and chamber conditions.** The divergent
section cannot change `ṁ` — it only converts the flow's enthalpy into velocity.

**Exit velocity** from energy conservation:
```
v_e = √( (2γ/(γ−1)) · (R_u T_c / M_w) · [1 − (p_e/p_c)^((γ−1)/γ)] )
```

> **⚠️ GOTCHA — read that equation, because it dictates propellant choice.**
> `v_e ∝ √(T_c / M_w)`. **Molecular weight is as important as temperature.**
> This is why **hydrogen wins despite burning cooler than kerolox**: H₂/O₂ runs fuel-rich
> to leave free H₂ in the exhaust, dropping `M_w` to ~10–13 kg/kmol against kerolox's ~22.
> ⚠️ **The optimum mixture ratio for Isp is therefore *not* stoichiometric — it's
> fuel-rich**, trading flame temperature for lower molecular weight. LOX/LH₂
> stoichiometric is O/F = 8; engines run 5.5–6.0.

### 2.2 The clean factorization

```
F = C_F · p_c · A*                    c* = p_c · A* / ṁ
Isp · g₀ = c* · C_F
```
**[DURABLE] This factorization is the most useful thing in engine analysis:**
- **`c*` (characteristic velocity)** measures **combustion quality only** — how well you
  converted chemical energy to hot, low-molecular-weight gas. Depends on propellants,
  mixture ratio, and combustion efficiency. **Typical: 1,800 m/s (kerolox) to 2,350 m/s
  (hydrolox).**
- **`C_F` (thrust coefficient)** measures **nozzle quality only** — how well you expanded
  it. Depends on `γ`, `p_c/p_e`, and area ratio. **Typical: 1.5–1.9.**

⚠️ **They're separately measurable**, so a hot-fire tells you whether your problem is the
injector or the nozzle. `c*` efficiency of 96–99% is the practical range; below that, your
injector isn't mixing.

```
C_F = √( (2γ²/(γ−1)) · (2/(γ+1))^((γ+1)/(γ−1)) · [1 − (p_e/p_c)^((γ−1)/γ)] )
      + (p_e − p_a)/p_c · (A_e/A*)
```

### 2.3 Expansion ratio and separation

**Optimum expansion is `p_e = p_a`.** Area ratio `ε_n = A_e/A*`:

| Application | ε_n | Note |
|---|---|---|
| Sea-level first stage | 10–25 | Constrained by separation |
| Vacuum upper stage | 40–200+ | RL10B-2 reaches 280 |

**⚠️ Flow separation is the hard sea-level limit.** If over-expanded too aggressively, the
boundary layer separates from the wall asymmetrically, generating **side loads that can
destroy the nozzle and gimbal**. **The Summerfield criterion** puts separation near
`p_e ≈ 0.4·p_a` as a rough engineering bound. **This is why first-stage nozzles look
"stubby"** — they're deliberately under-expanded at sea level to stay attached, giving up
vacuum performance.

**Altitude-compensating concepts** — **aerospike, dual-bell, expansion-deflection** —
solve this in principle. ⚠️ **None has flown operationally**; aerospikes suffer from base
heating, cooling difficulty, and mass, and the theoretical gain (~5–8% mission-averaged
Isp) has never justified the complexity (§16.3 → `rocket-reference`).

**Bell contour**: a **Rao thrust-optimized parabolic** contour reaches ~99.5% of ideal
divergence efficiency at ~80% the length of a 15° cone. **Divergence loss** for a conical
nozzle is `λ = (1 + cos α)/2` — a 15° cone loses 1.7%.

---
