---
id: skill-21-what-moved-verified-august-2026-88c6f1660d
purpose: 21 what moved verified august 2026
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-reference/SKILL.md
requires: ["skill-20-service-equivalence-f4861e878c"]
links: ["skill-22-misconceptions-0fcd67b324"]
---

## §21. What Moved — verified August 2026

### 21.1 ⚠️ Egress pricing and the EU Data Act — the lock-in economics changed
**⚠️ This is the most consequential structural change in cloud economics in years, and
it's under-appreciated because it happened through regulation rather than product.**

**What happened, in sequence:**
- **⚠️ Google moved first, in January 2024**, becoming **the first provider to stop
  charging egress fees for customers switching away.**
- **AWS followed in March 2024, waiving data transfer out to the internet for customers
  leaving** — **noting that over 90% of its customers already pay nothing for egress
  under the 100 GB monthly free allowance.**
- **Microsoft completed the set in mid-March 2024** with free egress for customers leaving
  Azure.
- **⚠️ The EU Data Act is the driver.** **It came into force 11 January 2024 and became
  applicable 12 September 2025**, and ⚠️ **it bans cloud switching and egress charges
  outright from 12 January 2027**, following the transition period.
- **In September 2025 Google went further with Data Transfer Essentials**, offering
  **zero-cost ongoing multi-cloud transfers for eligible EU and UK intra-organisation
  traffic** — **beyond the Act's minimum of at-cost pass-through.**
- **⚠️ In 2026 the ground shifted again**: **AWS Interconnect for multicloud reached
  general availability in April with Google Cloud as its first partner, followed in May
  by a free 500 Mbps interconnect tier per region with no per-gigabyte charges on the
  connection.**
- **⚠️ Regulatory pressure moved from anticipated to actual**: **the European
  Commission's own Digital Markets Act page confirms a preliminary determination,
  published 25 June 2026, that AWS and Azure should be designated "gatekeepers"** — the
  first time the DMA has reached cloud infrastructure rather than consumer platforms.
  ⚠️ **Secondary reporting, not confirmed on the Commission's own page, puts the
  companies' deadline to submit written representations at September 2026 and a final
  decision around October 2026.**

> **⚠️ GOTCHA — read the fine print, because the headlines overstate this considerably.**
> ⚠️ **The exit waivers are narrow: they generally require a FULL exit, notification of
> intent, account termination, completion within a limited window (reported at 60 days),
> and credits applied only AFTER the transfer completes.** **Partial migrations are
> case-by-case.** **⚠️ And none of this touches ORDINARY egress**, which is what most
> organizations actually pay.

**⚠️ Ordinary egress rates, as reported for 2026 — treat as approximate and verify against
current pricing pages:**
```
Internet egress (entry tier)  ⚠️ ~$0.09/GB AWS · ~$0.087/GB Azure ·
                              ~$0.12/GB GCP Premium Tier
                              ⚠️ Tiered — falls as monthly volume rises
Inter-region                  ⚠️ commonly ~$0.02/GB
Cross-AZ                      ⚠️ commonly ~$0.01/GB — and this one surprises people (§14)
Ingress                       ⚠️ free on all three
Zero-egress alternatives      Cloudflare R2, Backblaze B2, Wasabi at $0
```
**⚠️ Also worth knowing**: **AWS charges hourly for public IPv4 addresses (reported at
$0.005/hour)**, ⚠️ **so IPv6 adoption eliminates both that charge and the NAT gateway it
often implies** — **one of the larger easy wins available.** **And Google raised peering
egress rates on 1 May 2026** (**North America roughly doubling on CDN Interconnect, Direct
and Carrier Peering**), **while standard internet egress was unchanged** — ⚠️ **a reminder
that the direction of travel isn't uniformly downward.**

**⚠️ Why this matters strategically**: **exit costs were a genuine lock-in mechanism and a
distortion in every cloud-vs-on-prem TCO comparison.** ⚠️ **Removing them by 2027 makes
repatriation and hybrid strategies more viable, and strengthens your negotiating position
whether or not you ever move** (§17 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`, §18 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`).

### 21.2 ⚠️ The competitive position shifted — AI capacity is the driver
**⚠️ The stable "AWS then Azure then a distant Google" picture is no longer accurate, and
the cause is AI infrastructure demand.**

> **⚠️ GOTCHA — market share figures disagree meaningfully between sources and I'm not
> going to pretend otherwise.** ⚠️ **For Q1/Q2 2026 I found AWS reported at 28%, 29% and
> 30%; Azure at 20%, 21% and 24%; Google Cloud at 13%, 14% and 15%.** **Synergy Research
> Group is the most commonly cited source and puts Q1 2026 at roughly AWS 28% / Azure 21%
> / Google 14%.** ⚠️ **Methodologies differ on what counts as "cloud infrastructure," and
> Microsoft does not report Azure revenue as a standalone dollar figure at all — Azure
> dollar figures in circulation are analyst estimates applied to disclosed growth rates.**
> **Trust the direction, not the decimal.**

**⚠️ The direction is consistent across every source:**
- **⚠️ Google Cloud is the share gainer.** **Reported at $24.8B revenue in Q2 2026, up 82%
  year over year and accelerating from 63% the prior quarter.** **Operating income
  reported at $8.8B on a ~35.6% margin** — ⚠️ **a business that turned its first profit
  in 2023.**
- **⚠️ The backlog number is the most forward-looking figure in the data**: **Google
  Cloud's sales backlog reported at $514B, up from around $106B a year earlier.**
  **These are multi-year contracted commitments that convert to revenue slowly.**
- **Azure grew roughly 40% for two consecutive quarters.** **AWS remains much the largest
  by revenue** — ⚠️ **though reported AWS growth figures for the same period range from
  24% to 37% across sources, which is a larger spread than it should be and another reason
  to treat these numbers as directional.**
- **AWS's share has eroded gradually from 31–32% in 2022–2023** — ⚠️ **through slower
  growth, not decline.** **The market is expanding fast enough that everyone is growing.**
- **Omdia put Q4 2025 cloud infrastructure spending at $110.9B, up 29%** — **the sixth
  consecutive quarter above 20% growth** — **and forecast 27% growth for 2026.**

**⚠️ The operationally relevant consequence, which matters more than the share table:**
**capacity is constrained.** ⚠️ **Google explicitly cited capacity constraints as a
limiting factor in Q1 2026.** **Enterprises are signing long-term deals to lock in compute
years ahead.** **In practice this means: GPU and accelerator availability varies by region,
quota requests are real gating items, and capacity commitments are increasingly part of
enterprise negotiations** (§12 → `hyperscaler-storage-databases-analytics-and-observability`). ⚠️ **Architect on the assumption that the accelerator you
want may not be available in the region you want it in.**

**⚠️ A second-order consequence worth naming**: **hyperscaler capex is now large enough to
make electricity access a strategic constraint on cloud growth**, **tying region
availability and expansion timelines to grid capacity** (see a power engineering reference
§12).

---
