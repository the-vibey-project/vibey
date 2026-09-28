---
id: skill-1-the-four-laws-of-thermodynamics-14c635f97b
purpose: 1 the four laws of thermodynamics
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-thermodynamics-and-the-carnot-ceiling/SKILL.md
requires: []
links: ["skill-2-the-carnot-efficiency-ceiling-419b437e89"]
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
