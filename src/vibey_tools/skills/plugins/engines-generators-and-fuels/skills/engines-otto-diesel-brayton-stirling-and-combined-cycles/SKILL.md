---
name: engines-otto-diesel-brayton-stirling-and-combined-cycles
description: "Use when choosing or comparing an engine cycle (petrol, diesel, gas turbine, Stirling, combined cycle), working out why a compression ratio is limited, diagnosing knock or ignition-timing retard, explaining volumetric efficiency or Atkinson/Miller valve timing, sizing diesel aftertreatment, or reasoning about gas-turbine back-work ratio and combined-cycle efficiency. Covers the non-Rankine engine family with its efficiency equations, real efficiency figures and the practical limit behind each. Part 3 of the Engines, Generators and Fuel Sources reference."
---

# Otto, Diesel, Brayton, Stirling and Combined Cycles

> **Part 3 of 7** of the *Engines, Generators, and Fuel Sources* reference (plugin
> `engines-generators-and-fuels`), covering §7–§11 — internal combustion, gas turbines, the Stirling engine, and the combined cycle. Sibling skills:
> `engines-thermodynamics-and-the-carnot-ceiling` (§1–§3 — the four laws, the Carnot ceiling, working fluids and phase behaviour),
> `engines-rankine-steam-engines-and-turbines` (§4–§6 — the Rankine cycle and its five improvements, reciprocating engines and turbines, and what you would actually build),
> `engines-generators-and-house-power` (§12–§14 — Faraday to a wired house: generator theory, the four machine types, and designing or buying a house system),
> `engines-fuels-and-combustion` (§15–§17 — every fuel that can be burned, transformed or harvested, with energy densities and what engine each pairs with),
> `engines-rebuilding-engines-materials-and-tolerances` (§18–§20 — engine anatomy and the rebuild process, engine management and forced induction, and the materials and tolerance thinking that makes parts real),
> `engines-safety-and-reference` (§21–§23 — the six things that kill, the glossary, and the books that actually teach this),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Everything here is durable engineering and physics — the laws, cycles and
> equations do not expire; efficiency figures for current plant and practice do drift.

## THE UNIVERSAL DESIGN PRINCIPLE

All heat engines descend from the same ancestor: heat flows from hot to cold, and you can extract work
from that flow if you insert a machine in the path. Engine types are distinguished by working fluid,
thermodynamic cycle, internal or external combustion, and batch (reciprocating) or continuous (rotary)
operation.

> **Every improvement to every engine cycle is the same idea in different clothes — move heat addition
> to a HIGHER average temperature, or heat rejection to a LOWER one.** Superheating, reheating,
> regeneration, intercooling, combined cycles, higher compression ratios all serve that single goal.

That is the Carnot ceiling η = 1 − T_C/T_H (§2 → `engines-thermodynamics-and-the-carnot-ceiling`)
expressed as design practice. Read every cycle below as an answer to one question: *where is the lever
on T_H or T_C, and what stops me pulling it further?*

| Cycle | Combustion / flow | Lever on T_H | What stops you | Real efficiency |
|---|---|---|---|---|
| Otto (§7) | Internal, batch | Compression ratio | Knock — a fuel-chemistry limit | 25–35% |
| Diesel (§8) | Internal, batch | Much higher compression ratio | Peak cylinder pressure, mechanical stress, cold-start and emissions limits | 35–45% road; **50–55% large marine** |
| Brayton (§9) | Internal, continuous | Turbine firing temperature | Back-work ratio; blade materials | 30–40% simple cycle |
| Stirling (§10) | External, batch, sealed fluid | Any external heat source | Heat transfer, sealing, regenerator | Carnot in theory only |
| Combined (§11) | Brayton topping + Rankine bottoming | Brayton T_H with Rankine T_C | Nothing better is in service | **55–62%** |

## §7 The Otto cycle (spark-ignition / petrol)

The four-stroke cycle powering most cars: **intake, compression, power, exhaust** over two crankshaft
revolutions. **The 2:1 cam ratio and its consequence:** the camshaft turns at half crankshaft speed
because each valve opens once per two revolutions — which is why timing belt/chain ratios are 2:1, and
why **being one tooth out is a large error**. Timing failure on an interference engine is destructive:
§18 → `engines-rebuilding-engines-materials-and-tolerances`.

### Ideal efficiency — Carnot in disguise

    η = 1 − 1/r^(γ−1)        r = compression ratio, γ ≈ 1.4 for air

In the ideal case **efficiency depends on compression ratio alone** — the Carnot principle in
disguise, since higher compression means the mixture reaches a higher temperature before combustion,
i.e. higher T_H. **Editor-computed arithmetic on that equation** across the petrol band (8:1 to
13:1) at γ = 1.4 — none of these figures is from the source, and all of them are *ideal-cycle*
values, to be read against the sourced real-engine 25–35%:

| r | 8:1 | 9:1 | 10:1 | 11:1 | 12:1 | 13:1 |
|---|---|---|---|---|---|---|
| Ideal η = 1 − 1/r^0.4 | 56.5% | 58.5% | 60.2% | 61.7% | 63.0% | 64.2% |

**Real petrol engines achieve 25–35% thermal efficiency.** The gap comes from heat loss to cylinder
walls, finite combustion time, pumping losses (throttle), friction, and real working fluids having
variable specific heats.

### Knock — the limit on compression ratio

Knock (detonation) is **uncontrolled auto-ignition of the end gas ahead of the flame front**: the
remaining mixture explodes spontaneously when rising pressure and temperature from the advancing flame
exceed its auto-ignition threshold.

> **The sharp pressure spike hammers pistons and bearings and can destroy an engine in seconds.**

Knock limits compression ratio in petrol engines, and **it is a FUEL CHEMISTRY problem, not a
mechanical design problem**. Octane rating measures knock resistance.

**The octane misconception.** Higher octane allows higher compression and thus higher efficiency — but
**higher octane fuel does not contain more energy; it simply allows a higher compression ratio that
extracts more of the energy that is there** (fuel side: §15–§17 → `engines-fuels-and-combustion`).

**PRACTICAL CONSEQUENCE.** Modern engines use knock sensors (microphone-like accelerometers on the
block) to detect knock in real time; on detection the ECU retards ignition timing, protecting the
engine but costing power and efficiency. So a car that "feels gutless" may be pulling timing due to
knock caused by carbon deposits (which raise effective compression), bad fuel, overheating, or a lean
condition — **and it may set no fault code at all.** Diagnose with live data
(§19 → `engines-rebuilding-engines-materials-and-tolerances`), not a code scan.

### Volumetric efficiency (VE)

VE is **how completely the cylinder fills with fresh charge**. A naturally aspirated engine at
wide-open throttle might achieve **85–90% VE**; at part throttle much less. Every intake design
feature — ram tubes, tuned lengths, multiple valves, variable valve timing, port design — exists to
improve VE. **Forced induction is the brute-force solution**
(§19 → `engines-rebuilding-engines-materials-and-tolerances`).

### Atkinson / Miller — and why hybrids use them

Closing the intake valve **late (Atkinson)** or **early (Miller)** makes the effective compression
ratio lower than the effective expansion ratio: less work consumed during compression while the full
expansion ratio still serves the power stroke.

| | Effective compression | Effective expansion | Result |
|---|---|---|---|
| Conventional Otto | r | r | Balanced power and efficiency |
| Atkinson / Miller | < r | r | **Higher thermal efficiency, lower power density** |

This is why **Atkinson-cycle engines are standard in hybrids** — the electric motor compensates for
the reduced power density.

## §8 The Diesel cycle (compression-ignition)

Diesels compress air to such a high temperature (**typically 700–900°C at TDC**) that injected fuel
ignites spontaneously — **no spark plug**. This requires much higher compression ratios, which is why
diesels are inherently more efficient.

| | Petrol (Otto) | Diesel |
|---|---|---|
| Ignition | Spark | Compression |
| Compression ratio | 8:1 to 13:1 | **14:1 to 25:1** |
| Throttle | Yes — pumping losses | **None** — power controlled by fuel quantity, not air, so pumping losses are lower |
| Injection | — | Very high pressures; common-rail at **2,000+ bar** |
| Cold start aid | — | Glow plugs |
| Road engine | 25–35% | **35–45%** |
| Large marine | — | **50–55% — the highest of any internal combustion engine** |

**Diagnostic consequence:** because ignition is by compression, a diesel "misfire" is **always a
fuelling or compression problem, never an ignition one**.

**Why lean running forces DPF and SCR rather than a three-way catalyst.** Diesels run lean overall, so
a three-way catalyst cannot work — there is excess oxygen in the exhaust, and a three-way catalyst
only works at stoichiometric operation (§17 → `engines-fuels-and-combustion`). Diesel aftertreatment
therefore requires two devices instead:

| Device | Target | Mechanism |
|---|---|---|
| **DPF** (diesel particulate filter) | Soot | Traps soot and **periodically regenerates by burning it off at high temperature** |
| **SCR** (selective catalytic reduction) | NOx | Uses **urea/AdBlue to convert NOx to nitrogen and water** |

## §9 The Brayton cycle (gas turbines)

Powers jet engines, gas turbine power plants, and the turboshafts of helicopters and some ships.
**Continuous flow, continuous combustion, no reciprocating parts.** Three steps: **compress** ambient
air; **burn** fuel continuously at constant pressure; **expand** the hot gases through a turbine. Some
turbine output drives the compressor; the rest is useful output.

### The back-work ratio problem

> The compressor typically consumes **50–65% of the turbine's gross output** — the Brayton cycle's
> fundamental disadvantage against Rankine, because compressing gas is expensive.

**Isentropic compressor efficiency is critical: compressor irreversibility hurts more than turbine
irreversibility, because the compressor consumes such a large fraction of output.** Contrast Rankine,
where pump work is typically only 1–2% of turbine work because liquid water is nearly incompressible
(§4 → `engines-rankine-steam-engines-and-turbines`) — that low back-work ratio is Rankine's advantage.

| Improvement | What it does | Which side of the principle |
|---|---|---|
| **Intercooling** | Cool between compressor stages to reduce work | Attacks the back-work ratio |
| **Reheat** | Add heat between turbine stages | Raises average heat-addition temperature |
| **Regeneration** | Turbine exhaust preheats compressed air before combustion | Recycles rejected heat into heat addition |
| **Combined cycle (§11)** | Bottoming Rankine cycle on the exhaust | **The biggest step by far** |

Efficiency: simple-cycle gas turbines **30–40%**; combined-cycle plants **55–62%**, the highest of any
heat engine in commercial service. First-stage blades run in 1400–1600°C gas and survive only via
internal cooling, thermal barrier coatings and single-crystal casting
(§20 → `engines-rebuilding-engines-materials-and-tolerances`) — the materials constraint behind the
Carnot lever.

## §10 The Stirling engine

**External combustion with a sealed working fluid** (usually air, helium, or hydrogen). Heat is
applied from outside to one end and removed from the other. A **displacer piston** shuttles the fluid
between hot and cold spaces through a **regenerator** — a heat store that saves heat between cycles —
and expansion and contraction drive a **power piston**.

**Why it can theoretically reach Carnot:** heat addition and rejection are **isothermal**, the Carnot
cycle's defining feature.

**The three practical limits:**

| # | Limit | Why it bites |
|---|---|---|
| 1 | Heat transfer rates through cylinder walls | Slow — the isothermal ideal assumes heat moves as fast as the piston |
| 2 | Sealing of the working fluid | **Hydrogen and helium leak through almost anything** |
| 3 | Regenerator size | The heat store must be large to save heat between cycles |

Low power density and slow response to load changes are the *consequence* of those three, and are
what has limited Stirling engines to niche applications.

**What they are good at:** quiet; can use **any heat source** (solar, geothermal, biomass, waste
heat); **no exhaust emissions from the cycle itself**. External combustion leaves the fuel question
wide open (§15–§17 → `engines-fuels-and-combustion`).

## §11 The combined cycle — the most efficient heat engine

**A Brayton (gas turbine) cycle on top, a Rankine (steam) cycle on the bottom.** Gas turbine exhaust
(**typically 500–650°C**) is not wasted: it passes through a **heat recovery steam generator (HRSG)**
making steam for a bottoming Rankine cycle. **55–62% efficiency, the highest of any heat engine in
commercial service.**

**Why it works.** The Brayton cycle's heat rejection becomes the Rankine cycle's heat source, so the
overall cycle rejects heat at a much lower average temperature than Brayton alone. In Carnot terms it
gets both ends of the lever at once:

| | T_H | T_C |
|---|---|---|
| Brayton alone | Gas turbine firing temperature **~1400–1600°C** | Exhaust to atmosphere |
| Rankine alone | Boiler / superheater temperature | Steam condenser **~30°C** |
| **Combined** | **~1400–1600°C firing temperature** | **~30°C steam condenser** |

A higher T_H **and** a lower T_C than either cycle alone. **The ultimate expression of the universal
principle** stated at the top of this skill.

Next: §12–§14 → `engines-generators-and-house-power` (turning that shaft into electricity),
§15–§17 → `engines-fuels-and-combustion` (what to burn in each), and
§21 → `engines-safety-and-reference` (the hazards around any running engine, carbon monoxide above
all).
