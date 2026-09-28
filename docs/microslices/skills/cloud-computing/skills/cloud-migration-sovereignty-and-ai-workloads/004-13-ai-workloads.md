---
id: skill-13-ai-workloads-8cb59c9637
purpose: 13 ai workloads
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-migration-sovereignty-and-ai-workloads/SKILL.md
requires: ["skill-12-multi-cloud-and-lock-in-45b76b10cb"]
links: ["skill-14-sustainability-eff16ba1f7"]
---

## §13. AI Workloads

**[VERSIONED — the fastest-moving economics in cloud right now.]**

**⚠️ AI has broken the cost assumptions that FinOps was built on**, and the numbers make
the point: **GPUs reportedly make up ~18% of spend at AI-forward organizations, up from
~4% in 2023**, and **statically provisioned GPU fleets run at only 30–40% utilization.**
**Idle accelerators are the fastest-growing waste category and the most expensive per
hour.** **AI cost management is now cited as the top FinOps priority (98% of practitioners
in the 2026 FinOps Foundation survey), and the most-wanted skillset.**

**What's structurally different from conventional workloads:**
- **Training** is bursty, enormous, and interruption-tolerant — **⚠️ a near-perfect fit
  for spot/preemptible capacity that is widely under-exploited.**
- **Inference** is steady-state and latency-sensitive; economics are dominated by
  utilization and batching.
- **⚠️ Capacity, not price, is often the binding constraint.** Reservations and
  capacity blocks matter more than hourly rate.
- **⚠️ Forecasting is structurally harder** — which is precisely why Flexera attributes the
  waste reversal to AI outpacing existing tagging and attribution practice (§7.1 → `cloud-cost-security-and-operations`).
- **Data gravity intensifies.** Training data is enormous; moving it is expensive; **this
  is a lock-in force as much as a cost one.**
- **Token-based pricing for managed model APIs is a genuinely different cost model** —
  per-request, variable by output length, and easy to lose control of.

**[DURABLE] The engineering responses**: track **cost per training run and cost per
inference/token**; use spot for training with checkpointing; batch and cache inference;
right-size the model to the task; and **attribute AI spend to teams and features from day
one** — retrofitting attribution is what the 2026 waste numbers are measuring.

---
