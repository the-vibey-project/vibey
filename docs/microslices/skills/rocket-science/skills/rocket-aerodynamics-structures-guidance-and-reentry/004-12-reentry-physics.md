---
id: skill-12-reentry-physics-cc017e9e2d
purpose: 12 reentry physics
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-aerodynamics-structures-guidance-and-reentry/SKILL.md
requires: ["skill-11-guidance-and-control-dec9815c71"]
links: ["skill-13-instabilities-and-failure-physics-33fd2fd295"]
---

## §12. Reentry Physics

**[DURABLE] The problem: dispose of ~30 MJ/kg (LEO) or ~60 MJ/kg (lunar return) without
depositing it in the vehicle.**

**Allen–Eggers blunt body theory (1958)** — the foundational insight:

> **⚠️ GOTCHA — reentry heating is overwhelmingly *compression*, not friction.**
> The bow shock compresses and heats the air; the vehicle is heated by that gas.
> **A blunt body pushes a detached bow shock ahead of itself, dumping most of the energy
> into the air rather than into the vehicle.** A slender, "aerodynamic" shape produces an
> attached shock and concentrates heating on the surface — **it would be destroyed.**
> This is why every reentry vehicle from Mercury to Orion to Dragon is bluff.

**Deceleration** (Allen–Eggers, exponential atmosphere `ρ = ρ₀e^(−h/H)`, H ≈ 7.2 km):
```
a_max = v_e² · sin γ / (2·e·H)          [independent of ballistic coefficient!]
```
⚠️ **Peak deceleration depends only on entry velocity and flight path angle** — not on
mass or drag area. β shifts *where* it happens, not how severe it is. **Apollo: ~6.5 g;
ballistic Soyuz abort: ~9 g; Galileo probe at Jupiter: ~230 g.**

**Stagnation-point heating — the Sutton–Graves relation:**
```
q_s = k · √(ρ/R_n) · v³
```
with k ≈ 1.7415×10⁻⁴ (SI) for air.

**⚠️ Two consequences that drive all TPS design:**
1. **`q ∝ v³`.** Lunar return at 11 km/s versus LEO at 7.8 km/s is `(11/7.8)³` ≈ **2.8×
   the heat flux.** Mars return is worse still.
2. **`q ∝ 1/√R_n`.** ⚠️ **A blunter nose (larger radius) *reduces* peak heating.** Another
   argument for bluff bodies, and why sharp leading edges (Shuttle wing, X-37) need the
   most exotic materials.

**Total heat load** `Q = ∫q dt` scales differently from peak flux — ⚠️ **a shallow entry
lowers peak flux but *raises* total load**, which is why the design point is a trade, not a
minimization. **Peak flux sizes the material; total load sizes the thickness.**

**Radiative heating** becomes significant above ~10 km/s, scaling as roughly `v^8` — ⚠️ **at
Jupiter or high-speed sample-return, radiation dominates convection entirely.**

**The entry corridor**: too steep → exceed heating and g-limits; too shallow → skip out.
⚠️ **For Apollo lunar return the corridor was about ±1° in flight path angle** — a
genuinely tight target from 400,000 km away.

**Lifting entry** with L/D 0.3 (Apollo) to ~1 (Shuttle) widens the corridor, permits
cross-range, and allows load management by **bank-angle modulation** — rolling the lift
vector to control descent rate, which is how Apollo and Orion actually fly entry.

**⚠️ Mars EDL is the hardest routine case**: the atmosphere is thick enough to require a
heat shield but too thin to slow you to parachute-safe speeds. ⚠️ **Supersonic parachute
deployment at Mach 1.5–2.2** followed by propulsive terminal descent, and this chain is why
landed mass has historically been capped around 1 tonne.

---
