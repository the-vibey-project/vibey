---
name: homestead-reference
description: "Use when you hit an unfamiliar term of art from the homestead reference — Animal Unit, Body Condition Score, CEC, EPD, FAMACHA, GDD, IPM, NDF/ADF, rainscreen, refugia, rumen, shear wall, thermal bridge, volatile fatty acids — and need the definition plus the section that explains it, or when you want the books, codes and free services that actually teach building, livestock and soil. Covers the complete glossary and the complete further-reading list across all three domains. Part 8 of the Building a Homestead reference."
---

# Glossary and Further Reading

> **Part 8 of 8** of the *Building a Homestead* reference (plugin `building-a-homestead`), covering
> §23–§24 — the terms of art across all three domains, and the books that actually teach this. Sibling skills:
> `homestead-site-structure-and-materials` (§1–§3 — ground investigation, solar orientation, the gravity and lateral systems, and choosing a structural material),
> `homestead-envelope-and-building-physics` (§4–§5 — the four control layers in priority order, drying potential, and the materials that make them up),
> `homestead-services-sequencing-and-codes` (§6–§7 — MEP, fire safety, the order the trades run in, permitting, and the house build checklist),
> `homestead-livestock-digestion-nutrition-and-species` (§8–§10 — why cattle are different, the nutrient requirements that follow, and picking a species),
> `homestead-livestock-housing-health-and-grazing` (§11–§14 — fencing and shelter, biosecurity, reproduction, and the grazing systems with their trade-offs),
> `homestead-soil-and-fertility` (§15–§16 — what soil actually is and how to feed it without wrecking it),
> `homestead-crops-rotation-pests-and-water` (§17–§22 — crop production, why rotation does several jobs at once, IPM, irrigation methods, and an honest look at farming systems),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Building work is governed by local codes and inspection, and livestock by
> local animal-health rules; this reference tells you what to design for and what to ask, not what
> your jurisdiction permits.

## How to read a pointer

Every glossary entry ends with a pointer of the form **§N → `sibling-skill`**. `§N` is the section
that explains the term in context — the argument it belongs to, not just a restatement of the
definition. The skill name is the file to open.

| Sections | Skill | What lives there |
|---|---|---|
| §1–§3 | `homestead-site-structure-and-materials` | Ground investigation, solar orientation, the gravity and lateral systems, choosing a structural material |
| §4–§5 | `homestead-envelope-and-building-physics` | The four control layers in priority order, drying potential, the materials that make them up |
| §6–§7 | `homestead-services-sequencing-and-codes` | MEP, fire safety, the order the trades run in, permitting, the house build checklist |
| §8–§10 | `homestead-livestock-digestion-nutrition-and-species` | Why cattle are different, the nutrient requirements that follow, picking a species |
| §11–§14 | `homestead-livestock-housing-health-and-grazing` | Fencing and shelter, biosecurity, reproduction, the grazing systems with their trade-offs |
| §15–§16 | `homestead-soil-and-fertility` | What soil actually is and how to feed it without wrecking it |
| §17–§22 | `homestead-crops-rotation-pests-and-water` | Crop production, rotation, IPM, irrigation, an honest look at farming systems |
| §23–§24 | `homestead-reference` | This skill: the glossary and the further reading |

## §23 The glossary

Fourteen terms, listed alphabetically as the reference lists them. Three come from building, eight
from livestock, three from soil and crops. Each definition is the reference's own; the pointer sends
you to the section where the term does work.

| Term | Definition | Explained in |
|---|---|---|
| **Animal Unit (AU)** | Standardized measure for grazing: one 1000-pound cow with calf = 1 AU. Approximately 5 sheep or 5 goats = 1 AU. Used to calculate stocking rates across species. | §14 → `homestead-livestock-housing-health-and-grazing` |
| **Body Condition Score (BCS)** | A subjective scoring of an animal's fat cover (typically 1-5 or 1-9 scale). The practical, free management tool for monitoring nutrition. Condition at calving/lambing predicts rebreeding success. | §9 → `homestead-livestock-digestion-nutrition-and-species` (and again as the reproductive lever at §13 → `homestead-livestock-housing-health-and-grazing`) |
| **CEC (Cation Exchange Capacity)** | The soil's ability to hold positively charged nutrient ions on clay and organic matter surfaces. Low CEC soils (sandy) leach nutrients; high CEC soils (clay, high organic matter) retain them. | §15 → `homestead-soil-and-fertility` |
| **EPD (Expected Progeny Difference)** | A prediction of a sire's progeny performance relative to a breed's base. Not comparable across breeds. Accuracy values indicate the reliability of the prediction. | §13 → `homestead-livestock-housing-health-and-grazing` |
| **FAMACHA** | A scoring system using eyelid mucous membrane color to assess anemia in small ruminants, used for targeted selective deworming against barber pole worm. Red/pink = anemic = treat; bright pink/red = healthy = don't treat. ⚠️ **Reproduced as written, and as written it is self-contradictory** — the same colours appear on both sides. Verify against an official FAMACHA card before deworming; see §12. | §12 → `homestead-livestock-housing-health-and-grazing` |
| **GDD (Growing Degree Days)** | Heat accumulation used to predict crop development. Each day contributes max(0, (daily max + daily min)/2 − base temperature) — ⚠️ **clamped at zero**, or a cold day subtracts heat the crop already banked and the running total moves predictions backwards. Many models also cap the daily maximum at a crop-specific upper threshold. More reliable than calendar dates for timing planting and harvest. | §17 → `homestead-crops-rotation-pests-and-water` |
| **IPM (Integrated Pest Management)** | A decision framework using economic thresholds to determine if pest control is justified, with least-disruptive methods applied first: cultural, biological, mechanical, then chemical. | §19 → `homestead-crops-rotation-pests-and-water` |
| **NDF / ADF** | NDF (neutral detergent fiber) predicts feed intake — higher NDF means lower intake. ADF (acid detergent fiber) predicts digestibility — higher ADF means lower digestibility. Key forage quality metrics. | §9 → `homestead-livestock-digestion-nutrition-and-species` |
| **Rainscreen** | A wall assembly principle: accept that the outer skin leaks, and provide a drained and ventilated cavity with a drainage plane behind it. More durable than "perfect barrier" designs that fail at the first sealant failure. | §4 → `homestead-envelope-and-building-physics` |
| **Refugia** | In parasite management, deliberately leaving a population of unselected (susceptible) parasites by not deworming every animal. The susceptible genes dilute resistance genes in the parasite population, slowing the evolution of resistance. | §12 → `homestead-livestock-housing-health-and-grazing` (the same device reappears in pesticide resistance management — leave unsprayed areas — at §19 → `homestead-crops-rotation-pests-and-water`) |
| **Rumen** | The first and largest stomach compartment of a ruminant — a fermentation vat of bacteria, protozoa, fungi, and archaea that digests cellulose and produces volatile fatty acids and microbial protein. You feed the rumen microbes, not the animal. | §8 → `homestead-livestock-digestion-nutrition-and-species` |
| **Shear Wall** | A wall sheathed with plywood or OSB, designed to resist lateral (wind and seismic) forces and transfer them to the foundation. The primary lateral system in most houses. | §3 → `homestead-site-structure-and-materials` |
| **Thermal Bridge** | A continuous conductive path through insulation (like a steel beam or balcony slab) that causes both heat loss and local cold surfaces where condensation forms. Exterior insulation is the most effective way to break thermal bridges. | §4 → `homestead-envelope-and-building-physics` |
| **Volatile Fatty Acids (VFAs)** | Acetate, propionate, and butyrate — produced by rumen microbes during fermentation. These, not glucose, are the ruminant's main energy source. Acetate dominates on forage diets; propionate rises on grain. | §8 → `homestead-livestock-digestion-nutrition-and-species` |

### The same fourteen, grouped by domain

| Domain | Terms |
|---|---|
| Building | Rainscreen (§4), Shear Wall (§3), Thermal Bridge (§4) |
| Livestock | Animal Unit (§14), Body Condition Score (§9), EPD (§13), FAMACHA (§12), NDF / ADF (§9), Refugia (§12), Rumen (§8), Volatile Fatty Acids (§8) |
| Soil and crops | CEC (§15), GDD (§17), IPM (§19) |

### Two vocabularies that rhyme

Drawn from the reference's own sections, not added to them:

- **Refugia is one idea in two domains.** In small-ruminant parasite management (§12) you deliberately
  leave a population of unselected parasites so resistance does not fix in the population; in pest
  management (§19) you leave unsprayed areas so susceptible pests survive to dilute resistance.
  Both are counterintuitive, and both are correct.
- **Both livestock and crops start with a test, not an assumption.** A forage analysis costs $20-40
  and stops you feeding "hay" as if it were a constant (§9); a soil test stops you fertilizing by
  guesswork (§16). "Start with a soil test. Always." is the reference's own instruction.

## §24 Further reading

The reference's own list, with the reason each work is on it. Free, local sources appear in two of
the four groups and again as the closing recommendation — that is deliberate.

### Building

| Work | Why it is listed |
|---|---|
| Francis Ching, *Building Construction Illustrated* | The standard visual reference. |
| The International Residential Code (IRC) | The actual rules for house construction in most US jurisdictions. |
| Joseph Lstiburek, *Builder's Guide* series (by climate zone) | The best practical guide to building envelope and moisture management. |
| John Raabe, *Code Check* series | Simplified code references for builders. |

The IRC is also the code named in §7 → `homestead-services-sequencing-and-codes` as covering one-
and two-family dwellings, and the *Builder's Guide* series is by climate zone for the reason §4 →
`homestead-envelope-and-building-physics` gives: copying a vapor-control detail from the wrong
climate zone traps moisture in the assembly and rots it.

### Livestock

| Work | Why it is listed |
|---|---|
| Temple Grandin, *Livestock Handling and Transport* | Low-stress handling. |
| The Merck Veterinary Manual | The standard reference for animal health. |
| Your local extension service publications | Region-specific, practical, and free. |
| Ron Parker, *Stockmanship* | The art of working animals with their instincts. |

Grandin's flight zone and point of balance are set out at §14 →
`homestead-livestock-housing-health-and-grazing`.

### Crops and soil

| Work | Why it is listed |
|---|---|
| ATTRA / National Center for Appropriate Technology publications | Practical, free, sustainable agriculture guides. |
| Your local extension service soil test and crop recommendations | *(No reason line given in the source; it is listed alongside the ATTRA publications as a local source.)* |
| Elaine Ingham's Soil Foodweb materials | Soil biology for growers. |
| Robert Pavlis, *Soil Science for Gardeners* | Accessible but scientifically accurate. |
| *Building Soils for Better Crops* (SARE) | The practical guide to soil organic matter management. |

### Homesteading integration

| Work | Why it is listed |
|---|---|
| John Seymour, *The Self-Sufficient Life and How to Live It* | The classic homesteading reference. |
| Ben Hewitt, *The Nourishing Homestead* | A modern, practical account. |
| Your local agricultural extension agent | The single most valuable free resource available to a new farmer or homesteader. |

### The reference's closing judgement

The list ends on the extension agent, not on a book. Across all three parts the same pattern holds:
the ground you did not choose (§1), the forage you did not analyse (§9), and the soil you did not
test (§16) are each local facts that no general reference can supply. The free, region-specific
source is not a consolation prize — it is the one input the rest of the method depends on.

## Where to go next

- **A building term you cannot place** — start at the four control layers, §4 →
  `homestead-envelope-and-building-physics`. Water destroys more buildings than structural failure,
  so most unfamiliar envelope vocabulary resolves there.
- **A livestock term you cannot place** — start at ruminant digestion, §8 →
  `homestead-livestock-digestion-nutrition-and-species`. The rumen explains most of the rest.
- **A soil or crop term you cannot place** — start at soil science, §15 →
  `homestead-soil-and-fertility`. Texture is permanent, structure is manageable, and organic matter
  is the highest-leverage property.
- **A judgement call rather than a definition** — the honest assessments live with their subjects:
  the intensive-grazing debate at §14, the organic yield gap and regenerative carbon claims at §21 →
  `homestead-crops-rotation-pests-and-water`, and the cost-influence curve at §1 →
  `homestead-site-structure-and-materials`.
