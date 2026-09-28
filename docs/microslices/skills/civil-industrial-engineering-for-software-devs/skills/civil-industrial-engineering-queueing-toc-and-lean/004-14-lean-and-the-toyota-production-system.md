---
id: skill-14-lean-and-the-toyota-production-system-6e9efebacd
purpose: 14 lean and the toyota production system
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-industrial-engineering-queueing-toc-and-lean/SKILL.md
requires: ["skill-13-theory-of-constraints-c1173e078b"]
links: ["skill-15-six-sigma-and-statistical-process-control-2127d6bdf2"]
---

## §14. ⚠️ Lean and the Toyota Production System

**⚠️ What TPS actually is, as distinct from what software borrowed:**
```
⚠️ JIDOKA        ⚠️ automation WITH A HUMAN TOUCH — machines stop themselves
   on detecting a defect. ⚠️ The ANDON CORD: any worker can halt the line
JUST-IN-TIME     produce only what's needed, when needed
⚠️ HEIJUNKA      LEVEL the production schedule — smoothing variability (§12)
KANBAN           ⚠️ a physical PULL signal, not a board with columns
⚠️ KAIZEN        continuous small improvement BY THE PEOPLE DOING THE WORK
⚠️ THE 7 WASTES  overproduction, waiting, transport, over-processing,
   inventory, motion, defects
GENCHI GENBUTSU  ⚠️ "go and see" — decide at the actual place, not from a report
```
> **⚠️ GOTCHA — software's borrowing of "lean" dropped the two things that make it work.**
> ⚠️ **First, the ANDON CORD: TPS gives the lowest-status worker unconditional authority
> to stop production, and management's job is to come to them.** **Most software
> organizations that adopted "lean" did not adopt this, and the equivalent —
> stop-the-line on a broken build, or a junior engineer halting a release — is
> comparatively rare.**
> **⚠️ Second, HEIJUNKA: TPS goes to enormous lengths to LEVEL demand variability, because
> §12 says variability is what creates queues.** **Software's version of lean typically
> accepts wildly variable batch sizes and then wonders why flow is poor.**
> **⚠️ And note the misreading of "waste": eliminating slack is not lean.** ⚠️ **TPS runs
> buffers deliberately where variability requires them** — **removing all slack raises
> utilization toward the cliff in §12.**

**⚠️ Where lean genuinely transferred well**: **⚠️ small batch sizes, pull rather than push,
making work visible, and reducing handoffs** — **all of which are §12 and §13 in
practice.**

---
