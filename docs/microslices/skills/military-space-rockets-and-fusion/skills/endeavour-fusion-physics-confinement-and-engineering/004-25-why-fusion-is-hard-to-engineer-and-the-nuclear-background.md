---
id: skill-25-why-fusion-is-hard-to-engineer-and-the-nuclear-background-8b7dbe5f6e
purpose: 25 why fusion is hard to engineer and the nuclear background
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-fusion-physics-confinement-and-engineering/SKILL.md
requires: ["skill-24-magnetic-and-inertial-confinement-2657877a5e"]
links: []
---

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
