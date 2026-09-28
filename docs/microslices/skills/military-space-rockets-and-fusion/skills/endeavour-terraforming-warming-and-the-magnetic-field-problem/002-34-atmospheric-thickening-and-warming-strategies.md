---
id: skill-34-atmospheric-thickening-and-warming-strategies-361d0e1a40
purpose: 34 atmospheric thickening and warming strategies
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-terraforming-warming-and-the-magnetic-field-problem/SKILL.md
requires: ["skill-33-terraforming-theory-and-the-three-habitability-thresholds-9dc6425ee4"]
links: ["skill-35-the-magnetic-field-problem-9033dda042"]
---

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
