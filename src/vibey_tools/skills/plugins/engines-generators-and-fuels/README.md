# Engines, Generators, and Fuel Sources Plugin

Heat engines, the generators they turn, and the fuels that feed them — the physics that bounds
every one of them, the cycles that chase that bound, and what you would actually build.

One reference, split into 7 skills, so a task loads only the part it needs.

**The single idea that organizes the whole set:**

> Every improvement to every engine cycle is the same idea in different clothes: move heat addition
> to a **higher** average temperature, or heat rejection to a **lower** one. Superheating, reheating,
> regeneration, intercooling, combined cycles, higher compression ratios — all of them serve that one
> goal. There is no other lever.

That is the Carnot ceiling, `η = 1 − T_C/T_H`, restated as engineering practice. It is also why the
binding constraint on engine efficiency is usually a **materials** problem — finding metals that
survive a higher T_H — rather than a thermodynamics one.

Reference, not tutorial. The laws, cycles and equations here are durable: they do not expire.
Efficiency figures for *current* plant and practice do drift, and are marked where they appear.

## The skills

| Skill | Sections | Covers |
|---|---|---|
| `engines-thermodynamics-and-the-carnot-ceiling` | §1–§3 | The four laws, the steady-flow energy equation and why enthalpy exists, entropy as energy unavailability, the Carnot ceiling, and working-fluid phase behaviour |
| `engines-rankine-steam-engines-and-turbines` | §4–§6 | The Rankine cycle and its five improvements, reciprocating engines (cut-off, compounding, uniflow), turbines (impulse vs reaction, Euler, specific speed), and practical builds from model to 10 kW |
| `engines-otto-diesel-brayton-stirling-and-combined-cycles` | §7–§11 | Otto and knock, Diesel and its aftertreatment, Brayton and the back-work ratio, Stirling, and the combined cycle |
| `engines-generators-and-house-power` | §12–§14 | Faraday to back-EMF, the four generator types, AC vs DC, and sizing / building / switching a house power system |
| `engines-fuels-and-combustion` | §15–§17 | Every fuel with its energy density and matching engine, the non-combustion sources, HHV vs LHV, and combustion chemistry |
| `engines-rebuilding-engines-materials-and-tolerances` | §18–§20 | Engine anatomy, the five-step rebuild, ECU fuel trims, forced induction, materials, manufacturing processes and tolerance thinking |
| `engines-safety-and-reference` | §21–§23 | The six things that kill, the glossary, and the books that actually teach this |

Section numbers are **shared across the set**: a reference written as `§N → skill` points into that
sibling skill.

## Safety

This pack describes machines that kill people. Boiler explosions were the leading industrial killer
of the 19th century; carbon monoxide is colourless and odourless and is produced by every engine;
generator output is mains voltage; steam at 10 bar is invisible at the leak point and causes
instantaneous third-degree burns.

`engines-safety-and-reference` (§21) carries the full set of warnings and prevention rules, and the
build sections repeat the ones that bear on them. **Never cap or bypass a safety valve. Never run an
engine indoors. Never backfeed a generator through a wall outlet.** None of this is a substitute for
a boiler designed to code, a certified relief valve, a qualified inspection, or an electrician.

## Neighbours in this marketplace

Several plugins cover adjacent ground as **disciplines** rather than as this pack's
engine-by-engine walk:

- `thermodynamics-fluid-mechanics` — the academic treatment of cycles, heat transfer and flow
- `power-engineering` — the grid side: generation at scale, protection, SCADA and markets
- `electrical-engineering` and `electromagnetism-and-electricity` — the machine and field theory
  under §12
- `manufacturing-mechanical-engineering-for-software-devs` — process families and DFM under §20
- `automotive-software` — the electronic and network side of the vehicle, where §19 stops

Use this pack when the question is about **a specific engine, generator or fuel**: which cycle, which
fuel, what efficiency to expect, what to build, and what will hurt you.
