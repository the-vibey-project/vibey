---
name: endeavour-terraforming-warming-and-the-magnetic-field-problem
description: "Use when you need to know what terraforming Mars would actually require — which habitability threshold a proposal is aiming at, how much gas has to be added and where it could come from, which warming method is physically plausible and on what timescale, or whether the missing magnetic field is a blocker. Covers the Armstrong limit, plant survival and human breathability, the mass problem, polar and regolith CO₂, manufactured super-greenhouse gases, volatile import, orbital mirrors and albedo reduction, and the unsolved magnetic field problem. Part 10 of 12 of the Military Science, Rockets, Space, Fusion, and Mars reference."
---

# Terraforming: Thresholds, Atmosphere, Warming, and the Magnetic Field Problem

> **Part 10 of 12** of the *Military Science, Rockets, Space, Fusion, and Mars* reference (plugin
> `military-space-rockets-and-fusion`), covering §33–§35 — what terraforming means and the three
> habitability thresholds, where the gas would come from and how the planet would be warmed, and the
> magnetic field problem. Sibling skills:
> `endeavour-military-theory-levels-of-war-and-deterrence` (§1–§3 — the theoretical canon, the levels of war, deterrence and nuclear strategy),
> `endeavour-logistics-doctrine-modern-conflict-and-the-law` (§4–§6 — force structure and logistics, doctrine and procurement, modern conflict, and the law of armed conflict),
> `endeavour-rocket-equation-nozzles-engines-and-propellants` (§7–§10 — Tsiolkovsky and staging, nozzle thermodynamics, turbomachinery and cooling, propellants),
> `endeavour-orbits-ascent-structures-and-reentry` (§11–§16 — orbital mechanics, the ascent budget, loads and structures, guidance, reentry, failure physics),
> `endeavour-mission-architecture-and-spacecraft-subsystems` (§17–§22 — mission architecture, power and thermal, comms and navigation, EDL, human physiology, reliability),
> `endeavour-fusion-physics-confinement-and-engineering` (§23–§25 — fusion reactions and the Lawson criterion, confinement, the engineering reality and the nuclear background),
> `endeavour-satellites-flight-software-and-instruments` (§26–§28 — satellite design and orbits, flight software and FDIR, instrumentation and planetary protection),
> `endeavour-the-martian-environment-and-in-situ-resources` (§29–§30 — Mars as engineering parameters, and the water, CO₂ and regolith resource base),
> `endeavour-mars-mission-design-and-settlement` (§31–§32 — windows and EDL, surface power, habitats, ECLSS closure and the psychological challenge),
> `endeavour-ecopoiesis-oxygen-timelines-and-ethics` (§36–§38 — ecopoiesis, the oxygen problem, the phase timelines, paraterraforming, ethics and Venus),
> `endeavour-reference` (§39–§40 — the glossary across all six parts, and the further reading),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. This section covers the *engineering* phase of terraforming; the
> biological phase, the timelines and the ethics are §36–§38 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics`.

Mars is the only body in the solar system where terraforming is physically plausible. The physics is
real and the engineering is genuinely hard. Everything below stays at the level the source pitches
it: what each step would require, what the numbers are, and — for each proposal — how plausible its
own advocates think it is. Where a figure is a range, the range is the answer.

---

## §33 Terraforming theory and the three habitability thresholds

**Terraforming** is the deliberate modification of a planet's environment to make it habitable for
Earth life **without life support** — breathing the air, standing on the surface, liquid water in the
open.

The concept moved from science fiction to semi-serious technical analysis in the **1960s–70s
(Sagan, Averner)**, received its first rigorous treatment by **McKay, Toon, and Kasting in 1991**,
and has been refined by **Zubrin, McKay**, and others since.

### Why Mars is the only plausible candidate

| Body | Why not |
|---|---|
| The Moon | Too small and lacks volatiles |
| Venus | Too hot and has too much atmosphere (§38 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics`) |
| Mercury | Too close to the Sun |
| Outer planet moons | Abundant water, but receive too little sunlight and are too cold |
| **Mars** | Marginally too cold, too little atmosphere, no magnetic field — **but** it has the raw materials (CO₂, water, nitrogen) and enough gravity and sunlight that the gap is bridgeable, at least in principle |

### What "habitable" means — the three thresholds

Three separate thresholds matter, and **confusing them is the common error in terraforming
discussions**. They are not points on one scale you pass through cheaply; the third is orders of
magnitude harder than the first.

| Threshold | Pressure | What clearing it buys | What it still does not buy |
|---|---|---|---|
| 1. Armstrong limit | ~6.3 kPa | Surface work with an **oxygen mask** instead of a full pressure suit | A breathable atmosphere — it is still nearly pure CO₂ |
| 2. Plant survival | ~10–25 kPa with appropriate composition | Outdoor biological experiments; agriculture in pressurized greenhouses, or open fields with genetic engineering for low-pressure tolerance | Anything a human can breathe |
| 3. Human breathability | ~50–100 kPa with ~21% O₂ | Full terraforming — walking outside without a mask | Nothing: this is the end state, and the hardest threshold by orders of magnitude |

**1. The Armstrong limit (~6.3 kPa).** Below this pressure, water boils at human body temperature
(37 °C). You cannot survive even with an oxygen mask — your saliva, tears and alveolar fluids boil.
Mars at **610 Pa** (§29 → `endeavour-the-martian-environment-and-in-situ-resources`) is below it.
Raising pressure above the Armstrong limit is the first terraforming goal.

**2. Plant survival (~10–25 kPa with appropriate composition).** Some microbes and lichens survive
at very low pressures with CO₂ and water. **Higher plants need ~10 kPa total pressure with at least
0.1–0.2 kPa O₂ and sufficient CO₂.**

**3. Human breathability (~50–100 kPa with ~21% O₂).** Requires not just pressure but the right
composition: enough oxygen, **CO₂ not above ~1% partial pressure** (toxic above that), and a **buffer
gas (nitrogen)**. Hardest by orders of magnitude, because it requires generating enormous quantities
of oxygen and nitrogen — and the oxygen half of that is unsolved (§36 →
`endeavour-ecopoiesis-oxygen-timelines-and-ethics`).

> **THE MASS PROBLEM, STATED PLAINLY.** To raise Mars's atmospheric pressure to Earth's (101 kPa),
> you need to add roughly **2.5×10¹⁶ kg** of gas — about **200,000 times** the current atmosphere.
> Even reaching the Armstrong limit (6.3 kPa) requires roughly **2.5×10¹⁴ kg**, about **400×** the
> current atmosphere. The current Martian atmosphere weighs about **2.5×10¹³ kg**. Where does this
> gas come from? That is the central question of terraforming, and the answer determines whether it
> is physically plausible on any timescale.
>
> **The source's stated multiples do not reconcile with its own stated masses**, and all four
> figures are carried here as it gives them rather than quietly recomputed. Against the
> **2.5×10¹³ kg** current atmosphere, **2.5×10¹⁴ kg** is **10×** and **2.5×10¹⁶ kg** is **1,000×**,
> not the 400× and 200,000× stated; taking the pressure ratios instead, 6.3 kPa is **10.3×** and
> 101 kPa is **166×** the 610 Pa now. The mass for the Armstrong limit is consistent with the
> pressure ratio and only its multiple is off; the Earth-pressure line does not reconcile either
> way. **What survives all three readings is the shape of the problem**: even the most modest of the
> stated figures — 10× the present atmosphere, merely to clear the Armstrong limit — is a
> planetary-scale industrial programme, and Earth pressure is orders of magnitude beyond that.

## §34 Atmospheric thickening and warming strategies

### Where the gas comes from — five options and their assessments

| Option | Inventory | The source's own assessment |
|---|---|---|
| 1. Polar CO₂ caps | South polar residual cap ~10¹³–10¹⁴ kg of CO₂ ice | Most frequently proposed first step; buys only a factor of **3–8** in pressure |
| 2. Regolith CO₂ | Uncertain — from modest (comparable to the caps) to tens of millibars equivalent | One of the **largest uncertainties** in terraforming scenarios |
| 3. Manufactured super-greenhouse gases | Feedstock (fluorine, carbon) available on Mars | **The most physically plausible warming method** |
| 4. Importing volatiles | Titan alone holds ~10¹⁸ kg of nitrogen | **Least plausible near-term option**, though not forbidden by physics |
| 5. Deep-interior outgassing | — | **Not a serious near-term proposal** |

**Option 1 — subliming the polar CO₂ caps.** Mars's south polar residual cap contains a large CO₂
ice deposit, estimated at roughly **10¹³ to 10¹⁴ kg**, potentially enough to roughly **double** the
atmosphere if fully sublimed; the north polar cap is mostly water ice with a seasonal CO₂ frost. This
is the most frequently proposed first step because it uses **energy as the only input** and the
material is already on Mars in concentrated form. The method: warm the poles, CO₂ sublimes,
atmospheric pressure rises, the greenhouse effect of the added CO₂ warms the planet further,
releasing more CO₂ from the regolith — **a positive feedback loop**. The open question is whether the
feedback is strong enough to run to completion or **stalls partway**. Current estimates suggest the
readily available CO₂ from the caps and adsorbed in the regolith could raise pressure to perhaps
**2–5 kPa** — above the Armstrong limit in the optimistic case, but well short of plant-survival or
human-breathability thresholds. This is the "easy" terraforming step, and it only gets you a factor
of **3–8** in pressure.

**Option 2 — CO₂ from the regolith.** Significant CO₂ is adsorbed onto regolith particles and
trapped in subsurface **clathrate hydrates**. Estimates of the total are uncertain and range widely,
from modest (comparable to the caps) to large (potentially **tens of millibars equivalent**).
Releasing it requires heating the regolith, which requires warming the planet substantially. The
coupling between regolith CO₂ release and the greenhouse feedback is one of the largest uncertainties
in terraforming scenarios.

**Option 3 — manufacturing super-greenhouse gases.** This is **Zubrin and McKay's key insight: you
do not need to warm Mars with CO₂ alone.** You can manufacture gases with vastly higher greenhouse
warming potential — **perfluorocarbons (CF₄, C₂F₆, C₃F₈)**, **sulfur hexafluoride (SF₆)**, or
**chlorofluorocarbons (CFCs)**. These are **thousands to tens of thousands of times more potent** as
greenhouse gases than CO₂, and they are chemically stable in the Martian atmosphere — no UV breakdown,
because there is no ozone layer to speak of and the gases are designed to be photostable.
Manufacturing them requires **fluorine and carbon (both available on Mars)** plus industrial capacity
— which means surface power at industrial scale (§31 → `endeavour-mars-mission-design-and-settlement`).
**A sustained production of ~10⁸ kg/year of PFCs could warm Mars by tens of degrees over decades to
centuries.** This is the most physically plausible warming method: it requires industrial
infrastructure but **not physics beyond what we know**.

**Option 4 — importing volatiles.** Redirecting volatile-rich asteroids or comets to impact Mars, or
importing nitrogen from the outer solar system. **Titan's atmosphere is mostly N₂ at 147 kPa and
holds roughly 10¹⁸ kg of nitrogen, far more than Mars needs** — relevant because Mars has very little
nitrogen and Earth-like life needs it (§30 → `endeavour-the-martian-environment-and-in-situ-resources`).
The energy cost of moving material from the outer solar system to Mars is enormous, and the precision
required to deliver it to Mars rather than into the Sun or elsewhere is challenging. Least plausible
near-term option; not forbidden by physics.

**Option 5 — outgassing from the deep interior.** Mars is geologically inactive: its core has
solidified and volcanic outgassing has stopped. Inducing volcanism to release trapped volatiles
requires **energy on a planetary scale** and is not a serious near-term proposal.

### Warming: the targets

Current Mars average temperature is **−63 °C**. The targets:

| Goal | Mean temperature needed |
|---|---|
| Liquid water at the surface | roughly **−10 °C to 0 °C** (transient liquid water is possible lower with perchlorate brines, but a water cycle needs **bulk melting**) |
| Full terraforming | **+5 to +15 °C** |

**Super-greenhouse gases** are the most efficient method. The feedback loop: **PFCs warm the planet →
CO₂ sublimes from caps and regolith → added CO₂ warms further → more CO₂ released.** If the feedback
runs to completion, Mars could reach a **stable warm state at perhaps 20–50 kPa of CO₂** — still not
breathable (too much CO₂, no O₂), but **warm enough for liquid water and above the Armstrong limit**.
The timescale for this phase: **optimistically 100–500 years** of continuous industrial PFC
production; **more conservatively 1,000–10,000 years**. Both ends of that range are the honest
answer — this is Phase 1 of the four-phase timeline in §37 →
`endeavour-ecopoiesis-oxygen-timelines-and-ethics`, and the phase whose optimistic end is defensible.

**Orbital mirrors.** Large, thin mirrors in orbit (or at the L1 point) reflecting additional sunlight
onto the polar caps. A mirror of **~200 km diameter** could provide enough extra insolation to warm
the south polar cap significantly. It would be made of **ultra-thin aluminized film a few micrometres
thick** and could be relatively low mass. This is engineering on a scale we have not attempted, but
it is **not physics-breaking**. Zubrin estimated **~200 kW of microwave beaming** from solar power
satellites could also sublime polar CO₂.

**Darkening the poles.** Covering polar ice with dark material (dust, soot, engineered materials)
reduces albedo and increases absorption — something **Mars already does naturally during dust
storms**. The low albedo of dark material could locally raise temperatures by **tens of degrees**,
and the material requirement is modest by terraforming standards: **a few centimetres of dark dust
over the polar caps**.

**Reducing planetary albedo.** The same approach planet-wide — darkening surface materials to absorb
more sunlight. Less targeted than polar darkening, and harder to maintain against dust storms that
redistribute bright dust (§29 → `endeavour-the-martian-environment-and-in-situ-resources`).

> **THE FAINT YOUNG SUN PROBLEM — IN REVERSE.** When Mars had liquid water 3–4 billion years ago,
> the Sun was **20–30% dimmer** than today. Mars was warm then because it had a thicker atmosphere
> (**possibly 1–10 bar of CO₂**) and possibly a magnetic field. The Sun is brighter now, which helps
> — but Mars has lost most of its atmosphere and its magnetic field. **The fact that Mars was once
> warm with a thicker atmosphere is the strongest evidence that warming is possible with enough
> atmospheric mass.** The open question is whether enough of the original CO₂ remains accessible —
> in the caps, the regolith, and as carbonates — to recreate a significant greenhouse effect.

## §35 The magnetic field problem

Mars has no global magnetic field: the dynamo died roughly 4 billion years ago, leaving only weak
patchy crustal fields (§29 → `endeavour-the-martian-environment-and-in-situ-resources`). **This is an
open problem with no demonstrated solution**, and the honest position below is not that it has been
solved but that it may not need solving.

Two consequences for terraforming:

- **Atmospheric loss.** The solar wind strips atmosphere at roughly **1–2 kg/s**, adding up to
  **~10⁸–10⁹ kg per century** — slow on human timescales, significant on geological ones.
- **Surface radiation.** Unshielded GCR and SPE reach the surface (§21 →
  `endeavour-mission-architecture-and-spacecraft-subsystems` for what that dose does to people).

For a *thickened* atmosphere, the loss is negligible on biological timescales: **even a 1 bar
atmosphere would last millions of years without a magnetic field.** The radiation is the more
immediately relevant consequence — and a thick CO₂ atmosphere at **100+ kPa provides substantial
shielding by itself**, its **atmospheric column mass equivalent to about 10 m of regolith**. So once
the atmosphere is thick enough, **the radiation problem largely solves itself without a magnetic
field.** The field therefore matters more for maintaining the atmosphere over millions of years, and
for protecting the early thin atmosphere during the warming phase.

### The three proposed responses

**Artificial magnetosphere at the Sun-Mars L1 point.** A dipole field generator positioned at L1,
roughly **1 million km sunward** of Mars, could deflect the solar wind before it reaches Mars,
creating a magnetotail that shields the atmosphere. The concept — proposed by **NASA's Green and
colleagues** — would require a very large superconducting dipole or a plasma-based field:
**engineering we cannot currently do, but that is not physics-breaking.** The power requirement is
modest, because the field only needs to deflect the solar wind, not match Earth's magnetosphere.

**Surface magnetic shielding.** Local magnetic fields over settlements or critical areas. Feasible
with superconducting coils, but it **protects only the immediate area, not the atmosphere** — a
habitat measure, not a planetary one, and regolith berming already does that job with free material
(§32 → `endeavour-mars-mission-design-and-settlement`).

**Accept the loss.** If you are thickening the atmosphere on a 1,000-year timescale, the
**10⁸–10⁹ kg/century** loss is negligible compared with the **10¹³–10¹⁶ kg** you are adding. The
atmosphere will persist for millions of years regardless. **This is the most pragmatic position — a
magnetic field is nice to have but not strictly necessary for terraforming on any practical
timescale.**

## Quick reference

| Quantity | Value |
|---|---|
| Current Mars surface pressure / atmospheric mass | 610 Pa / ~2.5×10¹³ kg |
| Armstrong limit / gas to reach it | ~6.3 kPa / ~2.5×10¹⁴ kg (~400× current — the source's multiple; its own masses give 10×) |
| Plant survival / human breathability | ~10–25 kPa (≥0.1–0.2 kPa O₂) / ~50–100 kPa at ~21% O₂, CO₂ < ~1% |
| Earth-pressure target / gas to reach it | 101 kPa / ~2.5×10¹⁶ kg (~200,000× current — the source's multiple; its own masses give 1,000×) |
| South polar CO₂ ice deposit | ~10¹³–10¹⁴ kg — roughly doubles the atmosphere if fully sublimed |
| Caps + adsorbed regolith, realistically | 2–5 kPa — a factor of 3–8 |
| PFC production rate that warms by tens of degrees | ~10⁸ kg/year, over decades to centuries |
| Titan nitrogen inventory | ~10¹⁸ kg (atmosphere mostly N₂ at 147 kPa) |
| Mean temperature: now / liquid water / full terraforming | −63 °C / −10 to 0 °C / +5 to +15 °C |
| Stable warm end state of the PFC→CO₂ feedback | perhaps 20–50 kPa CO₂ — unbreathable |
| Phase 1 timescale | 100–500 years optimistic; 1,000–10,000 years conservative |
| Orbital mirror / microwave beaming | ~200 km diameter, aluminized film a few µm thick / ~200 kW (Zubrin) |
| Solar wind atmospheric loss | 1–2 kg/s ≈ 10⁸–10⁹ kg/century, against 10¹³–10¹⁶ kg added |
| Shielding of a 100+ kPa CO₂ atmosphere | equivalent to ~10 m of regolith |

Glossary entries for the **Armstrong limit**, **terraforming**, **super-greenhouse gases**,
**ecopoiesis** and **paraterraforming** live in §39–§40 → `endeavour-reference`.
