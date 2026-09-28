---
id: skill-26-what-s-live-verified-august-2026-1edda19ada
purpose: 26 what s live verified august 2026
source: src/vibey_tools/skills/plugins/electromagnetism-and-electricity/skills/em-reference/SKILL.md
requires: []
links: ["skill-27-misconceptions-cec75af1c4"]
---

## §26. What's Live — verified August 2026

### 26.1 ⚠️ Superconductivity: a case study in extraordinary claims
**⚠️ Included because the physics is settled and the SOCIOLOGY is instructive — this is
the best recent example in physical science of how claims fail and how a field corrects.**

- **⚠️ The ambient-pressure record actually moved in 2026.** ⚠️ **A University of Houston
  team reported Tc of 151 K at ambient pressure in HgBa₂Ca₂Cu₃O₈₊δ via a "pressure quench"
  technique, published in PNAS** — **reported as the highest recorded at ambient pressure
  since superconductivity was discovered in 1911, against a plateau of around 133–135 K
  that had stood for decades.**
- **⚠️ The high-profile failures are worth knowing in detail, because the pattern
  repeats:**
```
⚠️ 2020  Dias et al., carbonaceous sulfur hydride, room-temperature
   superconductivity at ~267 GPa, published in Nature.
   ⚠️ Nature reportedly published over the objections of the majority
   of its own peer reviewers
⚠️ 2022  ⚠️ RETRACTED. Data artefacts identified externally, including
   magnetic susceptibility data that appeared copied between ranges
⚠️ 2023  Dias et al., N-doped lutetium hydride, room temperature at
   ~1 GPa, published in Nature. ⚠️ RETRACTED the same year at the
   request of most of its own authors
⚠️ 2023  LK-99 (copper-doped lead apatite) — ⚠️ viral, and conclusively
   explained within about two months: the levitation was ferromagnetic
   Cu₂S impurity, and the resistivity drop near 380 K matched a Cu₂S
   superionic phase transition. NOT the Meissner effect
```
> **⚠️ GOTCHA — the diagnostic that separates real from spurious, and it's simple.**
> ⚠️ **A drop in electrical resistance is NOT sufficient evidence of superconductivity —
> many things cause that, including phase transitions in impurity phases.** **⚠️ True
> superconductivity requires demonstration of the MEISSNER EFFECT (§22 → `em-conduction-semiconductors-grounding-and-electrical-safety`), verified by
> SQUID magnetometry.** **⚠️ Independent replication is the other half.**
> ⚠️ **Note how the field self-corrected: external groups reanalysed published figures,
> found artefacts, failed to replicate, and traced LK-99's anomalies to a specific
> impurity — largely in public and within months.**

**⚠️ Where the field actually stands, per a 2026 PNAS programmatic review**: ⚠️ **there are
no physical laws preventing room-temperature superconductivity — superconductivity is
described as "almost a generic property of nonmagnetic metals" — and the authors frame the
remaining work as two grand challenges: a PREDICTION challenge (prediction has advanced
dramatically but most predicted materials are not synthesizable) and an ENGINEERING
challenge.** ⚠️ **The 2026 landscape is characterized as a stark divide: hydride systems
that set Tc records but demand pressures exceeding 100 GPa, and ambient-pressure
candidates that remain unvalidated.**
**⚠️ Genuine ambient-pressure progress is happening in nickelates** — ⚠️ **reported
superconductivity onset above 60 K in ambient-pressure nickelate films, up from a previous
cap around 50 K, and around 96 K in nickelates under pressure.**
**⚠️ Sourcing note: this topic attracts hype aggregators; I anchored on PNAS, Nature's
retraction record, Science's reporting and arXiv preprints.**

### 26.2 ⚠️ Wide-bandgap semiconductors: §21's physics becoming infrastructure
**⚠️ The most consequential applied electromagnetics shift currently underway.**

- **⚠️ The physics driving it** (§21 → `em-conduction-semiconductors-grounding-and-electrical-safety`): ⚠️ **SiC is reported with roughly 10× the breakdown
  field and 3× the thermal conductivity of silicon**, **permitting thinner drift regions,
  much lower on-resistance at high voltage, higher junction temperatures and higher
  switching frequency.** ⚠️ **GaN's electron mobility is reported around 2000 cm²/V·s,
  roughly twice SiC's, giving sub-nanosecond switching.**
- **⚠️ The resulting division of labour is a physics consequence, not a marketing one:**
```
⚠️ SiC   ⚠️ high voltage, high temperature, high power. EV traction
   inverters — ⚠️ especially 800 V architectures, where bus voltages
   approach or exceed the rating limits of conventional silicon
   IGBTs — plus grid and solid-state transformers, 1200–3300 V classes
⚠️ GaN   ⚠️ the 100–650 V "golden zone." ⚠️ Sub-nanosecond switching
   shrinks magnetics and heatsinks dramatically, because passive
   component size scales inversely with frequency
⚠️ Si    ⚠️ still the volume foundation — reported at 52.72% of EV
   semiconductor technology share in 2025
```
- **⚠️ Adoption figures, with the caveat that market-research numbers vary widely:**
  ⚠️ **SiC went into a reported 1.17 million EV traction inverters in Q1 2026, or 17.2% of
  everything shipped (TrendForce); ⚠️ one source reports SiC inverter share rising from
  under 8% of global EV production in 2021 to 24% by 2026, with a projection of 55% by
  2030; ⚠️ another puts SiC above 50% penetration in PREMIUM vehicles specifically.**
  ⚠️ **Grid and HVDC penetration is reported below 5%, constrained by device voltage
  ratings and evolving standards.**
- **⚠️ Efficiency claims**: ⚠️ **reported around 10% better inverter efficiency versus
  silicon, and claims of up to 70% lower energy losses** — **⚠️ treat the higher figure as
  vendor-adjacent and application-specific.**

> **⚠️ GOTCHA — the two technologies stopped being competitors, and hybrid design is now
> the state of the art.** ⚠️ **A reported 12 kW AI server power supply reference design
> mixes silicon, SiC and GaN in one unit — GaN on the high-frequency stages, SiC on the
> high-stress ones — at better than 99% PFC efficiency.** **⚠️ A single bidirectional GaN
> switch is reported replacing a four-MOSFET full bridge.**
> **⚠️ The AI data centre is now a major driver alongside EVs, pushing 800 VDC
> architectures for exactly §14 → `em-magnetism-induction-and-transformers`'s reason: at fixed power, higher voltage means lower
> current, and I²R losses fall as the square.**

**⚠️ Sourcing note: this section draws heavily on market-research and trade publications
with commercial interests, and the market-size figures disagree with each other by wide
margins.** ⚠️ **The PHYSICS — breakdown field, mobility, and the resulting
voltage-versus-frequency division of labour — is solid and checkable from §21 → `em-conduction-semiconductors-grounding-and-electrical-safety`; the
adoption percentages are directional only.**

---
