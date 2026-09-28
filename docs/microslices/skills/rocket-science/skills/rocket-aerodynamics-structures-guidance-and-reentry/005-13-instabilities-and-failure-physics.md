---
id: skill-13-instabilities-and-failure-physics-33fd2fd295
purpose: 13 instabilities and failure physics
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-aerodynamics-structures-guidance-and-reentry/SKILL.md
requires: ["skill-12-reentry-physics-cc017e9e2d"]
links: []
---

## §13. Instabilities and Failure Physics

**13.1 Combustion instability** — acoustic modes of the chamber coupling with the
combustion process. **Longitudinal (chug, ~100s Hz), tangential and radial (screech,
kHz).** ⚠️ **Tangential modes are the destructive ones — they can destroy an engine in
milliseconds.** Rayleigh's criterion: instability grows when heat release is in phase with
pressure oscillation. **Fixes: acoustic baffles, Helmholtz/quarter-wave cavities, injector
redesign.** ⚠️ **The F-1 required ~2,000 full-scale tests and years of injector iteration**;
it is still not a fully predictive discipline.

**13.2 POGO** — §10.

**13.3 Water hammer and priming shock** — filling a dry line with propellant produces
pressure spikes far above steady-state.

**13.4 Stage separation** — ⚠️ **brief, violent, essentially untestable at full scale on
the ground.** Recontact, plume impingement, and tip-off rates. **Hot staging** (igniting
the upper stage before separation) removes ullage-settling requirements but requires an
interstage that survives the plume.

**13.5 Reliability statistics** — ⚠️ **new vehicles historically succeed on first flight
roughly 50% of the time**; mature vehicles reach 95–98%. **Bayesian reliability growth
models** are the standard analytical treatment. **There is no launch vehicle approaching
aviation reliability, and the physics of §1 → `rocket-equation-nozzles-and-combustion` — thin margins, no redundancy in structure,
single-use hardware — is why.**

**13.6 The organizational failure mode** — ⚠️ **normalization of deviance**: an off-nominal
observation recurs without consequence and is reclassified as acceptable. **Challenger
(O-ring blow-by) and Columbia (foam shedding) both followed this pattern**, and both
accident boards concluded the organizational cause dominated the technical one.
