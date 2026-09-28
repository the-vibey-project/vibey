---
id: skill-2-the-provider-landscape-aaf38a3bc3
purpose: 2 the provider landscape
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-models-providers-and-primitives/SKILL.md
requires: ["skill-1-models-a7ef649f53"]
links: ["skill-3-the-primitives-6e343867d6"]
---

## §2. The Provider Landscape

**[VERSIONED — and read the ⚠️ in this section before quoting any number.]**

**Market structure as of Q1 2026**: the Big Three hold roughly **60–68%** of global cloud
infrastructure spend, with the market reaching **~$129B in Q1 2026, growing ~35% YoY** —
described as the **ninth consecutive quarter of increasing year-over-year growth**.

> **⚠️ GOTCHA — the share figures genuinely conflict across sources, and you should know
> why before citing them.** Synergy Research puts Q1 2026 at **AWS 28%, Azure 21%, Google
> Cloud 14%**. Other widely-circulated figures give **AWS 30% / Azure 24–25% / GCP 13%**,
> and others still **AWS 32% / Azure 23% / GCP 11%**.
>
> **The discrepancy is methodological, not an error.** One analysis explains it directly:
> Azure's higher share estimates **exceed a straight revenue calculation because Synergy
> weights IaaS-and-PaaS spend, where Azure is stronger** — and separately, **Microsoft
> does not break out Azure revenue at all, only its growth rate**, so any "Azure revenue"
> figure is derived. **Both kinds of figure are valid; they measure different scopes.**
> **Cite the source and the scope, or don't cite the number.**

**Growth is the more interesting story than share**: Azure and Google Cloud have been
growing substantially faster off smaller bases, with Google Cloud posting the highest rates
of the three. **AI is the driver** — AI-related spending was reported at **~19% of total
cloud spend in 2026, up from ~8% in 2023.**

**⚠️ The capex arms race is the structural fact underneath all of it.** 2026 guidance
figures in circulation: **Amazon ~$200B, Microsoft ~$190B, Alphabet ~$180–190B.** This
functions as a moat — the cost of building global infrastructure excludes almost everyone
— and it carries genuine risk: **the Big Three are betting hundreds of billions that AI
demand will justify the build-out, and if it disappoints the write-downs would be
enormous.** For a buyer, large capex commitments are **both a supply signal and a
lock-in signal.**

**Choosing** — the honest criteria, roughly in order: **existing skills and contracts**
(⚠️ **usually decisive and rarely stated**), **the specific services you need**,
**regional and data-residency footprint** (§11 → `cloud-migration-sovereignty-and-ai-workloads`), **pricing for your actual shape of
workload**, **enterprise agreements and discounts**, and **regulatory posture**.
**Beyond the Big Three**: Oracle Cloud, IBM, Alibaba, and the **"neoclouds"** — GPU-focused
providers (CoreWeave, Lambda and others) estimated collectively at a small but real share
segment. **Cloudflare, Fastly, Vercel, Fly.io** for edge; **DigitalOcean, Hetzner,
Scaleway** for straightforward compute at markedly lower prices.

---
