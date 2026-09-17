---
name: endeavour-fusion-physics-confinement-and-engineering
description: "Use when reasoning about fusion energy — reading a Q or gain claim and working out which Q it means, comparing D-T against D-D, D-³He or p-¹¹B, computing or sanity-checking a Lawson triple product, choosing between magnetic and inertial confinement, or judging why a demonstrated net gain is still not a power plant. Covers the binding energy curve, the Coulomb barrier and the 10–15 keV requirement, the candidate-reaction table, tokamaks and stellarators, direct and indirect drive, tritium breeding, 14 MeV neutron damage, divertor heat flux, HTS magnets, and the nuclear background of forces, decay, shielding and dose. Part 6 of 12 of the Military Science, Rockets, Space, Fusion, and Mars reference."
---

# Fusion Physics, Confinement, and Why Fusion Is Hard to Engineer

> **Part 6 of 12** of the *Military Science, Rockets, Space, Fusion, and Mars* reference (plugin
> `military-space-rockets-and-fusion`), covering §23–§25 — fusion physics and the Lawson criterion, the two confinement families, and the engineering and nuclear background. Sibling skills:
> `endeavour-military-theory-levels-of-war-and-deterrence` (§1–§3 — what military science is, Clausewitz and Sun Tzu, sea and air power, the levels of war, and deterrence, nuclear strategy, escalation and alliances),
> `endeavour-logistics-doctrine-modern-conflict-and-the-law` (§4–§6 — force structure and logistics, doctrine, intelligence and procurement, modern conflict from unmanned systems to total defence, and the law of armed conflict),
> `endeavour-rocket-equation-nozzles-engines-and-propellants` (§7–§10 — Tsiolkovsky and staging, nozzle thermodynamics and the c*/C_F factorization, turbomachinery, engine cycles and cooling, and propellants),
> `endeavour-orbits-ascent-structures-and-reentry` (§11–§16 — vis-viva and manoeuvres, the ascent Δv budget, aerodynamic loads and structures, guidance and control, reentry physics and failure physics),
> `endeavour-mission-architecture-and-spacecraft-subsystems` (§17–§22 — mission architecture, power and thermal, communications and navigation, attitude control and EDL, human physiology, life support and ISRU, and reliability),
> `endeavour-satellites-flight-software-and-instruments` (§26–§28 — satellite types and orbits, flight software and FDIR, scientific instrumentation and planetary protection),
> `endeavour-the-martian-environment-and-in-situ-resources` (§29–§30 — Mars as a set of engineering parameters, and its water, CO₂ and regolith resources),
> `endeavour-mars-mission-design-and-settlement` (§31–§32 — launch windows, Mars EDL, communications and surface power, habitats, mobility, ECLSS closure and the psychological challenge),
> `endeavour-terraforming-warming-and-the-magnetic-field-problem` (§33–§35 — terraforming theory and the three habitability thresholds, the five gas sources and warming strategies, and the magnetic field problem),
> `endeavour-ecopoiesis-oxygen-timelines-and-ethics` (§36–§38 — ecopoiesis and the oxygen problem, the timeline estimates, paraterraforming, ethics and the Venus comparison),
> `endeavour-reference` (§39–§40 — the glossary spanning all six parts, and the further-reading list),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. **This is fusion energy, not weapons.** The material here is reactor
> physics and power-plant engineering — confinement, materials, breeding, heat removal — and it
> contains no weapon design, device physics or yield information. The physics does not expire; the state of any particular machine or programme does.

## The framing for Part IV

The binding energy curve explains fission and fusion in one picture. **Iron-56 is the most tightly
bound nucleus.** Anything heavier releases energy by splitting; anything lighter releases energy by
fusing. Both run downhill toward iron.

**Nuclear energy densities are about a million times chemical** — the same Coulomb barrier scaling
that makes nuclear reactions hard to initiate makes them enormous once initiated. Every practical
consequence — fuel volumes, waste volumes, accident severity — follows from that factor.

---

## §23 Fusion physics, the candidate reactions, and the Lawson criterion

### The Coulomb barrier is the whole problem

Nuclei must approach to **~1 fm** against electrostatic repulsion. Quantum tunnelling helps, but you
still need **~10–15 keV (~100–150 million K)**. Everything else in fusion — every magnet, every
laser, every confinement scheme — exists to hold matter at that temperature long enough and densely
enough to burn.

### The candidate reactions

| Reaction | Products | Notes |
|---|---|---|
| D + T | ⁴He (3.5 MeV) + n (14.1 MeV) | Highest cross section at lowest temperature. The only near-term option — and 80% of the energy is in a neutron |
| D + D | Two branches | No tritium needed, much harder |
| D + ³He | ⁴He + p | Aneutronic-ish, but ³He is essentially unavailable and needs far higher temperature |
| p + ¹¹B | 3 ⁴He | Truly aneutronic; enormous temperature and bremsstrahlung losses. Very hard |

**Why D-T despite the neutron problem.** Its cross section peaks **about 100× higher and at roughly
a quarter the temperature** of the alternatives. Everything else is a much harder physics problem in
exchange for an easier engineering one — and the engineering price D-T charges in return is the
14.1 MeV neutron, which is where most of §25 goes.

Note the split inside D-T's own energy release: the **3.5 MeV alpha** stays charged and can be
confined, which is what makes self-heating possible; the **14.1 MeV neutron** leaves immediately,
carrying 80% of the yield into the structure. The reaction that is easiest to ignite is also the one
that puts most of its output somewhere you cannot steer it.

### The Lawson criterion / triple product

    n · T · τ_E ≳ 3×10²¹ keV·s·m⁻³   (D-T ignition)

Density × temperature × energy confinement time. **The two confinement approaches attack different
factors of the same product**, which is why they look nothing alike and yet are measured against the
same number:

| | Density | Energy confinement time τ_E | How the product is reached |
|---|---|---|---|
| Magnetic confinement | Low | Long — **seconds** | Hold a thin plasma still for a long time |
| Inertial confinement | Enormous | Vanishing — **nanoseconds** | Compress to extreme density and let inertia do the rest |

Both must reach the same product. A scheme that wins on one factor has to pay for it on another.

> **Q DEFINITIONS — A RECURRING SOURCE OF INFLATED CLAIMS**
>
> - **Q_scientific** is fusion energy out divided by energy delivered to the plasma or target.
> - **Q_engineering** is electricity out divided by total electricity in, *including the whole
>   facility* — **this is the one that matters for a power plant**.
> - **Ignition** is when the alpha particles alone sustain the burn.
> - **NIF's reported gains are scientific Q against laser energy delivered to the target**, not
>   against the wall-plug energy drawn by the laser system, which is far larger.
>
> When a headline reports a gain, the first question is which Q it is measured against, and the
> second is what was in the denominator.

## §24 Magnetic and inertial confinement

### Magnetic confinement

Charged particles spiral along field lines, and a toroidal geometry closes those lines so they never
leave. **A purely toroidal field does not confine.** Field curvature and gradient cause
charge-dependent drift, the plasma separates, and it is lost. You need a twist — a **poloidal
component** — and the two leading configurations are two opposite answers to where that twist comes
from.

| Configuration | Source of the poloidal twist | Strength | Weakness |
|---|---|---|---|
| **Tokamak** | A current driven in the plasma itself | Axisymmetric and best-understood | That current is a free energy source for disruptions |
| **Stellarator** | External coils only | Intrinsically steady-state and disruption-free | Coil geometry is fiendishly complex, and only became tractable with modern computation |

Others in the family: **spherical tokamak, reversed field pinch, mirrors, FRC**.

**The problem set:**

- **Disruptions** — a sudden loss of confinement dumping enormous energy onto the wall. **The main
  risk in tokamaks**, and the direct consequence of storing energy in a plasma current.
- **MHD instabilities**.
- **ELMs** (edge-localized modes).
- **Turbulent transport** — this is what **sets τ_E**, and it is why **empirical scaling laws still
  substitute for first-principles prediction**. You cannot yet compute confinement time from first
  principles for a machine that has not been built.
- **Divertor heat load** — where the exhaust power lands; the number is under §25 below.

### Inertial confinement

Compress and heat a fuel capsule so fast that **inertia** confines it long enough to burn — over
nanoseconds. No field holds the fuel; its own mass does, briefly.

- **Direct drive** — lasers on the capsule.
- **Indirect drive** — lasers heat a high-Z **hohlraum** which re-radiates X-rays. More uniform, less
  efficient. **This is NIF's approach.**

**The physics obstacles**, in order of how much they dominate:

1. **Rayleigh-Taylor instability during compression — the dominant one.** Any surface imperfection
   grows catastrophically as the implosion proceeds.
2. Required implosion **symmetry**.
3. **Laser-plasma instabilities**.
4. **Capsule fabrication tolerances** — the target is a precision-manufactured object, and it is
   consumed in nanoseconds.

**Repetition rate is the gulf between ignition and a power plant.** NIF fires occasionally; a plant
would need **several shots per second, with a fresh target each time**. Ignition demonstrates the
physics of the burn; nothing about it demonstrates a machine that can do it continuously, cheaply,
and with targets manufactured at that rate.

## §25 Why fusion is hard to engineer, and the nuclear background

**The physics of net gain is now demonstrated.** These are the reasons that is not the same as a
power plant. None of them is a physics objection; all of them are unfinished engineering, and one of
them has never been demonstrated at all.

### Tritium — the largest unproven requirement

Tritium has a **12.3-year half-life** and **does not occur naturally in useful quantities**. A D-T
plant must therefore **breed its own from lithium using its own neutrons**, requiring a **tritium
breeding ratio above 1 including losses**. This has **never been demonstrated in an integrated
system**, and it is arguably **the single largest unproven requirement** in the whole enterprise. A
plant that cannot close its own fuel cycle has no fuel supply.

### 14 MeV neutrons — no qualified material, and no facility to qualify one

**80% of D-T energy is in neutrons** that damage structural materials through **displacement damage**
and **helium embrittlement**, and that **activate the structure**. Two facts stand together and are
what make this hard:

- **No material has been qualified for a full plant lifetime at fusion neutron fluence.**
- **There is no operating high-flux 14 MeV test facility** — which is why **IFMIF/DONES** matters.

You cannot qualify a material without the neutron source, and the neutron source is itself a
programme. This one is open, and nothing here closes it.

### Divertor heat flux

Steady-state loads **approaching 10 MW/m²** — **comparable to a rocket nozzle, sustained for years**.
The comparison is worth holding onto: rocket chambers run 10–160 MW/m² at the throat
(§9 → `endeavour-rocket-equation-nozzles-engines-and-propellants`), regeneratively cooled by the
propellant they are about to burn, on hardware often flown once. A divertor takes a flux in that
family with **neither of those escapes**, sustained for a plant lifetime — and that is where the
difficulty sits.

### Magnets

**HTS (REBCO) tape is the enabling change** — higher field allows a much smaller device, since
**fusion power scales roughly as B⁴**. That exponent is the whole argument: a modest gain in
achievable field is a large gain in power density, and therefore a large reduction in machine size
for a given output.

### Economics

A fusion plant is a **large capital-intensive thermal plant with an expensive, complex core**.
**"Fuel is free" is not the cost driver; capital cost is.** Cheap fuel does not make cheap
electricity when the machine that burns it is the expensive part.

### The honest radiological account

**Fusion is not radiologically clean, though it is much better than fission.**

- **No long-lived actinides**, and **no chain reaction to run away**.
- But **activated structure and a tritium inventory are real**.
- **Low-activation steels** are designed to make the waste decay to **hands-on levels in ~100 years
  rather than 100,000**.

That is a genuine and large improvement, and it is not the same as "no waste". Say both.

### Nuclear background: the four forces and the liquid drop model

At nuclear scale: **strong** (binds nucleons, range **~1 fm** — its short range is why big nuclei
become unstable, because **every proton repels every other but only neighbours attract**),
**electromagnetic** (repels protons), **weak** (beta decay), **gravity** (negligible).

The **semi-empirical mass formula (liquid drop model)** captures most binding energy in five terms:

    volume − surface − Coulomb − asymmetry − pairing

It explains the shape of the binding curve, the valley of stability, and **why fission becomes
energetically favourable for heavy nuclei** — the Coulomb term grows with every proton pair while
the attractive volume term only grows with neighbours.

### Radiation types, shielding, and dose

| Type | Stopped by | Hazard |
|---|---|---|
| Alpha | cm of air; stopped by skin | Negligible externally, **severe internally** |
| Beta | mm of plastic | Skin and eye dose |
| Gamma | Attenuates exponentially | Whole-body penetrating |
| Neutron | Hydrogenous shielding | Highly damaging, **activates materials** |

**Shielding logic.** Hydrogen-rich material (water, polyethylene, concrete) to moderate neutrons,
then a **thermal absorber (boron)**; **high-Z material (lead) for gamma**. **Layered shields are the
norm** — no single material handles the mixed field, and the order matters.

**Dose quantities**, which are four different things people routinely conflate:

| Quantity | Unit | What it measures |
|---|---|---|
| Activity | becquerel (Bq) | Decays per second — **a property of the source** |
| Absorbed dose | gray (Gy) | J/kg deposited |
| Equivalent dose | sievert (Sv) | Gy × radiation weighting |
| Effective dose | sievert (Sv) | × tissue weighting |

**Bq tells you nothing about hazard on its own.** A large Bq number from a weak alpha emitter safely
contained is harmless; a small number inhaled is not. For the dose numbers that bound human
spaceflight — GCR and SPE, and NASA's 600 mSv career limit — see
§21 → `endeavour-mission-architecture-and-spacecraft-subsystems`, and for the measured Martian
surface dose and regolith shielding see §29 → `endeavour-the-martian-environment-and-in-situ-resources`.

> **LONG HALF-LIFE MEANS LOW ACTIVITY**
>
> Activity is **λN**, and **λ = ln2/t½**. **²³⁸U (4.5 billion years) is barely radioactive — you can
> hold it. ¹³¹I (8 days) is intensely radioactive and dangerous.** "It stays radioactive for 10,000
> years" and "it is dangerously radioactive" are **close to opposites**, and the confusion drives a
> lot of bad reasoning about waste.

Run the same λ = ln2/t½ arithmetic the other way and ²³⁸Pu's **87.7-year half-life** sits where a
decades-long mission needs it: hot enough to deliver **~110 W electrical at BOL** through a ~6–7%
thermoelectric conversion, and slow enough to decay at only **~1.6%/yr** — see §18 →
`endeavour-mission-architecture-and-spacecraft-subsystems`.

Definitions of the terms of art used here — binding energy curve, Lawson criterion — and the books
that teach this material are in §39–§40 → `endeavour-reference`.
