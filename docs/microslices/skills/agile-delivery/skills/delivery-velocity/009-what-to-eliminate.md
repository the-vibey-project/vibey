---
id: skill-what-to-eliminate-41a9561f7f
purpose: what to eliminate
source: src/vibey_tools/skills/plugins/agile-delivery/skills/delivery-velocity/SKILL.md
requires: ["skill-decision-latency-the-1-delivery-killer-4164f4ab7a"]
links: ["skill-contract-structure-for-velocity-06707ba4b7"]
---

## What to Eliminate

The research converges on a clear list of delivery-killing practices. Each has specific evidence showing negative throughput impact.

| Practice | Evidence | Replace With |
|---|---|---|
| **Change Advisory Boards** | 2.6× more likely to be low performer (DORA 2019); no compensating stability benefit | Peer review (PRs) + automated deployment gates |
| **Large batch sizes** | 88% error probability at 25-change batch; quadratic debugging complexity (Reinertsen) | 1–3 day work items; daily trunk merges |
| **Large teams (7+)** | 3–4× more effort; 2–3× more defects (QSM) | Single team of 5 ± 2 |
| **Fixed-scope contracts** | 66% of technology projects end in partial/total failure (CHAOS 2020) | Fixed-time/variable-scope with 2-week billing cycles |
| **Heavy upfront documentation** | Waterfall creates 80% overhead (Standish); Agile halves overhead | Working software as primary artifact + lightweight ADRs |
| **Long-lived feature branches** | Merge complexity requiring stabilization periods | Trunk-based development; branches ≤3 days |
| **High capacity utilization (>80%)** | Reinertsen: high utilization in variable systems increases cycle time exponentially | Maintain **15–20% slack** in team capacity |
| **Annual/quarterly planning cycles** | Institutionalize large batch thinking | Continuous prioritization at each iteration boundary |
| **CAB-style governance** | DORA: "Approval by an external body simply doesn't work to increase the stability of production systems. However, it certainly slows things down." | Automated quality gates + peer review |

---
