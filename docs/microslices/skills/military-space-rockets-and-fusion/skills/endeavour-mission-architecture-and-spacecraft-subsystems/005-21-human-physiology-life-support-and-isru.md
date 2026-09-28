---
id: skill-21-human-physiology-life-support-and-isru-4840544458
purpose: 21 human physiology life support and isru
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-mission-architecture-and-spacecraft-subsystems/SKILL.md
requires: ["skill-20-attitude-control-in-space-propulsion-and-entry-descent-and-landing-39aad0ce65"]
links: ["skill-22-reliability-margins-and-the-failures-that-teach-them-6b6f5a2952"]
---

## §21 Human physiology, life support, and ISRU

> **A MARS MISSION EXCEEDS NASA'S RADIATION DOSE LIMIT.** NASA's current career limit is **600 mSv**
> effective dose. Estimates based on two 180-day transits plus ~500 days on the surface put the dose
> **near 1,000 mSv — above the limit.** This is not a margin problem to be engineered away at the
> edges; it is the mission, stated as a number.

Two sources, with opposite characters. **GCR** is continuous, high-energy heavy ions, hard to shield
because they produce secondary particle showers — the dominant **chronic** risk. **SPE** is sporadic,
proton-dominated and potentially **acute** — the reason a storm shelter is required. And a perverse
coupling: **solar maximum brings more SPE risk but suppresses GCR.** Solar minimum is
safer for acute events and worse for chronic dose. Surface dose measurements and regolith shielding
are at §29 → `endeavour-the-martian-environment-and-in-situ-resources`.

**Microgravity effects.** Bone loss ~1–1.5% per month in weight-bearing bone, not fully recovered
post-flight. Muscle atrophy, cardiovascular fluid shift, orthostatic intolerance.

**SANS (Spaceflight Associated Neuro-Ocular Syndrome)** is the constraint people underestimate —
optic disc oedema, posterior globe flattening, choroidal folds, hyperopic shifts up to 1.5
dioptres, affecting **roughly 70% of astronauts on missions over six months**, with no terrestrial
equivalent. **The underlying aetiology is not understood.** SANS is why "we've done a year on ISS, so
Mars is fine" does not follow — a round-trip Mars mission is 2–2.5 years, well beyond any flown
experience.

### ECLSS and closure

Functions: atmosphere pressure and composition, CO₂ removal, O₂ generation, water recovery, waste
management, humidity, fire detection, trace contaminant control.

On ISS: O₂ by water electrolysis; CO₂ removal by molecular sieve; a **Sabatier reactor (CO₂ + 4H₂ →
CH₄ + 2H₂O) recovering ~50% of the oxygen loop**; water recovery up to **~93%** from urine, sweat
and condensate.

**The gap between 93% and 98% is where the engineering difficulty lives.** At 5 kg/person/day of
consumables, a 1,000-day Mars mission for four people needs **20 tonnes open-loop**. Closure ratio is
the single biggest lever on crewed mission mass; what a permanent settlement needs beyond these
figures is at §32 → `endeavour-mars-mission-design-and-settlement`.

### ISRU — MOXIE proved the principle

MOXIE on Perseverance was the first demonstration of ISRU on another planet: a **15 kg** instrument
performing solid-oxide electrolysis of atmospheric CO₂ at **800 °C**, producing **12 g of oxygen per
hour at ≥98% purity**.

**The energy cost is the real constraint on scaling: ~30–70 kWh per kilogram of oxygen.** A Mars
ascent vehicle needs tens of tonnes of oxygen; at even 15 kWh/kg, 30 tonnes is **~450 MWh** — which
is a power plant, not an instrument, and is why surface fission keeps appearing in Mars
architectures. Both figures are the source's, and **15 kWh/kg is below the 30–70 kWh/kg range it
gives one sentence earlier** — not at its floor — so **~450 MWh understates the plant**: the same
30 tonnes at the stated range is **900–2,100 MWh**. Reworking it only strengthens the section's
point, because the power plant gets bigger. The full mine-to-methalox chain is at §30 →
`endeavour-the-martian-environment-and-in-situ-resources`.

**Why ISRU matters at all:** the rocket equation means propellant for the return trip, launched from
Earth, costs enormously more than its own mass at departure. **Making it at the destination breaks
the exponential.**
