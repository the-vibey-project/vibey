---
id: skill-26-what-s-live-checked-august-2026-3cee1e9388
purpose: 26 what s live checked august 2026
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-reference/SKILL.md
requires: []
links: ["skill-27-misconceptions-8676a99ab6"]
---

## §26. What's Live — checked August 2026

### 26.1 ⚠️ The bottleneck moved to the substation
**⚠️ §1 → `hw-bottlenecks-cpu-memory-gpu-and-storage`'s migration completing its latest step — and this is now the primary constraint on
whether AI infrastructure gets built at all.**

- **⚠️ THE SHIFT.** ⚠️ **Through 2023–24 the constraint was chips and packaging (see a
  semiconductor reference §27.2). Reporting through 2026 is consistent that GPU
  availability has improved measurably while the grid has not caught up — power capacity is
  now the more pressing constraint for new deployments.**
- **⚠️ THE QUEUE.** ⚠️ **US interconnection queues reportedly contained around 2,600 GW of
  proposed generation and storage in early 2026, with wait times of five years or more.**
  ⚠️ **Lawrence Berkeley National Laboratory research is cited finding interconnection wait
  times have more than doubled over fifteen years, averaging around five years.** ⚠️ **One
  analysis notes only about a quarter of active queue capacity nationally has an executed
  or draft interconnection agreement — meaning most has no confirmed timeline at all.**
  ⚠️ **In ERCOT, a reported 410 GW large-load queue is 87% data centres.**
- **⚠️ EQUIPMENT IS THE SECOND WALL, and it is physical rather than procedural.**
  ⚠️ **Wood Mackenzie is cited reporting power and distribution transformer supply
  shortfalls of 30% and 10% respectively in 2025, with large power transformer lead times
  averaging 128 weeks in Q2 2025 and generator step-up transformers 144 weeks.**
  ⚠️ **Substations, switchgear and transmission are named alongside.**
- **⚠️ THE DEMAND PICTURE.** ⚠️ **The IEA is cited projecting global data centre electricity
  consumption rising from 415 TWh in 2024 toward 945 TWh by 2030; Goldman Sachs Research is
  cited forecasting US data centre demand from 31 GW in 2025 to 66 GW by 2027.**
  ⚠️ **NERC has warned that roughly half of the continental US faces elevated reliability
  risk as early as 2026 from capacity shortfalls and delayed transmission.**

> **⚠️ GOTCHA — the timescale mismatch is the whole problem, and no amount of capital fixes
> it directly.** ⚠️ **IT hardware supply chains can scale in 12–24 months; grid upgrades and
> heavy electrical equipment run on multi-year to decadal cycles.** **⚠️ So money arriving
> faster does not make transformers arrive faster.**
> ⚠️ **The observed responses are telling: developers advancing projects with ON-SITE
> natural gas generation (the IEA reported this in April 2026), operators becoming de facto
> energy companies, relocation to regions with surplus capacity even where fibre is less
> mature, and regulatory attention — the DOE reportedly directed FERC to expedite large-load
> interconnection by 30 April 2026.**
> **⚠️ One genuinely interesting mitigation: DNV's study of the Dutch network suggests
> INTERRUPTIBLE "emergency lane" connections — accepting occasional planned curtailment —
> could unlock 5–15% additional capacity in congested areas without compromising system
> security.** ⚠️ **Demand flexibility is cheaper than new transmission and is
> underexploited.**

**⚠️ Sourcing caution: much of this comes from data centre developers, consultancies and
infrastructure investors who benefit from the scarcity narrative.** ⚠️ **I anchored on IEA,
LBNL, NERC and Wood Mackenzie figures as cited, and note that the demand projections in
particular have a poor forecasting track record in this sector.**

### 26.2 ⚠️ Rack power density and the move to 800 VDC
**⚠️ §17 → `hw-datacentre-facility-power-cooling-and-efficiency`'s distribution chain being redesigned — and it is a direct application of the
I²R physics in an electromagnetism reference.**

- **⚠️ THE DENSITY TRAJECTORY.** ⚠️ **Conventional racks draw perhaps 5–10 kW.**
  ⚠️ **Reported figures: Hopper-era AI racks around 40 kW; GB200 NVL72 at 120–130 kW;
  GB300 NVL72 at 132–142 kW; Vera Rubin VR200 NVL72 at roughly 190–230 kW; and the 2027
  Rubin Ultra "Kyber" rack specified at around 600 kW, with 1 MW-class behind it.**
- **⚠️ WHY 48 V BREAKS — and this is straightforward physics, not a vendor argument.**
  ⚠️ **Delivering 120 kW at 48 V requires currents exceeding 2.5 kA; one analysis puts the
  NVL72 busbar at more than 3.8 kA at peak.** ⚠️ **NVIDIA states that using 54 VDC for a
  1 MW rack would require up to 200 kg of copper busbar per rack — and up to 200,000 kg of
  rack busbar copper in a single gigawatt facility.**
  ⚠️ **Space is the other limit: NVIDIA notes 54 VDC distribution at megawatt scale would
  consume up to 64U of power shelves, leaving no room for compute.**
- **⚠️ THE ANSWER IS HIGHER VOLTAGE, LOWER CURRENT.** ⚠️ **800 VDC distribution to the rack,
  with AC/DC conversion moved OUT of the IT rack into an adjacent "SIDECAR" cabinet.**
  ⚠️ **That returns the 8–16 rack units power conversion previously consumed, and lets
  power capacity be managed independently of compute capacity.**
- **⚠️ The ecosystem is broad and real**: ⚠️ **ABB, Eaton, GE Vernova, Hitachi Energy,
  Mitsubishi Electric, Schneider Electric, Siemens, Vertiv, TI, Infineon, Navitas and ST
  are all named developing 800 VDC hardware — and note the power semiconductors involved
  are wide-bandgap GaN and SiC parts** (see an electromagnetism reference §26.2).
  ⚠️ **Vertiv's 800 VDC portfolio was reported planned for H2 2026.**

> **⚠️ GOTCHA — 800 VDC is NOT YET REQUIRED, and the honest analysis says so.** ⚠️ **One
> assessment notes the chip generations ramping in late 2026 and 2027 top out around
> 180–220 kW per rack, which three-phase AC can still deliver without hitting conductor
> sizing limits — making early adoption "voluntary future-proofing, not a forced response
> to a hardware constraint."**
> ⚠️ **The forcing function arrives at 400 kW and above.** **⚠️ Expect a retrofit era first,
> layering HVDC power racks onto existing white space without replacing transformers, UPS
> or switchgear.**
> **⚠️ And note the safety consequence: 800 VDC to the IT rack raises insulation, creepage
> and clearance requirements beyond three-phase AC practice, and DC arcs are harder to
> extinguish than AC** (see an electromagnetism reference §23). ⚠️ **There are also
> competing 800 VDC standards, unipolar and bipolar, which differ in exactly these
> respects.**

**⚠️ The cooling consequence is not optional either**: ⚠️ **air handles roughly 30–40 kW per
rack with optimized design; direct-to-chip liquid extends to 60–120 kW; and GB200 NVL72
class needs over 120 kW of cooling capacity.** ⚠️ **Above that, all-liquid is mandatory —
which is why §18 → `hw-datacentre-facility-power-cooling-and-efficiency`'s liquid section is now the default rather than the exception.**
**⚠️ Sourcing note: nearly all of this comes from NVIDIA and its power-infrastructure
partners, who are selling the transition.** ⚠️ **The PHYSICS (I²R, copper mass, rack unit
consumption) is checkable and solid; the density roadmap figures are vendor projections and
I have marked them as reported.**

---
