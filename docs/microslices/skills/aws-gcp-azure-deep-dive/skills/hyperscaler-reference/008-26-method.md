---
id: skill-26-method-f82251813d
purpose: 26 method
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-reference/SKILL.md
requires: ["skill-25-quick-reference-e7e814c791"]
links: []
---

## §26. Method

**§1–§20 → `hyperscaler-framing-responsibility-identity-and-hierarchy`, `hyperscaler-networking-compute-containers-and-serverless`, `hyperscaler-storage-databases-analytics-and-observability`, `hyperscaler-cost-reliability-iac-lock-in-and-migration` rest on stable material** — **IAM models, resource hierarchies, network
architecture, service equivalences and cost mechanics** — **and none of it needed
verification.** ⚠️ **Service names churn (Azure AD → Entra ID, Synapse → Fabric) but the
underlying architecture is durable, which is why §20 is a capability table rather than a
feature comparison.**

**Two searches were run in August 2026**, on **egress pricing and the EU Data Act** and
**market position** — ⚠️ **the two areas where a 2024-vintage answer is now materially
wrong.**

**Confidence.** **High** in §1–§20 → `hyperscaler-framing-responsibility-identity-and-hierarchy`, `hyperscaler-networking-compute-containers-and-serverless`, `hyperscaler-storage-databases-analytics-and-observability`, `hyperscaler-cost-reliability-iac-lock-in-and-migration`. ⚠️ **§3 → `hyperscaler-framing-responsibility-identity-and-hierarchy` is the section I'd most want read** — **the
Entra/Azure-RBAC split, AWS's intersecting-policies-with-explicit-deny evaluation, and
GCP's additive inheritance are the three things that most reliably catch experienced
engineers moving between platforms**, **and they're structural rather than incidental.**

**High** in §21.1's sequence — **Google January 2024, AWS March 2024, Microsoft mid-March
2024, EU Data Act applicable 12 September 2025 with the full charge ban from 12 January
2027** — **which is consistent across many independent sources including a UK CMA
appendix.** ⚠️ **I've flagged hard that the exit waivers are far narrower than the
headlines suggest, because that's the part that actually determines whether you can act on
it.** **The DMA gatekeeper designation is reported expectation, not decided, and I've said
so.** ⚠️ **Specific per-GB rates are approximate and tiered; verify against pricing pages.**

⚠️ **§21.2 contains a disagreement I've flagged rather than resolved.** **Market share
figures vary by several points across sources, and reported AWS growth for the same period
ranged from 24% to 37% — a spread wide enough that at least some of it is measurement
error or definitional difference rather than reality.** ⚠️ **Microsoft doesn't disclose
Azure as a standalone revenue figure, so any Azure dollar number you see is an estimate.**
**I've given the most-cited Synergy figures, shown the range, and said to trust the
direction.** **The direction — Google gaining fast, AWS eroding through slower growth in a
rapidly expanding market, capacity constrained — is consistent everywhere and is the part
that affects architecture decisions.**

⚠️ **Sourcing caution**: **much of the cloud-comparison and egress material online is
published by vendors selling migration tooling, FinOps platforms, interconnect services or
competing storage** — **and the framing tends toward urgency about lock-in.** **The
underlying facts recur across independent sources including regulatory filings; the
"act now" framing around them is marketing.** **Where I could anchor on a regulator (the
CMA appendix, the Data Act dates) or a primary earnings release, I did.**
