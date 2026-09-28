---
id: skill-7-orbital-mechanics-3109771761
purpose: 7 orbital mechanics
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-orbital-mechanics-and-ascent/SKILL.md
requires: []
links: ["skill-8-ascent-trajectory-e0899e4ffb"]
---

## §7. Orbital Mechanics

### 7.1 The two-body problem

**[DURABLE]** From Newton, the relative motion of two point masses:
```
r̈ = −μ · r̂ / r²,        μ = G(M+m) ≈ GM
```
Solutions are conic sections. The **orbit equation**:
```
r = h²/μ · 1/(1 + e·cos θ)
```
with specific angular momentum `h = r × v` and eccentricity vector
`e = (v×h)/μ − r̂`.

**Specific orbital energy**: `ε = v²/2 − μ/r = −μ/(2a)`
⚠️ **Energy depends only on semi-major axis.** Two wildly different-looking orbits with the
same `a` have the same energy and the same period.

**Rearranged, this gives the vis-viva equation — the single most useful formula in
mission design:**
```
v² = μ · (2/r − 1/a)
```
**Circular**: `v = √(μ/r)`. **Escape**: `v = √(2μ/r) = √2 · v_circ`.
⚠️ **Escape velocity is only 41% more than circular velocity** — a surprisingly small
margin, and the reason interplanetary departure is cheaper than intuition suggests.

**Period**: `T = 2π√(a³/μ)` (Kepler's third).

**Kepler's equation** for position in time: `M = E − e·sin E`, with `M = n(t − t_p)`.
⚠️ **Transcendental — no closed-form solution for E.** Newton-Raphson converges in a few
iterations; this is the standard numerical kernel in every propagator.

### 7.2 Manoeuvres

**Hohmann transfer** (two burns, minimum energy for coplanar circular-to-circular):
```
Δv₁ = √(μ/r₁) · [√(2r₂/(r₁+r₂)) − 1]
Δv₂ = √(μ/r₂) · [1 − √(2r₁/(r₁+r₂))]
```
**Worked — LEO (6,678 km) to GEO (42,164 km), μ_E = 398,600 km³/s²:**
```
v₁ = √(398600/6678) = 7.726 km/s
a_t = (6678+42164)/2 = 24,421 km
v_p,t = √(398600·(2/6678 − 1/24421)) = 10.239 km/s → Δv₁ = 2.513 km/s
v_a,t = √(398600·(2/42164 − 1/24421)) = 1.622 km/s
v₂ = √(398600/42164) = 3.075 km/s        → Δv₂ = 1.453 km/s
Total = 3.966 km/s   (⚠️ plus ~1.8 km/s if changing 28.5° inclination at GEO)
```

**⚠️ Bi-elliptic beats Hohmann when `r₂/r₁ > 11.94`** — a three-burn transfer via a very
high apoapsis. Counterintuitive, and genuinely used for some high-energy transfers.

**Plane change**: `Δv = 2v·sin(Δi/2)`.
⚠️ **At LEO velocity, a 28.5° plane change costs 3.8 km/s — more than reaching GEO.**
This is why you **launch into your target inclination**, why launch-site latitude is a
hard mission constraint, and why plane changes are done at apoapsis where `v` is smallest.

**Combined manoeuvre**: doing the plane change during the GEO circularization burn uses
vector addition rather than sequential burns:
`Δv = √(v₁² + v₂² − 2v₁v₂·cos Δi)` — ⚠️ **saves several hundred m/s and is standard
practice.**

**The Oberth effect**: for a burn `Δv` at speed `v`, energy change is
`Δε = v·Δv + Δv²/2`. ⚠️ **The `v·Δv` term means the same propellant buys more energy when
you're moving faster** — hence departure burns at periapsis, and the value of dropping deep
into a gravity well before burning.

### 7.3 Patched conics and interplanetary

**[DURABLE]** Divide the trajectory into segments where a single body dominates. The
**sphere of influence** radius:
```
r_SOI = a_planet · (m_planet/M_sun)^(2/5)
```
Earth: ~924,000 km. ⚠️ **A useful fiction, not physics — the transition is smooth in
reality, but the approximation is good to a fraction of a percent for preliminary design.**

**Hyperbolic excess velocity** `v_∞` is the speed relative to the planet at SOI exit, with
`C₃ = v_∞²` the **characteristic energy** — the number launch vehicle performance charts
are plotted against. Departure burn from a parking orbit:
```
v_p = √(v_∞² + 2μ/r_p)
```
⚠️ **Note the Oberth benefit is embedded here**: the `2μ/r_p` term means you need far less
than `v_∞` added to your orbital speed.

**Gravity assists**: in the planet's frame, `|v_∞|` is unchanged — only its **direction**
rotates by `2·arcsin(1/e)`. In the heliocentric frame, that rotation changes the heliocentric
speed. ⚠️ **Free Δv, paid for in launch-window rigidity and flight time**, and the reason
outer-planet missions have such constrained launch periods.

**Lambert's problem** — given two position vectors and a transfer time, find the orbit.
⚠️ **The computational core of all trajectory design**; solved by Gauss, Battin, or
universal-variable formulations, and what a porkchop plot is a visualization of.

### 7.4 Perturbations

Real orbits aren't Keplerian. The dominant terms, in order:

**J₂ (Earth oblateness, J₂ = 1.0826×10⁻³)** — by far the largest. Causes secular drift:
```
Ω̇ = −(3/2)·J₂·(R_E/p)²·n·cos i          [nodal regression]
ω̇ = (3/4)·J₂·(R_E/p)²·n·(5cos²i − 1)    [apsidal precession]
```
**⚠️ Two elegant exploitations:**
- **Sun-synchronous orbit**: choose `i` so `Ω̇` = 0.9856°/day (Earth's mean motion about the
  Sun). At 800 km this gives **i ≈ 98.6°** — retrograde. **The orbit precesses to keep
  local solar time constant**, which is why imaging satellites always see the same
  lighting.
- **Molniya orbit**: set `5cos²i − 1 = 0` → **i = 63.4°**, freezing apsidal precession so
  apogee stays over the northern hemisphere. Highly eccentric, 12-hour period, long
  northern dwell.

**Drag** — dominant below ~600 km: `a_drag = −(1/2)·ρ·(C_D·A/m)·v²·v̂`.
⚠️ **`ρ` varies by more than an order of magnitude with solar activity**, making reentry
prediction genuinely uncertain. Ballistic coefficient `β = m/(C_D·A)` determines lifetime.

**Third-body** (Moon, Sun), **solar radiation pressure** (~4.5 μN/m² at 1 AU; dominant for
high area-to-mass), and **higher geopotential terms** — ⚠️ **the J₂₂ tesseral term drives
GEO satellites toward two stable longitudes, requiring east-west station-keeping.**

---
