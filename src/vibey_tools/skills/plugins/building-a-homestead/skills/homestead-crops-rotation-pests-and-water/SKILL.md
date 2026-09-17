---
name: homestead-crops-rotation-pests-and-water
description: "Use when setting planting dates and seeding depth, designing a rotation, deciding whether a pest is worth spraying, choosing or scheduling irrigation, or comparing farming systems before committing to one. Covers growing degree days, cover crops, the tillage spectrum, IPM economic thresholds and resistance management, irrigation efficiency and salinity, and an honest read on conventional, organic, no-till, regenerative and agroforestry systems. Part 7 of the Building a Homestead reference."
---

# Crops, Rotation, Pests and Water

> **Part 7 of 8** of the *Building a Homestead* reference (plugin `building-a-homestead`), covering
> §17–§22 — crop production, why rotation does several jobs at once, IPM, irrigation methods, and an honest look at farming systems. Sibling skills:
> `homestead-site-structure-and-materials` (§1–§3 — ground investigation, solar orientation, the gravity and lateral systems, and choosing a structural material),
> `homestead-envelope-and-building-physics` (§4–§5 — the four control layers in priority order, drying potential, and the materials that make them up),
> `homestead-services-sequencing-and-codes` (§6–§7 — MEP, fire safety, the order the trades run in, permitting, and the house build checklist),
> `homestead-livestock-digestion-nutrition-and-species` (§8–§10 — why cattle are different, the nutrient requirements that follow, and picking a species),
> `homestead-livestock-housing-health-and-grazing` (§11–§14 — fencing and shelter, biosecurity, reproduction, and the grazing systems with their trade-offs),
> `homestead-soil-and-fertility` (§15–§16 — what soil actually is and how to feed it without wrecking it),
> `homestead-reference` (§23–§24 — the terms of art across all three domains, and the books that actually teach this),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Building work is governed by local codes and inspection, and livestock by
> local animal-health rules; this reference tells you what to design for and what to ask, not what
> your jurisdiction permits.

Everything in crop farming is a system with feedback — maximize yield and lose soil, maximize
nitrogen and leach it into the water table, maximize monoculture and invite pest resistance. The soil
and its microbial communities are the engine (§15 → `homestead-soil-and-fertility`); your job is
managing that engine.

## §17 Crop production

**Growing degree days (GDD).** Heat accumulation predicts crop development far better than
calendar dates.

```
GDD for one day = max(0, (daily max temp + daily min temp) / 2 − base temperature)
accumulated GDD = the sum of those daily values over the season
```

Base temperature varies by crop: typically **50°F / 10°C for warm-season crops**, **40°F / 4°C for
cool-season crops**.

**The `max(0, …)` is not decoration.** A day whose mean sits below the base temperature contributes
**zero**, not a negative number. Growth stalls on a cold day; it does not un-happen. Let the daily
term go negative and the accumulated total falls, which moves predicted maturity and harvest dates
*backwards* as the season goes on — a nonsense answer that looks like arithmetic. Many crop models
also cap the daily maximum at a crop-specific upper threshold before averaging, because development
stops gaining above it; the standard method for corn uses a 50°F base with an 86°F cap. Use
accumulated GDD to predict planting dates, maturity, and harvest timing.

**Planting decisions.**

| Decision | What governs it |
|---|---|
| Planting date | After last frost for warm-season crops; before last frost or early spring for cool-season crops |
| Plant population | Seeds per acre, or spacing within rows |
| Row spacing | Narrower rows canopy faster and suppress weeds, but may restrict equipment access |
| Seeding depth | Typically **2–3× seed diameter** |

**Cover crops** provide erosion control, nitrogen scavenging or fixation (legumes), organic matter,
weed suppression, and compaction relief. The honest caveat: **they cost money and water, and in dry
regions the water cost can exceed the benefit.** Termination timing is the main management variable —
terminate too early and you lose the benefits; too late and you deplete soil moisture for the cash
crop.

**The tillage spectrum.**

```
Conventional            → reduced          → strip-till        → no-till
(moldboard plow +         (chisel plow,      (only the row        (plant directly
 secondary tillage)        disk)              is tilled)           into residue)
```

No-till conserves soil and moisture, builds organic matter over time, and shifts weed control toward
herbicides. It creates different disease pressure and requires different planting equipment (a no-till
drill, or a planter with row cleaners). **It is a tradeoff, not a free win — but the soil benefits are
real and compound over years.**

## §18 Crop rotation — multiple jobs at once

Rotation is not one intervention. It does five jobs simultaneously:

| Job | Mechanism |
|---|---|
| Breaks pest and disease cycles | Pathogens that survive in soil or residue lose their host when a different crop is planted |
| Varies rooting depth | Deep-rooted crops like alfalfa bring nutrients up from the subsoil |
| Manages nitrogen | Legumes fix atmospheric N, contributing **50–200 lbs/acre** depending on the legume and conditions |
| Spreads labor and risk | Different crops are planted and harvested at different times |
| Reduces weed selection pressure | Different crops favor different weeds, and allow different weed control methods |

> **CONTINUOUS MONOCULTURE WORKS ONLY WITH ESCALATING INPUTS**
>
> Continuous corn or continuous wheat produces diminishing returns as pest pressure builds, soil
> organic matter declines, and nutrient removal is one-sided. The system is kept functional with
> escalating chemical inputs — more insecticide, more fungicide, more nitrogen. **The escalation is the
> tell that the system is degrading.** Rotation is not optional for long-term productivity; it is the
> foundation.

**A simple homestead rotation:**

| Year | Crop group | Notes |
|---|---|---|
| 1 | Heavy feeder | Corn, tomatoes, brassicas — with compost/manure applied |
| 2 | Light feeder / root crop | Carrots, beets, onions, garlic |
| 3 | Legume | Beans, peas, clover cover crop — to fix nitrogen |
| 4 | Soil-building cover crop or green manure | Oats, rye, vetch, clover |

Then repeat. **For field crops at scale:** corn → soybeans → small grain with cover crop, or similar
3–4 year rotations.

## §19 Integrated pest management (IPM)

IPM is **a decision framework, not an input list.** Its core insight is the **economic threshold** —
the pest density at which the cost of control equals the value of damage prevented. Below the
threshold, spraying loses money. Above it, not spraying loses money. **The threshold is not zero** —
some pest presence is normal and economically irrelevant.

**The IPM process:**

1. **Monitor.** Scout regularly, count pests, identify them correctly. *Most of IPM is looking.* Use
   pheromone traps, sticky traps, and visual inspection. Know your beneficial insects so you don't
   mistake them for pests.
2. **Identify correctly.** Misidentification wastes the entire intervention. Many beneficial insects
   look superficially like pests. Many diseases look similar but require different management.
3. **Threshold.** Is action economically justified? Compare the cost of control (materials, labor,
   equipment) against the value of damage prevented. For home gardens and homesteads the threshold may
   be lower — you value the produce more than its market price — but the principle still applies.
4. **Act, least-disruptive first.**
   - **Cultural** — rotation, planting date, resistant varieties, sanitation →
   - **Biological** — predators, parasitoids, beneficial insects, Bt →
   - **Mechanical** — hand-picking, traps, barriers, cultivation →
   - **Chemical** — pesticides, used as a last resort, targeted to the pest, timed to minimize
     beneficial impact.
5. **Evaluate.** Did it work? Adjust for next time.

> **PROPHYLACTIC CALENDAR SPRAYING IS THE ANTI-PATTERN**
>
> Spraying on a schedule regardless of pest presence costs money, kills natural enemies (causing
> secondary pest outbreaks — the pest you didn't have becomes the pest you do), and accelerates
> resistance. **Resistance management:** rotate modes of action (IRAC/FRAC group numbers on pesticide
> labels), use refugia (leave unsprayed areas so susceptible pests survive to dilute resistance), and
> avoid sub-lethal doses. **Resistance is permanent — once a pest population is resistant to a
> chemical, that chemical is lost to you forever.**

Refugia works the same way in livestock parasite management (§12 →
`homestead-livestock-housing-health-and-grazing`).

## §20 Water and irrigation

| Method | Efficiency | Cost | Best For | Limitations |
|---|---|---|---|---|
| Surface/flood | Low (40–60%) | Low capital | Level ground, rice, pasture | Uneven distribution, high evaporation, runoff |
| Sprinkler/pivot | Moderate (70–80%) | Moderate | Most field crops, varied terrain | Evaporation and wind loss, energy cost |
| Drip/micro | High (85–95%) | High capital | Vegetables, orchards, high-value crops | Clogging and rodent damage are the real failure modes |

**Scheduling beats hardware.** Soil moisture sensors, evapotranspiration-based scheduling, or a simple
checkbook water balance all beat "irrigate on Tuesdays." Irrigate based on what the crop needs, not on
the calendar. Over-irrigation wastes water, leaches nutrients, and promotes disease; under-irrigation
stresses the crop and reduces yield.

**Salinity.** Irrigation adds salt. Without **leaching** — applying extra water to flush salts below
the root zone — and drainage, salt accumulates and eventually ends agriculture. This has destroyed
irrigated civilizations historically and is an active problem in many irrigated regions today.

## §21 Farming systems, honestly

| System | Characteristics | Honest Assessment |
|---|---|---|
| Conventional | Synthetic inputs, tillage, monoculture-leaning | Highest yield per acre in most contexts. Soil degradation if not managed well. |
| Organic (certified) | Input restrictions per organic standards. NOT "no pesticides" — approved natural pesticides permitted, some more toxic than synthetics they replace. | Typically 10–30% lower yields. Price premium may compensate. Soil benefits from organic matter focus. |
| Conservation/No-till | Soil-focused, minimize disturbance, keep soil covered | Real soil benefits. More herbicide-dependent for weed control. |
| Regenerative | NOT a defined standard. A cluster of practices: no-till, cover crops, diversity, integrated livestock. | Many practices have good evidence for soil health, water infiltration, and resilience. Aggregate climate/carbon claims run ahead of measurements. |
| Agroforestry/Silvopasture | Trees + crops or livestock | Diversified income, soil protection, habitat. Longer time horizon for tree returns. |

> **A DOMAIN OF STRONG CLAIMS AND WEAK EVIDENCE ON ALL SIDES**
>
> The organic yield gap is real and varies substantially by crop and context; the claim that organic
> could feed the world at current diets is not well supported. Equally, "regenerative" carbon
> sequestration claims are frequently overstated — soil carbon gains saturate, are reversible on
> tillage, and are genuinely hard to measure at field scale. **Read yield comparisons carefully:
> per-acre versus per-farm versus per-calorie versus per-unit-input give different winners, and
> advocates on each side select the metric that favors them.**

## §22 The crop growing checklist

**BEFORE YOU PLANT**

- Get a soil test.
- Adjust pH with lime if needed.
- Add organic matter (compost, manure, cover crops).
- Check drainage — dig a hole, fill it with water, see how fast it drains.
- Plan your rotation **before** you plant your first crop.
- Choose varieties suited to your climate zone and soil type.
- Calculate how much seed you need for your area.
- Prepare beds or fields with the right tillage for your system.

**DURING THE SEASON**

- Monitor for pests weekly — scout, identify, threshold.
- Irrigate based on soil moisture, not the calendar.
- Manage weeds early — small weeds are easy, large weeds are hard and have already set back the crop.
- Side-dress nitrogen if the crop needs it (use a pre-sidedress nitrate test for corn).
- Walk the field regularly and observe — the best farmers are the ones who look most carefully.

**AT HARVEST AND AFTER**

- Harvest at the right maturity — too early reduces yield and quality; too late loses quality or
  shatters.
- Cool produce quickly to preserve quality.
- Save seed from open-pollinated varieties if you want to save money next year.
- Plant a cover crop immediately after harvest — **never leave bare soil over winter if you can avoid
  it.**
- Test the soil again to track changes over time.
- Add compost or manure for the next season.

Soil testing, pH and lime, nitrogen splitting and the 4Rs are covered in §16 →
`homestead-soil-and-fertility`. GDD, IPM, CEC and refugia are defined in the glossary at §23 →
`homestead-reference`, which also lists the crop and soil books worth owning (§24).
