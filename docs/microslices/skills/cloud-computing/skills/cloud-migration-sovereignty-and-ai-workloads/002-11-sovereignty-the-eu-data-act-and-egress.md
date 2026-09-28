---
id: skill-11-sovereignty-the-eu-data-act-and-egress-2a3eecc79a
purpose: 11 sovereignty the eu data act and egress
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-migration-sovereignty-and-ai-workloads/SKILL.md
requires: ["skill-10-migration-a72474a0b5"]
links: ["skill-12-multi-cloud-and-lock-in-45b76b10cb"]
---

## §11. Sovereignty, the EU Data Act, and Egress

**[VERSIONED — and §11.2 contains the most consequential dated fact in this document.]**

### 11.1 Data residency vs. sovereignty

**⚠️ The distinction that most organizations get wrong**, and one 2026 analysis names it
directly as **"the residency illusion" — the belief that a local data center footprint
satisfies sovereignty.** It doesn't.

- **Residency** — the data physically sits in region X.
- **Sovereignty** — **no foreign jurisdiction can compel access to it.**

**The gap is legal, not technical**: **US providers remain subject to US legal demands
under the CLOUD Act regardless of where the data sits**, which sits in tension with EU
sovereignty principles and GDPR Article 48. **A Frankfurt region does not solve this by
itself.** What narrows the gap: customer-managed keys with hold-your-own-key
arrangements, confidential computing, EU-operated sovereign offerings, and architectures
where the **provider cannot access unencrypted data** rather than merely promising not to.

### 11.2 ⚠️ The EU Data Act — the January 2027 deadline

**Regulation (EU) 2023/2854.** Entered into force 11 January 2024; **switching provisions
applicable from 12 September 2025**; **the critical date is 12 January 2027.**

| Date | What |
|---|---|
| **12 Sept 2025** | Cloud switching rights became **enforceable** across the EU — portability and switching-support obligations live |
| **Sept 2025 → Jan 2027** | Transition. Switching and egress charges permitted **only at direct, transparent, pre-agreed cost** — not exceeding costs directly incurred |
| **12 Sept 2026** | Products released after this date must be designed so **user data is accessible by default** |
| **⚠️ 12 January 2027** | **All switching charges, including data egress fees, are banned outright** for in-scope providers serving EU customers — **IaaS, PaaS and SaaS alike**, and **for every provider serving EU customers, not only European ones** |

**What remains chargeable**: standard service and subscription fees, proportionate early
termination fees on fixed-term contracts, and genuinely optional premium migration
services. **⚠️ Expect providers to move residual switching cost into base pricing** —
industry observers anticipated exactly this during the transition window.

**Enforcement** is delegated to **national authorities designated by each member state**,
with **penalties set in local legislation** — so they vary across the EU, though the Act
requires them to be effective.

> **⚠️ GOTCHA — three things to act on now.** **(1) The deadline is 12 January 2027, not
> 2026** — a commonly muddled point. **(2) Contracts do not auto-fix themselves**:
> auto-renewal clauses and migration-fee terms must be actively reviewed or the old cost
> structure stays in force. **(3) The fee was only the most visible lock-in.**
> **Proprietary APIs, vendor-specific data formats, and IAM binding keep you locked in
> long after the invoice line disappears** — six months' lead time is barely enough for
> serious exit planning.

**Note also**: AWS, Azure and Google **already waived egress fees for full exits in 2024**,
ahead of the regulation — but that is narrower than what 2027 requires. And the **DMA is
separately investigating AWS and Azure as potential gatekeepers**, which would add
interoperability obligations; **⚠️ analysts have flagged genuine friction between the two
regimes**, including conflicting compliance timelines and split enforcement (member states
for the Data Act, the Commission for the DMA).

**[VERSIONED] On 3 June 2026 the European Commission proposed the Cloud and AI Development
Act** as part of a Tech Sovereignty Package, proposing an **EU-wide method for assessing
how sovereign a cloud or AI service actually is, with graded levels for public-sector
providers.** ⚠️ **Still to pass Parliament and Council — details will change** — but the
direction is that "sovereign cloud" becomes a regulated standard rather than a sales claim.

### 11.3 Egress in practice

**[DURABLE] Data transfer pricing is asymmetric by design**: ingress free, egress charged,
**cross-AZ and cross-region transfer charged**, and internet egress most expensive.

**The architectural responses**: keep compute next to data; **use CDN for repeated
external delivery**; be deliberate about cross-AZ chatter (⚠️ **a chatty microservice mesh
spanning AZs is a recurring surprise line item**); use private endpoints; consider
providers with different egress models for egress-heavy workloads.

---
