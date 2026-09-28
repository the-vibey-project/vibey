---
id: skill-24-misconceptions-55ea9e899a
purpose: 24 misconceptions
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-reference/SKILL.md
requires: ["skill-23-what-s-live-verified-august-2026-0e930df786"]
links: ["skill-25-numbers-9d93346e35"]
---

## §24. Misconceptions

| Misconception | Correction |
|---|---|
| Factor of safety means "build it twice as strong" | ⚠️ **A calibrated allowance for quantified uncertainty** (§3 → `civil-loads-safety-factors-materials-and-foundations`) |
| Modern design uses one global safety factor | ⚠️ **Partial factors on loads and resistances (LRFD)** (§3 → `civil-loads-safety-factors-materials-and-foundations`) |
| Strong and stiff are the same | ⚠️ **Different properties; serviceability is stiffness** (§4 → `civil-loads-safety-factors-materials-and-foundations`) |
| Failure is failure | ⚠️ **Ductile warns; brittle doesn't. Design for ductile** (§4 → `civil-loads-safety-factors-materials-and-foundations`) |
| Building codes are bureaucratic overhead | ⚠️ **An accumulated failure log with legal force** (§6 → `civil-codes-licensure-failure-analysis-and-construction`, §8 → `civil-codes-licensure-failure-analysis-and-construction`) |
| Software should just adopt building codes | ⚠️ **Look at DO-178C's cost. That's the price** (§6 → `civil-codes-licensure-failure-analysis-and-construction`) |
| Tacoma Narrows was resonance | ⚠️ **Aeroelastic flutter** (§8 → `civil-codes-licensure-failure-analysis-and-construction`) |
| Hyatt Regency was a maths error | ⚠️ **A detail change nobody re-analysed** (§8 → `civil-codes-licensure-failure-analysis-and-construction`) |
| Watch the critical path | ⚠️ **Watch the NEAR-critical paths too** (§9 → `civil-codes-licensure-failure-analysis-and-construction`) |
| Industrial engineering is about factories | ⚠️ **Systems of people, materials and information** (§11 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Little's Law is a useful analogy | ⚠️ **It's a theorem. It holds unconditionally** (§12 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| A fully-utilized team is efficient | ⚠️ **Queues explode near 100% utilization** (§12 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Speed up everyone to go faster | ⚠️ **Only the constraint matters** (§13 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Kanban means a board with columns | ⚠️ **A pull signal. The WIP limit is the point** (§14 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Lean means eliminating slack | ⚠️ **TPS buffers deliberately; heijunka levels demand** (§14 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| We adopted lean | ⚠️ **Did you adopt the andon cord? Usually not** (§14 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Investigate every metric dip | ⚠️ **That's tampering. Check the control limits first** (§15 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| Measure developer output like factory output | ⚠️ **Non-repetitive work. Taylorism fails here** (§16 → `civil-industrial-engineering-queueing-toc-and-lean`) |
| MTBF of 100,000 hours means it lasts 11 years | ⚠️ **It's a rate parameter, not a lifespan** (§19 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Improve reliability by raising MTBF | ⚠️ **Halving MTTR often helps as much, cheaper** (§19 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Ten 99.9% services give 99.9% | ⚠️ **Series multiplies: 99%** (§19 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Training and policy are strong controls | ⚠️ **Second-weakest tier. Eliminate instead** (§20 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Human error explains the incident | ⚠️ **It's where analysis starts** (§18 → `civil-reliability-safety-and-what-transfers-to-software`, §20 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Software isn't real engineering, so nothing transfers | ⚠️ **The mathematics transfers exactly** (§21 → `civil-reliability-safety-and-what-transfers-to-software`) |
| Software is engineering, so civil practice applies | ⚠️ **Seven real disanalogies** (§22 → `civil-reliability-safety-and-what-transfers-to-software`) |
| We're getting better at estimating | ⚠️ **Overruns roughly constant for 70 years** (§23.2) |
| IT projects are averagely risky | ⚠️ **Unremarkable mean, catastrophic tail** (§23.2) |
| Bottom-up estimation is more rigorous | ⚠️ **Reference class forecasting beats it** (§23.2) |

---
