---
id: skill-17-crop-production-484ca7ec74
purpose: 17 crop production
source: src/vibey_tools/skills/plugins/building-a-homestead/skills/homestead-crops-rotation-pests-and-water/SKILL.md
requires: []
links: ["skill-18-crop-rotation-multiple-jobs-at-once-306a4abdd7"]
---

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
