---
id: skill-ruthless-scope-reduction-e1adb5cc3e
purpose: ruthless scope reduction
source: src/vibey_tools/skills/plugins/agile-delivery/skills/delivery-velocity/SKILL.md
requires: ["skill-core-thesis-fix-time-vary-scope-e6e77d10f1"]
links: ["skill-wsjf-weighted-shortest-job-first-7d77493bd3"]
---

## Ruthless Scope Reduction

### The Feature Utilization Evidence

The evidence on feature utilization is damning:
- **Standish Group**: 64% of features are rarely or never used; **45% are never used at all**
- **Pendo 2019** (hundreds of software products): **80% of features are rarely or never used**; only **12% of features generate 80% of daily usage**

Every feature not built is delivery capacity reclaimed for features that matter.

### Lean Startup Validation

Camuffo et al.'s 2020 RCT — the most rigorous study ever conducted on Lean Startup methodology — tested scientific hypothesis-driven development across 116 Italian startups. The treatment group achieved **statistically significant shorter time to revenue** (P<0.05, Cox proportional hazard model), pivoted faster, and terminated unviable ideas earlier.

A 2024 replication across **759 firms in four RCTs** (Milan, Turin, London, Torino) confirmed these results. The mechanism: disciplined hypothesis testing prevents teams from building features nobody needs.

### Ruthless Scoping Process

1. **Identify the 12%** — for every proposed feature, ask "will this drive daily usage?" If not, cut it from the MVP
2. **Write a hypothesis** for every remaining feature: "We believe [feature] will [behavior change] for [user type]. We will know this is true when [measurable outcome]."
3. **Apply WSJF** to rank the remaining backlog (see below)
4. **Cap Must-Haves at 60% of sprint effort** — the remaining 40% is release pressure relief
5. **Question every Should-Have**: most Should-Haves become Could-Haves or are dropped under time pressure

---
