---
id: skill-16-contested-questions-e5029064d0
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-reference/SKILL.md
requires: ["skill-15-anti-patterns-e8cb9db57b"]
links: ["skill-17-currency-snapshot-verified-august-2026-1ee5929748"]
---

## §16. Contested Questions

**16.1 Is cloud cheaper than on-prem?** *For*: no capex, elastic, no datacenter staff,
you pay for what you use. *Against*: at **steady, predictable, high utilization**, owned
hardware is frequently cheaper — and that's exactly the profile that gets repatriated.
**[CONTESTED, and the honest answer is workload-dependent.]** The 2026 data supports a
middle reading: **~21% of workloads repatriated, but new cloud workloads outstrip the
exits.** ⚠️ **From 2027 the EU removes exit-cost distortion from this comparison, which
means the TCO math should genuinely be re-run** rather than assumed.

**16.2 Is repatriation a real trend or vendor noise?** Real but bounded. **Selective
repatriation of steady-state, high-utilization workloads is happening**, driven partly by
FinOps tooling finally making the comparison visible. **Wholesale cloud exit is not.**

**16.3 Multi-cloud: insurance or expensive complexity?** §12 → `cloud-migration-sovereignty-and-ai-workloads`. The 2025 outages strengthened
the resilience argument; the operational reality strengthened the complexity argument.
**Both got more true at once.**

**16.4 Is Kubernetes over-adopted?** **[CONTESTED but leaning yes.]** Excellent at scale
with a platform team, poor fit below that, and adopted for reasons that are often about
résumés and perceived sophistication rather than requirements.

**16.5 Does serverless deliver?** *For*: genuinely excellent for event-driven, spiky, and
low-volume workloads; operational burden near zero. *Against*: cost inversion at sustained
volume, cold starts, testing friction, vendor coupling. **The pendulum settled around
"right tool for specific shapes" rather than a default.**

**16.6 Is sovereign cloud meaningful or theatre?** *For*: the CLOUD Act tension is real
and residency genuinely doesn't solve it. *Against*: much of what's marketed as sovereign
is residency with extra branding. **⚠️ The EU's proposed Cloud and AI Development Act
(June 2026) is an attempt to settle this by defining graded sovereignty levels** — which
is itself an admission that the term is currently unregulated marketing.

**16.7 Are the hyperscalers over-building for AI?** ⚠️ **Genuinely unknown, and the stakes
are large.** ~$570B+ of combined 2026 capex guidance is a bet that AI demand
materializes. Revenue growth currently supports it. **If it disappoints, the write-downs
would be historically large** — and buyers should factor that uncertainty into
long-horizon commitments.

---
