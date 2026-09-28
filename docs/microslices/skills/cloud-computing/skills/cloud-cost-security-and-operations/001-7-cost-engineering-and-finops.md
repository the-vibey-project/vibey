---
id: skill-7-cost-engineering-and-finops-47ea9ba516
purpose: 7 cost engineering and finops
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-cost-security-and-operations/SKILL.md
requires: []
links: ["skill-8-security-and-shared-responsibility-2efeb1bbef"]
---

## §7. Cost Engineering and FinOps

**[VERSIONED in figures, DURABLE in method.]**

### 7.1 The state of it

**⚠️ Cloud waste reversed a five-year improving trend in 2026.** Flexera's 2026 *State of
the Cloud* (n=753 cloud decision-makers, 15th edition) estimates **29% of IaaS/PaaS spend
is wasted, up from 27%** — with the reversal **attributed largely to AI adoption
outpacing the tagging, attribution, and governance practices FinOps teams had built for
predictable workloads like VMs and storage.**

Other 2026 findings worth knowing: **managing cloud spend is the top priority (84%),
surpassing security**; **FinOps team prevalence ~63%** and **Cloud Centers of Excellence
~71%**; **fewer than half of organizations use any one commitment discount per provider**
(⚠️ **that is free money left on the table**); and **~21% of workloads have been
repatriated**, though **new cloud workloads outstrip the exits, so cloud continues to
grow.**

**⚠️ The nature of the work has shifted, and this matters for expectation-setting**:
practitioners consistently report that **the large, obvious waste has already been
addressed** — what remains is **smaller savings distributed across more workloads,
requiring deeper analysis and tighter engineering collaboration.** More respondents now
prioritize governance, forecasting, and organizational alignment over pure optimization.

### 7.2 Where the money actually goes wrong

| Cause | Fix |
|---|---|
| **Idle and zombie resources** | Scheduled shutdown for non-prod; automated detection |
| **Over-provisioning** | Right-size continuously against real utilization |
| **⚠️ Orphaned storage** — detached volumes, old snapshots past any retention policy | Lifecycle policies (§3 → `cloud-models-providers-and-primitives`) |
| **No commitment coverage** | Reserved instances / savings plans on your stable baseline |
| **Not using spot** | ⚠️ 60–90% cheaper for interruptible work |
| **Egress and cross-AZ transfer** | ⚠️ **Frequently the invisible line item** (§11 → `cloud-migration-sovereignty-and-ai-workloads`) |
| **Wrong storage class** | Tiering (§3 → `cloud-models-providers-and-primitives`) |
| **Untagged resources** | ⚠️ **You cannot allocate what you cannot attribute** |
| **⚠️ Idle GPUs** | §13 → `cloud-migration-sovereignty-and-ai-workloads` — the fastest-growing waste category |

**[DURABLE] The FinOps method**: **Inform** (visibility, tagging, allocation, showback) →
**Optimize** (rightsizing, commitments, architecture) → **Operate** (governance,
forecasting, continuous improvement). **Federated model** — a small central team enabling
embedded champions, because **central teams cannot scale by headcount.**

**[VERSIONED] FOCUS** (FinOps Open Cost and Usage Specification) standardizes cost and
usage data across providers, addressing the normalization problem as FinOps expands to
cover SaaS, licensing, Kubernetes, and data platforms.

**⚠️ The measure that changes behaviour: unit economics.** Cost per transaction, per
customer, per feature — **not the aggregate bill.** An aggregate that goes up is
ambiguous; a cost-per-order that goes up is a bug.

**[DURABLE] And the engineering point**: cost is set at design time. **The three
decisions that dominate are data placement (egress), service selection (managed vs.
self-run), and the commitment/spot mix.** Everything after that is optimization at the
margins.

---
