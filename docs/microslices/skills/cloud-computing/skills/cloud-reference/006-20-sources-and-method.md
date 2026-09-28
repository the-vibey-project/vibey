---
id: skill-20-sources-and-method-c43fb684f6
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-reference/SKILL.md
requires: ["skill-19-quick-reference-5a6fcfd895"]
links: []
---

## §20. Sources and Method

**Method.** Narrative review. The architectural material — §1 → `cloud-models-providers-and-primitives`, §4 → `cloud-architecture-and-resilience`, §6.3 → `cloud-architecture-and-resilience`'s principles, §8 → `cloud-cost-security-and-operations`,
§9 → `cloud-cost-security-and-operations`, §10 → `cloud-migration-sovereignty-and-ai-workloads`, §15 — rests on the provider Well-Architected frameworks, SRE literature, and
long-stable practice, and does not move much. **The economics, market structure, and
regulation move fast**, and those were verified in **August 2026** with four targeted
searches; every such claim is flagged **[VERSIONED]** and carries a decay rating in §17.

**Search log** (August 2026): cloud market share and AI capex · EU Data Act cloud
switching, egress fees, and sovereignty · the October–November 2025 outages and resilience
lessons · FinOps, cloud waste, and repatriation.

**Primary and near-primary sources consulted (selected):**
- **Market**: Synergy Research figures as reported via Statista and multiple trackers;
  Omdia's Q4 2025 cloud infrastructure analysis; company earnings coverage (Amazon,
  Microsoft, Alphabet Q1 2026). **⚠️ The methodological explanation for the divergent share
  figures came from a tracker that showed its working** — I've reproduced the reasoning
  rather than picking a number
- **EU Data Act**: legal analyses from **Alston & Bird**, **McCann FitzGerald**,
  **Kemp IT Law**, **CMS**, and **Turing Law** for the switching-charge provisions,
  transition rules, and enforcement structure; **CSIS** for the Data Act / DMA friction
  analysis; contemporaneous coverage for the June 2026 Cloud and AI Development Act
  proposal
- **Outages**: incident analyses from **Cockroach Labs' 2025 outage review**,
  **DevOps.com**, **Datacenter Knowledge**, **INE**, and independent write-ups; AWS's own
  post-mortem as reported. **⚠️ I did not read the provider post-incident reports directly**
- **FinOps**: **Flexera *State of the Cloud* 2026** (n=753) via its own materials and
  secondary reporting; **FinOps Foundation *State of FinOps* 2026**; CIO Dive's coverage of
  the repatriation and waste figures

**Confidence statement.** **High confidence** in §1 → `cloud-models-providers-and-primitives`, §3–§5 → `cloud-models-providers-and-primitives`, `cloud-architecture-and-resilience`, §6.2 → `cloud-architecture-and-resilience`–6.3, §8–§10 → `cloud-cost-security-and-operations`, `cloud-migration-sovereignty-and-ai-workloads`, §15 — these
are architectural principles and widely-corroborated practice. **High confidence in the
EU Data Act dates and structure** in §11.2 → `cloud-migration-sovereignty-and-ai-workloads`, which came from multiple independent legal
analyses agreeing on the 12 September 2025 and **12 January 2027** dates; the Regulation
number and text are checkable at EUR-Lex and I'd recommend doing so before relying on it
commercially. **High confidence in the outage facts** in §6.1 → `cloud-architecture-and-resilience`, which are consistently
reported across many independent sources, though **root-cause descriptions are
summarized from secondary analyses rather than from the provider post-incident reports
themselves.**

**⚠️ Lower confidence, deliberately flagged, on the numbers.** **Market share figures
genuinely conflict by 4+ percentage points across reputable sources for methodological
reasons I've explained in §2 → `cloud-models-providers-and-primitives`** — treat any single figure as directional. **Capex figures
are company guidance, not actuals.** **Waste, repatriation, and GPU-utilization figures
are survey-based** (Flexera n=753, FinOps Foundation n≈523 for some measures), carry
self-report bias, and vary between surveys — Harness reported ~21% waste against Flexera's
29% in overlapping periods. **The us-east-1 concentration figures (~69% of usage, 44%+ of
requests) come from different methodologies measuring different things** and should not be
combined. Several FinOps-adjacent sources are **vendor-published with an obvious interest
in the size of the problem they sell tooling for**, which I've weighted accordingly. §16 is
opinion labelled as such.
