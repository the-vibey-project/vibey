---
id: skill-23-what-s-live-verified-august-2026-0e930df786
purpose: 23 what s live verified august 2026
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-reference/SKILL.md
requires: []
links: ["skill-24-misconceptions-55ea9e899a"]
---

## §23. What's Live — verified August 2026

### 23.1 ⚠️ Infrastructure condition: the asset-management picture in numbers
**⚠️ Included because it's what §10 → `civil-codes-licensure-failure-analysis-and-construction`'s asset management produces when done at national
scale — and because "technical debt" arguments are strengthened enormously by seeing what
a quantified version looks like.**

- **⚠️ ASCE's 2025 Report Card graded US infrastructure an overall 'C'** — ⚠️ **an
  improvement from 'C−' in 2021 and the highest since the Report Card began in 1998.**
  **18 categories assessed; ⚠️ nearly half improved, and for the first time since 1998 no
  category received a 'D−'.**
- **⚠️ Grades ranged from 'B' for ports to 'D' for stormwater and transit.** **Broadband
  debuted at 'C+'.** ⚠️ **Energy (D+) and rail (B−) DECLINED.** **Nine categories remain
  in the 'D' range.**
- **⚠️ The gap grew even as grades improved, which is the important finding.** **ASCE
  projects a **$3.7 trillion** shortfall between planned investment and what's needed for
  a state of good repair — ⚠️ **up from $2.59 trillion four years earlier.**
- **⚠️ The improvement is attributed largely to the 2021 IIJA ($1.2 trillion; reported
  $580B in new funding), and ASCE cautions the gains are driven by SHORT-TERM funding
  rather than long-term certainty**, ⚠️ **with authorizations expiring in fiscal 2026 and
  reauthorization uncertain.**

> **⚠️ GOTCHA — the lesson for software's technical-debt conversations is the shape of the
> curve, not the dollar figure.** ⚠️ **Grades improved AND the gap widened simultaneously**,
> **because deterioration and demand growth outran a large one-off investment.** **⚠️ A
> backlog that grows faster than you pay it down is not fixed by a single funded
> initiative — and the ASCE framing shows what it takes to argue for sustained funding:
> a standing inventory, condition assessment, deterioration modelling and a published
> number.** **Software's technical-debt arguments almost never have any of those.**

### 23.2 ⚠️ Project estimation: the base rates, and they include software
**⚠️ The most directly transferable body of evidence in this entire document, because
Flyvbjerg's database includes IT projects and compares them to physical ones.**

- **⚠️ The database holds roughly 16,000 large projects across 20+ fields and 136
  countries, assembled at Oxford over decades**, ⚠️ **recording the budget at the decision
  to build against the final outcome.**
- **⚠️ The headline finding**: ⚠️ **reportedly only about 0.5% of projects come in on
  budget, on time, AND with the promised benefits.** **Around 8.5% hit cost and time but
  not benefits.**
- **⚠️ Averages by type from the earlier published work**: ⚠️ **rail ~45% cost overrun,
  fixed links (bridges and tunnels) ~34%, roads ~20%, in real terms.** **⚠️ Nine out of ten
  projects overrun; overruns above 50% are common and above 100% not uncommon.**
- **⚠️ The finding that should end the "we're getting better at this" conversation**:
  ⚠️ **overruns have been roughly CONSTANT across the seventy years for which data
  exists** — **indicating no improvement in planning and cost management over that period.**

> **⚠️ GOTCHA — IT sits in the FAT TAIL, and that's the number software people should
> know.** ⚠️ **Reportedly 18% of IT projects had cost overruns above 50%, and for those
> projects the average overrun was around 447%.** **⚠️ The distinction that matters is not
> the mean but the TAIL: IT's average overrun is unremarkable, and its catastrophic-outcome
> rate is among the worst of any category.**
> **⚠️ The practical implication: for software projects, the risk is not "we'll be 30%
> over," it's the small probability of a multiple-of-budget disaster** — **which means
> risk management should target the tail, not the average.**

**⚠️ REFERENCE CLASS FORECASTING is the documented remedy, and it's the technique to
steal:**
```
⚠️ 1. Identify a reference class of similar COMPLETED projects
⚠️ 2. Establish the distribution of outcomes for that class
⚠️ 3. Position your project in that distribution and apply the UPLIFT
   for your desired confidence level
```
⚠️ **It's described as the only forecasting method with documented evidence of reducing
optimism bias**, **has been endorsed by the American Planning Association, and has been
mandatory in UK Treasury Green Book / Department for Transport practice since 2003.**
**⚠️ The worked logic**: **if rail's 50th-percentile overrun is 40% and its 80th percentile
is 57%, then an 80%-confidence budget applies a 57% uplift** — **and publishing the
un-uplifted figure is CHOOSING roughly an 80% probability of overrun.**
**⚠️ Translated to software**: ⚠️ **your team's own history of similar completed projects
IS a reference class, and using it beats bottom-up estimation.** **This is the same
statistical move as Monte Carlo forecasting from historical cycle time** (see an
engineering-process reference).

> **⚠️ One honest caveat on the source.** ⚠️ **The Flyvbjerg database has been criticized
> in the peer-reviewed literature for not being openly available**, **which limits
> independent verification of the specific figures.** ⚠️ **Note also that other bodies
> measuring differently report less extreme numbers — PMI-derived figures put IT budget
> overruns around 27% on average with ~55% of projects meeting goals — because they
> aggregate projects of all sizes, and small projects perform better.** **⚠️ The
> qualitative finding (systematic optimism bias, fat-tailed IT outcomes, RCF as remedy) is
> robust and widely replicated; treat the precise percentages as contested.**

---
