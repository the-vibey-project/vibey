---
id: skill-26-what-s-live-checked-august-2026-16a0f58733
purpose: 26 what s live checked august 2026
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-reference/SKILL.md
requires: []
links: ["skill-27-misconceptions-3ef42f831c"]
---

## §26. What's Live — checked August 2026

### 26.1 ⚠️ Arm started making chips — a 35-year break from the model
**⚠️ §2 → `arm-what-arm-is-licensing-families-and-isa-generations`'s licensing model changing at its foundation, and this is the most significant
strategic shift in the company's history.**

- **⚠️ WHAT HAPPENED.** ⚠️ **In March 2026, at its Arm Everywhere event, Arm announced
  Arm-designed SILICON PRODUCTS for the first time — the Arm AGI CPU, a data centre
  processor for agentic AI infrastructure.** ⚠️ **Arm's own framing is that it is extending
  its platform "beyond IP and Compute Subsystems (CSS) to include Arm-designed silicon
  products."** ⚠️ **One outlet notes the company had never done this in 35 years.**
- **⚠️ THE CHIP, as reported**: ⚠️ **136 Neoverse V3 cores per CPU at 3.7 GHz, TSMC 3nm,
  300 W TDP.** ⚠️ **A high-density air-cooled rack is claimed to deliver over 8,000 cores at
  36 kW with twice the performance of an equivalent x86 configuration at the same power;
  liquid-cooled configurations are claimed to scale past 45,000 cores per rack.**
  ⚠️ **Meta is the lead partner and co-developer, with other customers and ODMs reported.**
  ⚠️ **Development reportedly began in 2023.**
- **⚠️ THE PATH THERE WAS GRADUAL, and §2 → `arm-what-arm-is-licensing-families-and-isa-generations`'s CSS is the middle step.** ⚠️ **CSS are
  pre-integrated blueprints rather than bare cores; Arm reported 19 CSS licences with 11
  companies and five customers already shipping CSS-based chips, and claims first-generation
  CSS delivers double the royalty of ARMv9.** ⚠️ **Arm has also described CSS saving
  customers "80 engineering years."**
- **⚠️ THE ROYALTY LOGIC underneath all of this.** ⚠️ **ARMv9 is reported to command roughly
  double the royalty rate of ARMv8, and Arm reported v9 contributing over 50% of royalty
  revenue in late 2025.** ⚠️ **Moving from core IP → subsystem → chiplet → whole chip
  captures progressively more value per unit of silicon.**

> **⚠️ GOTCHA — this puts Arm in partial competition with its own licensees, and that
> tension is real.** ⚠️ **Analyst commentary notes the turnkey CPU directly substitutes for
> services design houses have traditionally provided, forcing them to reposition toward
> chiplet and 3D-integration work.**
> ⚠️ **It also changes Arm's risk profile fundamentally: ⚠️ core licensing carried no
> supply-chain responsibility, while subsystems and silicon demand coordination with
> foundries, packaging houses and firmware partners.** **⚠️ A company with 97% gross margins
> selling IP is a different business from one shipping chips.**
> **⚠️ And note the naming: "AGI CPU" is Arm's product name for agentic AI infrastructure —
> one outlet glosses it as "Artificial General Intelligence," which is marketing, not a
> technical claim.**

**⚠️ Sourcing note: the announcement and specifications come from Arm's own newsroom and
from trade press reporting the launch event.** ⚠️ **The performance claims — 2× per rack
versus x86 — are Arm's, made by the CEO, and are not independently verified here.**
⚠️ **A large share of the surrounding commentary is investment analysis with obvious
positions, and I have kept to the announcement facts.**

### 26.2 ⚠️ Where ARM actually is in the datacentre — and why the numbers disagree
**⚠️ §3 → `arm-what-arm-is-licensing-families-and-isa-generations`'s Neoverse story, with a measurement caveat that matters.**

- **⚠️ THE DEPLOYMENT PICTURE IS UNAMBIGUOUS.** ⚠️ **Arm reported in February 2026 that
  Neoverse CPUs had surpassed ONE BILLION CORES DEPLOYED.** ⚠️ **Every major hyperscaler has
  custom Arm silicon: AWS Graviton, Google Axion, Microsoft Cobalt, NVIDIA Grace/Vera —
  and Arm reported data centre royalty revenue more than doubling year on year for several
  consecutive quarters.**
- **⚠️ AWS is the proof case.** ⚠️ **Graviton is reported serving nearly 100,000 cloud
  customers and driving over half of AWS's CPU demand — Arm's own materials say Graviton
  powers over 50% of AWS's recent capacity.**

> **⚠️ GOTCHA — the market-share figures differ by a factor of two or three depending on
> what is being counted, and this is the thing to get right.**
> ⚠️ **IDC data reported in June 2026 put Arm-based machines at well over 45% of server
> market REVENUE.** ⚠️ **A separate analysis puts Arm at 15–23% of server CPU SHIPMENTS in
> 2025, up from around 5% in 2020.**
> **⚠️ Both can be true. Revenue share is inflated by AI servers, where an Arm CPU sits
> alongside expensive accelerators and the whole system counts** — ⚠️ **the same reporting
> notes accelerated servers were around 70.6% of all server revenue in Q1 2026.**
> ⚠️ **A third datum keeps it grounded: one report cites an analyst noting Arm's roughly
> $2 billion in AGI CPU sales are still not enough to reach 5% of overall market share.**
> **⚠️ When you see an ARM server share figure, ask: revenue or units, shipments or
> installed base, and does it count the CPU or the whole system.**

**⚠️ The driver is power, not performance** (see a computer-hardware reference §26.1):
⚠️ **cloud operators adopt Arm to lower cost per request and free campus power capacity for
AI racks.** ⚠️ **One market analysis puts it plainly — the shift has less to do with chip
performance than with energy economics under power-constrained AI scaling.**
**⚠️ The remaining constraint is software readiness**, ⚠️ **and one analyst's framing is
honest: a processor can look efficient on paper, but enterprise planners need container
support and database tuning before moving production workloads** (§23 → `arm-cortex-m-toolchain-porting-and-performance`).
**⚠️ Sourcing caution: several sources here are market-research firms selling forecast
reports, whose absolute figures I would not rely on.** ⚠️ **The billion-cores milestone and
the hyperscaler adoption are from Arm and are consistent with independent reporting; the
share figures are exactly where I would expect motivated numbers, hence the gotcha.**

---
