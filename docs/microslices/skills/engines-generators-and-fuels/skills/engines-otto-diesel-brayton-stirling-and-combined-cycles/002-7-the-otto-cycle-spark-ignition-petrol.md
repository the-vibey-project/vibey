---
id: skill-7-the-otto-cycle-spark-ignition-petrol-2dbdd53aa8
purpose: 7 the otto cycle spark ignition petrol
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-otto-diesel-brayton-stirling-and-combined-cycles/SKILL.md
requires: ["skill-the-universal-design-principle-923b2c19ec"]
links: ["skill-8-the-diesel-cycle-compression-ignition-ef289f5eb4"]
---

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
