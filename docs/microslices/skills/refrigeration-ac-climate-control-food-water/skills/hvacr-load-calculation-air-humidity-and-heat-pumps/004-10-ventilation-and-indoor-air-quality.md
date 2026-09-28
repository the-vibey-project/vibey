---
id: skill-10-ventilation-and-indoor-air-quality-e621a7f43d
purpose: 10 ventilation and indoor air quality
source: src/vibey_tools/skills/plugins/refrigeration-ac-climate-control-food-water/skills/hvacr-load-calculation-air-humidity-and-heat-pumps/SKILL.md
requires: ["skill-9-humidity-control-358c45af5a"]
links: ["skill-11-heat-pumps-c81b366dd9"]
---

## §10. Ventilation and Indoor Air Quality

**⚠️ Ventilation dilutes; filtration removes; source control beats both.**
**Rates per ASHRAE 62.1/62.2; ⚠️ CO₂ as a PROXY for ventilation adequacy (⚠️ it's a
tracer for occupant-generated pollutants, not itself the hazard at typical indoor
levels), demand-controlled ventilation.**
**⚠️ Filtration**: **MERV and the equivalences to ISO/EN ratings; ⚠️ HEPA; and ⚠️ the
critical caveat that fitting a high-MERV filter to a system not designed for its pressure
drop reduces airflow and can cause §5 → `hvacr-cycle-components-refrigerants-and-diagnosis`'s problems.** **Check ESP after any filter upgrade.**
**⚠️ Energy recovery**: **HRV (sensible only) vs ERV (⚠️ sensible AND latent — usually the
right choice in humid climates).**
**⚠️ Legionella is the serious IAQ hazard in this domain**: ⚠️ **it grows in warm stagnant
water — cooling towers, hot water systems held between roughly 20–45°C, and dead legs in
plumbing.** **⚠️ Control is temperature (hot stored hot, cold kept cold), circulation, and
elimination of stagnation; ASHRAE 188 covers water management plans.**

---
