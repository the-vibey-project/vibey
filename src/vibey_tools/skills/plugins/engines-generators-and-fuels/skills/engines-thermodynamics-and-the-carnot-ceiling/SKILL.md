---
name: engines-thermodynamics-and-the-carnot-ceiling
description: "Use when you need the physics that bounds any heat engine — checking whether an efficiency claim is even possible, computing a Carnot ceiling from hot and cold temperatures, deciding whether to raise T_H or lower T_C, writing an energy balance for a closed or open system, or reasoning about a working fluid near saturation, its latent heat, its critical point, or its specific-heat ratio. Covers the four laws of thermodynamics, the Carnot efficiency equation and why efficiency is a materials problem, and phase behaviour including the classic misuse of the ideal gas law. Part 1 of the Engines, Generators and Fuel Sources reference."
---

# Foundational Thermodynamics and the Carnot Ceiling

> **Part 1 of 7** of the *Engines, Generators, and Fuel Sources* reference (plugin
> `engines-generators-and-fuels`), covering §1–§3 — the four laws, the Carnot ceiling, working fluids and phase behaviour. Sibling skills:
> `engines-rankine-steam-engines-and-turbines` (§4–§6 — the Rankine cycle and its five improvements, reciprocating engines and turbines, and what you would actually build),
> `engines-otto-diesel-brayton-stirling-and-combined-cycles` (§7–§11 — internal combustion, gas turbines, the Stirling engine, and the combined cycle),
> `engines-generators-and-house-power` (§12–§14 — Faraday to a wired house: generator theory, the four machine types, and designing or buying a house system),
> `engines-fuels-and-combustion` (§15–§17 — every fuel that can be burned, transformed or harvested, with energy densities and what engine each pairs with),
> `engines-rebuilding-engines-materials-and-tolerances` (§18–§20 — engine anatomy and the rebuild process, engine management and forced induction, and the materials and tolerance thinking that makes parts real),
> `engines-safety-and-reference` (§21–§23 — the six things that kill, the glossary, and the books that actually teach this),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Everything here is durable engineering and physics — the laws, cycles and
> equations do not expire; efficiency figures for current plant and practice do drift.

Every engine — steam, petrol, diesel, gas turbine, Stirling, jet — is at its core a device that
converts heat into useful work. The laws that govern this conversion are the same for all of them,
and they are **not engineering guidelines but laws of nature that no design can violate**. Every
design choice in every engine is ultimately an attempt to get closer to a thermodynamic limit while
working around material and practical constraints.

---

## §1 The four laws of thermodynamics

| Law | What it states | What it buys you |
|---|---|---|
| Zeroth | Two systems each in thermal equilibrium with a third are in equilibrium with each other | Makes temperature a meaningful, measurable quantity |
| First | Energy cannot be created or destroyed, only transformed | The bookkeeping identity — you cannot win |
| Second | Entropy sets a direction; some heat must always be rejected | The ceiling — where all the engineering lives |
| Third | Entropy → a constant as T → absolute zero | The floor — absolute zero is unreachable in finite steps |

### Zeroth Law

If two systems are each in thermal equilibrium with a third, they are in equilibrium with each
other. This is what makes temperature a meaningful, measurable quantity. Named "zeroth" because the
First and Second were already numbered when its foundational role was recognized.

### First Law (energy conservation)

Energy cannot be created or destroyed, only transformed.

**Closed system:**

    ΔU = Q − W

where U is internal energy, Q is heat added *to* the system, W is work done *by* the system.

**Open system** (a control volume with mass flowing through it — the model used for many real
engines and engine components):

    Q̇ − Ẇ = Σṁ_out(h + V²/2 + gz) − Σṁ_in(h + V²/2 + gz)

where h is enthalpy (internal energy plus flow work, **h = u + Pv**), V is velocity, gz is
gravitational potential. This is the **steady-flow energy equation**, the bookkeeping identity every
flow analysis starts from.

**Why enthalpy exists.** Not a distinct form of energy. It exists because the engines and components
analysed this way are open systems — mass crosses their boundaries — and the `Pv` term accounts for
the work required to push that mass across the boundary. Carry `h` instead of `u` and the boundary
work is already paid for. A machine whose working fluid never leaves it — a Stirling engine, a
sealed refrigeration loop — is a closed system, and is analysed with `ΔU = Q − W` or component by
component with flow between the components.

> **KEY INSIGHT.** The First Law says you cannot win — you cannot get more energy out than you put
> in. But it says nothing about *how much* of the heat you can convert to work. That is the Second
> Law's job, and it is where all the engineering lives.

### Second Law (entropy and direction)

Four equivalent statements. Use whichever one makes the argument at hand shortest.

| Form | Statement | Typical use |
|---|---|---|
| Kelvin-Planck | No cycle can convert heat entirely into work using a single thermal reservoir — you must always reject some heat to a colder sink | Killing "100% efficient engine" claims outright |
| Clausius | Heat does not spontaneously flow from cold to hot | Refrigeration and heat-pump arguments |
| Mathematical | dS ≥ δQ/T, with equality only for reversible processes | Cycle analysis, isentropic idealizations |
| Practical | S_gen ≥ 0 for any real process | Quantifying irreversibility in a real component |

**What entropy actually is.** Entropy is **NOT "disorder"** — that popular gloss is misleading.
Entropy measures the number of microscopic configurations consistent with the macroscopic state
(Boltzmann: **S = k ln Ω**). More practically, it measures how much energy has become *unavailable
for doing work* at a given ambient temperature. Every real process generates entropy, and that
entropy generation represents lost work potential.

### Third Law

Entropy approaches a constant (conventionally zero) as temperature approaches absolute zero. Less
practically relevant for engines, but it sets the floor — you cannot reach absolute zero in a finite
number of steps.

## §2 The Carnot efficiency ceiling

**The most important equation in all of engine engineering:**

    η_Carnot = 1 − T_C / T_H

where T_C and T_H are the **ABSOLUTE** temperatures (Kelvin) of the cold and hot reservoirs.

This is the **maximum possible efficiency of any heat engine operating between those two
temperatures, regardless of design, materials, or engineering skill.** It is a limit set by the
temperatures alone.

- Use Kelvin. Every time. Celsius in this equation produces nonsense, including negative and
  greater-than-unity "efficiencies".
- It is a ceiling, not a target. Real cycles fall well below it; see §4–§6 → `engines-rankine-steam-engines-and-turbines` and
§7–§11 → `engines-otto-diesel-brayton-stirling-and-combined-cycles` for how far, and why.

> **CRITICAL CONSEQUENCE.** This is why raising T_H is the perennial goal in power generation. Every
> improvement in engine efficiency throughout history — higher compression ratios, superheated
> steam, reheat cycles, regenerative cycles, combined cycles — is ultimately an attempt to move heat
> addition to a higher *average* temperature or heat rejection to a lower one. **There is no other
> lever.**

### Why efficiency is a MATERIALS problem

The Carnot limit is also why a **materials** problem — finding metals that survive higher
temperatures — is often the binding constraint on engine efficiency, **not** a thermodynamics
problem. The thermodynamics has been settled since Carnot; what changes is what an alloy will
tolerate at temperature. When an efficiency programme stalls, look first at the hot-section metal,
not at the cycle diagram (§18–§20 → `engines-rebuilding-engines-materials-and-tolerances`).

### Reading the ceiling (editor-computed; no source figures below)

| T_H | T_C = 300 K | T_C = 320 K | T_C = 350 K |
|---|---|---|---|
| 600 K | 50.0% | 46.7% | 41.7% |
| 900 K | 66.7% | 64.4% | 61.1% |
| 1200 K | 75.0% | 73.3% | 70.8% |

Two consequences follow directly from `η = 1 − T_C/T_H`:

- **Returns on T_H diminish.** The ceiling rises with T_H but asymptotically toward 1; each
  additional kelvin at the hot end buys less than the last.
- **A kelvin off the cold end is worth more than a kelvin onto the hot end.** Differentiating,
  ∂η/∂T_C = −1/T_H while ∂η/∂T_H = T_C/T_H²; the ratio of their magnitudes is T_C/T_H, which is
  always less than 1. Cold-end improvements are cheap in thermodynamic terms — which is exactly why
  condenser vacuum matters as much as boiler pressure (§4–§6 →
  `engines-rankine-steam-engines-and-turbines`).

## §3 Working fluid properties and phase behaviour

The choice of working fluid determines what kind of engine you have: **water/steam** for Rankine
(§4–§6 → `engines-rankine-steam-engines-and-turbines`), **air** for Brayton and Otto (§7–§11 →
`engines-otto-diesel-brayton-stirling-and-combined-cycles`), **refrigerants** for heat pumps.
Critical properties follow.

### Saturation

At a given pressure a pure substance boils at **exactly one** temperature. While boiling, adding
heat changes the **QUALITY** (vapour fraction) but not the temperature.

This is why a steam boiler at a given pressure produces steam at a fixed temperature — and why
**raising the pressure raises the boiling point**, allowing higher-temperature steam and thus higher
Carnot efficiency (§2). Pressure is the knob; temperature is the consequence.

### Latent heat

The energy to change phase is **enormous** compared with sensible heat. Water's latent heat of
vaporization is roughly **540 times** the energy to raise one gram by 1°C.

This is why phase change dominates thermal engineering — an incredibly dense way to store and
transport energy.

### Critical point

Above the critical temperature and pressure there is **no distinction between liquid and vapour**.
Supercritical fluids have liquid-like density and gas-like transport properties.

Modern ultra-supercritical steam plants operate above water's critical point: **374°C, 22.1 MPa**.

### Ideal gas law

    Pv = RT

Good at **low pressure and high temperature relative to critical**. For liquids and solids use
tabulated properties or incompressible approximations.

> **Applying the ideal gas law near saturation is a classic and serious error.** If the state is
> anywhere near the saturation line, reach for steam tables or a property library — not `Pv = RT`.

### Specific heats and γ

- **c_p > c_v always**, because constant-pressure heating must also do expansion work.
- For ideal gases, **c_p − c_v = R**.
- The ratio **γ = c_p/c_v** appears in every gas-cycle efficiency formula and determines how
  temperature changes during compression and expansion.

γ is the parameter that carries §3 into the gas cycles: it is what turns a compression ratio into a
temperature ratio, and therefore into an efficiency (§7–§11 →
`engines-otto-diesel-brayton-stirling-and-combined-cycles`).

## Quick reference

| Symbol | Meaning |
|---|---|
| U, u / h | Internal energy (total, specific) / enthalpy, h = u + Pv |
| Q, Q̇ / W, Ẇ / ṁ | Heat added to the system / work done by the system / mass flow, and their rates |
| S, S_gen / Ω | Entropy; entropy generated by a real process (S_gen ≥ 0) / microstate count (S = k ln Ω) |
| T_H, T_C | Absolute (Kelvin) hot- and cold-reservoir temperatures |
| x | Quality — vapour mass fraction in a two-phase mixture |
| c_p, c_v / γ / R | Specific heat at constant P, at constant v / γ = c_p/c_v / gas constant, c_p − c_v = R |

Full glossary entries for Carnot efficiency, enthalpy, entropy, exergy, isentropic processes and
quality live in §21–§23 → `engines-safety-and-reference`.
