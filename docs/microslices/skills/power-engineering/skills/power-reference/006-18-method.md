---
id: skill-18-method-ee087900f4
purpose: 18 method
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-reference/SKILL.md
requires: ["skill-17-quick-reference-a25bd2d8a3"]
links: []
---

## §18. Method

**§1–§14 → `power-ac-fundamentals-generation-and-grid`, `power-system-analysis-and-protection`, `power-scada-ems-and-protocols`, `power-inverters-storage-markets-and-datacenters` rest on settled material** — **Fortescue's symmetrical components (1918)**,
per-unit, Newton-Raphson power flow, protection principles, and market optimization
formulations — sourced from the references in §16, chiefly **Kundur**, **Glover/Sarma/
Overbye**, **Blackburn & Domin**, and **Wood/Wollenberg**. ⚠️ **None of that needed
verification; it's been stable for decades and the textbooks are the authority.**

**Scoped to complement**: component-level circuit design, op-amps, PCB layout and signal
integrity sit in an electrical-engineering reference. **This picks up at the kilovolt
scale.** ⚠️ **§11.1 → `power-inverters-storage-markets-and-datacenters` and §11.2 → `power-inverters-storage-markets-and-datacenters` deliberately parallel the flight-software and automotive
references — safety-critical embedded practice converges across industries, and the
reasoning transfers.**

**Two searches were run in August 2026**, on the two areas that genuinely moved: **the
inverter-dominated grid** and **datacenter load growth.**

**Confidence.** **High** in §1–§11 → `power-ac-fundamentals-generation-and-grid`, `power-system-analysis-and-protection`, `power-scada-ems-and-protocols`, `power-inverters-storage-markets-and-datacenters` and §14 — textbook material stated with its
assumptions, and the assumptions are the useful part. **High** in §8 → `power-inverters-storage-markets-and-datacenters`'s technical content:
the GFL/GFM distinction, the inertia and short-circuit-ratio mechanism, and the
protection consequences of limited inverter fault current are **consistent across
peer-reviewed sources** (IET, ScienceDirect, MDPI, arXiv reviews) **and NREL/NERC
material.**

⚠️ **Two hedges, weighted differently.**

**§8.2 → `power-inverters-storage-markets-and-datacenters`'s UK procurement figure I'd treat as solid and important** — it comes from a
consultancy analysis but is a **concrete, checkable procurement outcome** rather than a
forecast, and ⚠️ **it cuts directly against the prevailing enthusiasm, which is part of
why I've given it prominence.** **Verify the current figure if you're making a
technology decision on it.**

**⚠️ §15.2 is the weak section and is flagged in place.** The sourcing is **consultancies,
real estate firms, equipment vendors, grid-analytics companies and investment banks, all
of whom benefit from the growth narrative**, and ⚠️ **the demand projections varied
noticeably between them.** **I have deliberately separated the better-attested physical
facts — interconnection queue lengths, the 13%/77% historical completion base rate,
transformer and switchgear lead times, PJM's January 2026 connect-and-manage
announcement — from the forecasts, and I'd trust the former considerably more than the
latter.** ⚠️ **Direction is solid; magnitude is contested.**

**One thing I'd flag as the actionable insight rather than trivia**: ⚠️ **PJM's
connect-and-manage framework makes workload flexibility an interconnection asset.** **If
that model spreads, scheduler design becomes a determinant of how fast compute capacity
can be built** — which is an unusually direct line from software architecture to physical
infrastructure.
