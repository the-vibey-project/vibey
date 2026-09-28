---
id: skill-27-what-s-live-checked-august-2026-5b2be1741c
purpose: 27 what s live checked august 2026
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-reference/SKILL.md
requires: []
links: ["skill-28-misconceptions-480f24f425"]
---

## §27. What's Live — checked August 2026

### 27.1 ⚠️ High-NA EUV: in production, and the leaders disagree about it
**⚠️ §11 → `semi-cleanroom-lithography-deposition-etch-and-cmp`'s frontier, and it has just crossed from R&D into manufacturing — with a genuine
split between foundries about whether it is worth the money.**

- **⚠️ THE TOOL.** ⚠️ **ASML's TWINSCAN EXE:5200B, with 0.55 NA anamorphic optics from Zeiss,
  at a reported cost of roughly $360–400 million per machine.** ⚠️ **Intel reported the
  EXE:5200B at 175 wafers per hour with 0.7 nm overlay.** ⚠️ **Standard 0.33-NA EUV tops out
  around 13 nm half-pitch in a single exposure; High-NA reportedly enables features up to
  66% smaller.**
- **⚠️ IT IS NOW IN VOLUME PRODUCTION.** ⚠️ **Intel installed the industry's first
  commercial High-NA tool in December 2025, and on 15 July 2026 ASML confirmed High-NA EUV
  had reached high-volume manufacturing — used to pattern specific layers of Intel Core
  Ultra Series 3 (Panther Lake) processors built on Intel 18A.**
- ⚠️ **Note the nuance that coverage sometimes loses: 18A was DESIGNED around Low-NA EUV
  and multi-patterning and does not depend on High-NA to ship.** ⚠️ **18A is the commercial
  validation; Intel's 14A is the node where High-NA becomes foundational.**
- **⚠️ Samsung and SK hynix are also adopting** — ⚠️ **Samsung reportedly received its first
  EXE:5200B in late 2025 with a second in H1 2026 for advanced foundry lines, and SK hynix
  is reported as the first memory maker to install a commercial system.**

> **⚠️ GOTCHA — TSMC, the largest foundry, is deliberately SITTING OUT, and its reasoning is
> economically serious rather than conservative.** ⚠️ **TSMC has said High-NA remains too
> expensive at this stage and plans to continue using current EUV systems for the next
> several chip generations — with A13 and A12, targeted for 2029, reportedly not requiring
> High-NA.**
> ⚠️ **The underlying argument: existing Low-NA tools can match High-NA's resolution using
> DOUBLE PATTERNING, and one analysis estimates that approach may still cost LESS than
> High-NA single patterning.** ⚠️ **Against that, each extra patterning step reportedly adds
> a mask set, alignment error budget, two more etch steps and roughly 30% to wafer cost —
> and by the 2nm node the most aggressive layers were already triple- and
> quadruple-patterned.**
> **⚠️ So this is a genuine open question about where the crossover sits, not a case of one
> party being wrong.** ⚠️ **ASML's own CEO frames adoption as gradual, with high-volume
> manufacturing expected across 2027–28.**

**⚠️ Hyper-NA** is reported as ASML's next step, some time in the next decade.
**⚠️ Sourcing note: ASML and Intel are interested parties on one side and TSMC on the
other; I've taken the production milestone from ASML's own press release and the
cost-benefit dispute from trade reporting on both companies' statements.**

### 27.2 ⚠️ The bottleneck moved to packaging and memory
**⚠️ §20 → `semi-integration-yield-metrology-test-and-packaging`'s subject becoming the industry's binding constraint — and this is a genuine
reversal of decades of structure.**

- **⚠️ THE CLARIFYING NUMBER.** ⚠️ **Epoch AI estimates the four largest AI chip designers
  collectively consumed around 90% of global CoWoS capacity and HBM supply in 2025 — while
  consuming only about 12% of advanced LOGIC DIE production.**
  ⚠️ **That single comparison tells you where the constraint is: not transistors.**
- **⚠️ WHY.** ⚠️ **An AI accelerator cannot be a single monolithic die — reticle limits
  (§17 → `semi-integration-yield-metrology-test-and-packaging`) and yield force chiplets, and the compute die must sit adjacent to multiple HBM
  stacks on an interposer.** ⚠️ **So every accelerator needs a front-end wafer AND a CoWoS
  slot AND an HBM allocation, and no single intervention resolves it.**
- **⚠️ CAPACITY IS SCALING FAST AND STILL SHORT.** ⚠️ **Reported figures vary by source and
  by what they count, but the direction is consistent: TSMC CoWoS capacity has roughly
  tripled since 2023, with 2026 in-house targets reported variously around 120,000–140,000
  wafers per month, plus OSAT spillover.** ⚠️ **TrendForce is cited estimating the
  supply-demand gap narrowing from around 20% to around 10% by end-2026.**
  ⚠️ **CoWoS is reported fully booked, with NVIDIA holding roughly 60% of allocation.**
- **⚠️ HBM IS THE CO-EQUAL CONSTRAINT.** ⚠️ **HBM3E reportedly effectively sold out for 2026;
  HBM4 ramping into late 2026.** ⚠️ **A structural problem underneath: HBM4 is reported to
  need roughly 3× the wafer area of standard DRAM for the same capacity, so reallocating
  fabs toward HBM tightens conventional DRAM — which is why memory prices for ordinary PCs
  rose.** ⚠️ **HBM is reported at around 25% of DRAM industry revenue on under 5% of bit
  volume.**

> **⚠️ GOTCHA — capacity announcements are a LAGGING indicator, because capacity that cannot
> pass customer qualification does not ship.** ⚠️ **Reporting on Samsung's 12-layer HBM3E
> stacking yield difficulties makes the point: stacking more dies compresses bonding
> alignment tolerance and TSV integrity margins, so an announced capacity increase is only
> meaningful once yield is proven.**
> ⚠️ **This is §17 → `semi-integration-yield-metrology-test-and-packaging`'s yield lesson reappearing at the package level — and it is why HYBRID
> BONDING (§20 → `semi-integration-yield-metrology-test-and-packaging`) is described as becoming essential rather than optional.**

**⚠️ Where this is heading**: ⚠️ **reporting points to CoWoS generations supporting eight
HBM4 stacks with dual compute chiplets, 16-high stacks raising yield and thermal risk, and
CO-PACKAGED OPTICS moving into high-performance systems as power savings in AI networking
become compelling.** ⚠️ **One analysis notes memory and packaging together now represent
60–70% of AI accelerator cost of goods — logic silicon is no longer the dominant cost,
which is the whole story in one line.**
**⚠️ Sourcing caution: capacity and share figures here come from market-intelligence firms
and supply-chain consultancies and DISAGREE with each other on specifics — I've reported
ranges and marked them.** ⚠️ **The Epoch AI 90%/12% comparison is the most useful and
best-sourced single datum, and it is an estimate.**

---
