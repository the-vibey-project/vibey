---
name: endeavour-orbits-ascent-structures-and-reentry
description: "Use when budgeting Δv for a transfer or an ascent, sizing a Hohmann burn or a plane change, choosing an orbit that exploits J₂, explaining why launch-site latitude is a hard mission constraint, reasoning about max-Q, q·α, buckling knockdown factors, pressure-stabilized tanks or POGO, scheduling notch filters and powered-descent guidance, or sizing a heat shield against Sutton-Graves and an entry corridor. Part 4 of 12 of the Military Science, Rockets, Space, Fusion, and Mars reference."
---

# Orbital Mechanics, Ascent, Structures, Guidance, and Reentry

> **Part 4 of 12** of the *Military Science, Rockets, Space, Fusion, and Mars* reference (plugin
> `military-space-rockets-and-fusion`), covering §11–§16 — orbits and manoeuvres, the ascent Δv budget,
> aerodynamic loads and thin-walled structures, guidance and control, reentry physics, and the failure
> modes that recur. Sibling skills:
> `endeavour-military-theory-levels-of-war-and-deterrence` (§1–§3 — what military science is, the theoretical canon, the levels of war, deterrence and nuclear strategy),
> `endeavour-logistics-doctrine-modern-conflict-and-the-law` (§4–§6 — force structure, logistics, doctrine, intelligence, procurement, modern conflict, and the law of armed conflict),
> `endeavour-rocket-equation-nozzles-engines-and-propellants` (§7–§10 — Tsiolkovsky and staging, nozzle thermodynamics and the c*/C_F factorization, turbomachinery, engine cycles, cooling, and propellants),
> `endeavour-mission-architecture-and-spacecraft-subsystems` (§17–§22 — mission architecture, power, thermal, comms, navigation, attitude control, in-space propulsion, EDL, human physiology, life support and reliability),
> `endeavour-fusion-physics-confinement-and-engineering` (§23–§25 — fusion reactions, the Lawson criterion, magnetic and inertial confinement, and why fusion is hard to engineer),
> `endeavour-satellites-flight-software-and-instruments` (§26–§28 — satellite types and orbit regimes, flight software and FDIR, instrumentation and planetary protection),
> `endeavour-the-martian-environment-and-in-situ-resources` (§29–§30 — the Martian environment as engineering parameters, and Mars resources and ISRU),
> `endeavour-mars-mission-design-and-settlement` (§31–§32 — Mars launch windows, EDL, communications, surface power, habitats and settlement),
> `endeavour-terraforming-warming-and-the-magnetic-field-problem` (§33–§35 — terraforming theory, the habitability thresholds, atmospheric thickening, warming, and the magnetic field problem),
> `endeavour-ecopoiesis-oxygen-timelines-and-ethics` (§36–§38 — ecopoiesis, the oxygen problem, timelines, paraterraforming, ethics and the Venus comparison),
> `endeavour-reference` (§39–§40 — the glossary and the further reading),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Everything here is durable physics — vis-viva, the buckling and POGO failure
> modes, and the Sutton-Graves scaling do not expire; reliability statistics and vehicle-specific
> figures drift.

Three ideas carry this whole part. **Orbits are energy states, not altitudes** — vis-viva turns two numbers
into nearly every mission-design answer. **The atmosphere is a structural problem before it is a drag
problem** — the ascent is flown to a load metric, not an efficiency metric, and the vehicle is a thin-walled
cylinder that buckles rather than yields. And **reentry disposes of energy into air rather than into the
vehicle**, which is why every crew capsule is bluff rather than sleek. The propulsion supplying the Δv is
§7–§10 → `endeavour-rocket-equation-nozzles-engines-and-propellants`.

## §11 Orbital mechanics: vis-viva, manoeuvres, and perturbations

From Newton, the two-body problem gives **conic-section orbits**. The **vis-viva equation** is the
single most useful formula in mission design:

    v² = μ · (2/r − 1/a)

> **ENERGY DEPENDS ONLY ON THE SEMI-MAJOR AXIS.** Everything else about the orbit — eccentricity,
> orientation, where you happen to be in it — drops out of the energy budget. Two numbers, r and a,
> and vis-viva gives you the speed.

The three relations that follow:

| Quantity | Relation | Note |
|---|---|---|
| Circular velocity | v = √(μ/r) | the speed that holds a given radius |
| Escape velocity | v = √(2μ/r) = **√2 · v_circ** | only **41% more** than circular |
| Period | T = 2π√(a³/μ) | Kepler's third |

Escape being only 41% above circular is the reason **interplanetary departure is cheaper than intuition
suggests** — you are not doubling the job you already did to reach orbit.

### Manoeuvres

The **Hohmann transfer** is two burns and the minimum-energy path between coplanar circular orbits.
Worked example, LEO (6,678 km) to GEO (42,164 km):

| Burn | What it does | Δv |
|---|---|---|
| Δv₁ | circular at 6,678 km → transfer ellipse | **2.513 km/s** |
| Δv₂ | transfer ellipse → circular at 42,164 km | **1.453 km/s** |
| **Coplanar total** | — | **3.966 km/s** |
| Inclination change of 28.5° at GEO | if the launch site forced one | **~1.8 km/s** |

**Bi-elliptic beats Hohmann when r₂/r₁ > 11.94** — counterintuitive, and genuinely used for some
high-energy transfers.

**Plane change:** Δv = 2v·sin(Δi/2). At LEO velocity a **28.5° plane change costs 3.8 km/s — more than
reaching GEO at all**.

> **LAUNCH-SITE LATITUDE IS A HARD MISSION CONSTRAINT, NOT A PREFERENCE.** Because plane change scales
> with the velocity you are already carrying, you launch directly into your target inclination rather
> than fixing it later, and when a plane change is unavoidable you do it at apoapsis where v is
> smallest. The same geometry decides which orbit regimes a given site can serve at all
> (§26 → `endeavour-satellites-flight-software-and-instruments`).

**The Oberth effect:** for a burn Δv at speed v, the energy change is

    Δε = v·Δv + Δv²/2

The **v·Δv** term means the same propellant buys more energy when you are moving faster — hence
departure burns at periapsis, and the value of **dropping deep into a gravity well before burning**.

### Perturbations

**J₂ (Earth oblateness) is the dominant perturbation**, and it has two elegant exploitations:

- **Sun-synchronous orbit** — choose the inclination so that nodal regression matches Earth's mean
  motion about the Sun. At 800 km that is **i ≈ 98.6°, retrograde**, and it keeps local solar time
  constant, which is why imaging satellites use it.
- **Molniya orbit** — set **5cos²i − 1 = 0**, i.e. **i = 63.4°**, which freezes apsidal precession so
  apogee stays over the northern hemisphere.

**Drag dominates below ~600 km**, and atmospheric density varies by **more than an order of magnitude with
solar activity** — which is why **reentry prediction is genuinely uncertain**, not merely imprecise.

## §12 The ascent trajectory and the Δv budget

The full budget is additive, with one term working in your favour:

    Δv_required = Δv_orbital + Δv_gravity + Δv_drag + Δv_steering − Δv_rotation

| Term | Sign | Magnitude | What sets it |
|---|---|---|---|
| Δv_orbital | + | the orbit you want | vis-viva (§11 above) |
| **Δv_gravity** | + | **1.2–1.7 km/s** for a typical launch | time spent fighting gravity — minimized by pitching over early and by high initial thrust-to-weight |
| Δv_drag | + | **only 100–150 m/s** | much smaller than people expect, because the vehicle is through the dense atmosphere quickly |
| Δv_steering | + | *(no magnitude given in this reference)* | departures from the ideal thrust direction |
| **Δv_rotation** | **−** | **465·cos(latitude) m/s** eastward — Cape Canaveral gets **409 m/s** | launch-site latitude; polar and retrograde launches forfeit it |

**Gravity loss is the big one**, and practical liftoff **thrust-to-weight is 1.2–1.4**. The Earth rotation
credit is why **equatorial sites are valuable**.

### The gravity turn — and why zero-α is structural

After a vertical rise the vehicle pitches slightly, then lets gravity rotate the velocity vector at
**zero angle of attack**.

> **ZERO-α IS NOT AN EFFICIENCY CHOICE — IT IS A STRUCTURAL ONE.** Aerodynamic side loads on a long
> thin cylinder at angle of attack generate bending moments the structure cannot take. The trajectory
> is shaped by what the airframe survives, not by what the propulsion prefers.

**Max-Q** occurs where **q = ½ρv²** peaks — **typically 30–90 seconds, at 10–15 km altitude, at
20–40 kPa**. Engines throttle down through it to limit loads.

## §13 Aerodynamic loads and thin-walled structures

**Dynamic pressure q = ½ρv² drives everything structural in the atmosphere**, and the metric vehicles
are actually flown to is the **q·α product**: guidance limits q·α, and **wind shear is dangerous
precisely because it creates α the vehicle did not command**.

Launch vehicles are **aerodynamically unstable** — centre of pressure ahead of centre of mass — and are
**actively stabilized by thrust vectoring**, so **a control failure is immediately catastrophic** (§14 below).

**Acoustic loads at liftoff are 160–180 dB OASPL.** Water deluge is **not primarily cooling — it is acoustic
suppression**, protecting the payload and vehicle from reflected acoustic energy that could shake components
apart.

### Buckling governs, not yielding

| Structural fact | Consequence |
|---|---|
| Thin-walled cylinder axial buckling uses a **knockdown factor γ of 0.15–0.65** | real cylinders are **exquisitely sensitive to imperfections**; **classical theory over-predicts buckling strength by up to 5×** |
| **Pressure stabilization** — internal pressure adds tensile stress that raises the effective buckling threshold | Atlas's **balloon tanks** took this to the limit: the vehicle **would collapse under its own weight if depressurized** |
| **Hoop stress is twice longitudinal stress** — σ_h = pR/t, σ_l = pR/(2t) | cylindrical tanks **fail along a longitudinal seam**, so **weld orientation matters** |

**POGO** is a closed-loop instability: structural longitudinal modes → feedline pressure oscillation → thrust
oscillation → back into the structure. It **nearly destroyed Apollo 13's S-II**, and is suppressed with
**gas-filled accumulators in the feedlines that detune the hydraulic resonance**.

## §14 Guidance and control

Attitude dynamics:

    I·ω̇ + ω × (I·ω) = M

The **ω × Iω gyroscopic coupling term is why 3-axis control is not three independent problems** — an
axis you excite shows up in the others.

**TVC control authority is small and shrinking:** typical gimbal range is **only ±5–8°**, and it
**decreases as propellant depletes and the centre of mass moves**.

Two control challenges, each a real loss-of-vehicle mode:

- **Slosh** — propellant in a partly-full tank behaves like a pendulum; **anti-slosh baffles raise
  damping**.
- **Flexible body modes** — the vehicle bends, the IMU measures local attitude *including* the bending
  mode, and a controller with gain at that frequency **drives the mode**. **Notch filters at the
  bending frequencies are mandatory**, and because **the frequencies shift as propellant drains, the
  filters must be scheduled**.

### Guidance phases

| Phase | Law | Why |
|---|---|---|
| Atmospheric | **open-loop pitch program** | closed-loop steering at high q risks commanding an α the structure cannot survive (§13 above) |
| Vacuum | **Powered Explicit Guidance** | solves the **linear-tangent steering law**, which is the optimal-control solution |

**Powered descent** is the hard one: the landing problem is **non-convex**, because thrust magnitude is
**bounded below by a non-zero minimum** — an engine cannot be throttled to nothing and restarted at
will.

> **LOSSLESS CONVEXIFICATION IS THE GENUINELY IMPORTANT MODERN CONTRIBUTION.** Açıkmeşe and Ploen
> proved that a **relaxed convex formulation has the same optimum** as the original non-convex problem.
> That makes **real-time solutions with guaranteed convergence** possible, and it is **why autonomous
> propulsive landing became practical** — a theorem, not an incremental engineering gain.

## §15 Reentry physics

> **REENTRY HEATING IS COMPRESSION, NOT FRICTION.** The **bow shock compresses and heats the air**, and
> the vehicle is heated by that gas. A **blunt body pushes a detached bow shock ahead of itself,
> dumping most of the energy into the air rather than into the vehicle**. A slender, "aerodynamic"
> shape produces an **attached** shock and concentrates heating on the surface — it would be destroyed.
> This is why **every reentry vehicle from Mercury to Orion to Dragon is bluff**.

Stated as energy, the problem is to **dispose of ~30 MJ/kg (LEO) or ~60 MJ/kg (lunar return) without
depositing it in the vehicle**.

**Peak deceleration depends only on entry velocity and flight path angle — not on mass or drag area:**

    a_max = v_e² · sin γ / (2·e·H)

Apollo: **~6.5 g**. A ballistic Soyuz abort: **~9 g**.

**Stagnation-point heating — the Sutton-Graves relation:**

    q_s = k · √(ρ/R_n) · v³

Two consequences follow directly from the exponents:

| Scaling | Consequence |
|---|---|
| **q ∝ v³** | lunar return at **11 km/s** versus LEO at **7.8 km/s** is **2.8× the heat flux** |
| **q ∝ 1/√R_n** | **a blunter nose reduces peak heating** — another argument for bluff bodies |

**Total heat load scales differently from peak flux.** A **shallow entry lowers peak flux but raises
total load**. The design rule that falls out: **peak flux sizes the material; total load sizes the
thickness.**

**The entry corridor** is bounded on both sides — **too steep exceeds heating and g-limits; too shallow skips
out**. For **Apollo lunar return the corridor was about ±1° in flight path angle** — a genuinely tight target
from **400,000 km away**. The Martian version of this squeeze, where the atmosphere is too thick to ignore and
too thin to stop you, is §20 → `endeavour-mission-architecture-and-spacecraft-subsystems` and
§31 → `endeavour-mars-mission-design-and-settlement`.

## §16 Failure physics and normalization of deviance

**Combustion instability** — acoustic modes of the chamber coupling with the combustion process. **Tangential
modes are the destructive ones: they can destroy an engine in milliseconds.** The **F-1 required about 2,000
full-scale tests and years of injector iteration**, and **it is still not a fully predictive discipline**. The
injector geometry that sets stability is §8 → `endeavour-rocket-equation-nozzles-engines-and-propellants`.

**Stage separation** is **brief, violent, and essentially untestable at full scale on the ground** —
**recontact, plume impingement and tip-off rates** are all risks, and each added stage buys Δv at the price of
another separation event (§7 → `endeavour-rocket-equation-nozzles-engines-and-propellants`).

### The reliability numbers, as they stand

| Population | Success rate |
|---|---|
| **New vehicles, first flight** | **roughly 50%**, historically |
| **Mature vehicles** | **95–98%** |
| Aviation-class reliability | **no launch vehicle approaches it** |

The physics is why: **thin margins, no redundancy in structure, single-use hardware.** Margin practice
on the spacecraft side — where redundancy *is* affordable — is
§22 → `endeavour-mission-architecture-and-spacecraft-subsystems`.

> **NORMALIZATION OF DEVIANCE.** An off-nominal observation recurs without consequence and is
> reclassified as acceptable. **Challenger (O-ring blow-by)** and **Columbia (foam shedding)** both
> followed this pattern, and **both accident boards concluded the organizational cause dominated the
> technical one**. This is the recurring organizational failure mode in aerospace: **the system that
> tolerated the anomaly is the system that produced the disaster.**
