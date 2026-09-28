---
id: skill-15-six-sigma-and-statistical-process-control-2127d6bdf2
purpose: 15 six sigma and statistical process control
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-industrial-engineering-queueing-toc-and-lean/SKILL.md
requires: ["skill-14-lean-and-the-toyota-production-system-6e9efebacd"]
links: ["skill-16-work-measurement-and-standard-work-9dbd0bcb3d"]
---

## §15. Six Sigma and Statistical Process Control

```
DMAIC          Define, Measure, Analyse, Improve, Control
⚠️ SIX SIGMA   3.4 defects per million opportunities (⚠️ with the
   conventional 1.5-sigma long-term shift baked in — the arithmetic
   surprises people who compute it from a normal table)
⚠️ CONTROL CHARTS  ⚠️ THE core tool, and the most transferable
   ⚠️ COMMON CAUSE variation = inherent to the process; reacting to it
      makes things WORSE (Deming's funnel experiment)
   ⚠️ SPECIAL CAUSE variation = something changed; investigate THIS
PROCESS CAPABILITY  Cp, Cpk — is the process capable of the spec at all?
```
> **⚠️ GOTCHA — the common-cause/special-cause distinction is the most useful idea here
> and software systematically violates it.** ⚠️ **Treating normal variation as a signal —
> asking why this sprint's velocity dipped, why last month's incident count rose — is
> TAMPERING, and Deming demonstrated it increases variation rather than reducing it.**
> **⚠️ Before reacting to a metric movement, establish whether it's outside the control
> limits.** **Most dashboard-driven management is tampering with a nice UI.**

**⚠️ Honest assessment of Six Sigma as a programme**: ⚠️ **the statistical tools are sound
and the belt-certification apparatus is largely organizational theatre.** **⚠️ It suits
high-volume repetitive processes with measurable defects; it fits software development
poorly because software work is not repetitive in the required sense — though it fits
software OPERATIONS (incidents, deploys, alerts) considerably better.**

---
