---
id: skill-31-method-730408f990
purpose: 31 method
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-reference/SKILL.md
requires: ["skill-30-quick-reference-f7c9c240cd"]
links: []
---

## §31. Method

**§1–§24 → `logistics-why-projects-fail-complexity-and-modeling`, `logistics-constraint-programming-metaheuristics-and-bounds`, `logistics-routing-packing-scheduling-and-network-design`, `logistics-inventory-forecasting-operations-and-solvers` and §26–§30 rest on stable material** — **complexity theory, LP/MIP/CP,
metaheuristics, the classical OR problem family, inventory theory and warehouse
science** — sourced from §29. ⚠️ **None of it needed verification; Dijkstra, Held-Karp,
the newsvendor result and branch-and-bound are not going to change.**

**Two searches were run in August 2026**, on **the solver landscape** and **quantum/AI
optimization claims** — ⚠️ **one because the buy-vs-open-source decision genuinely
shifted, and one because it's where practitioners are currently being mis-sold.**

**Confidence.** **High** in §1 → `logistics-why-projects-fail-complexity-and-modeling`, which is the section I'd most want read and the one that
is least present in textbooks. ⚠️ **The claim that these projects fail on data, hidden
constraints and trust rather than on algorithms is a position, and I've presented it as
an ordered judgement rather than a measured finding** — **but the stability requirement,
the need for a feasibility checker independent of the optimizer, and the soft-constraints
recommendation in §5 → `logistics-why-projects-fail-complexity-and-modeling` are the three things I'd defend hardest.**

**High** in §2 → `logistics-why-projects-fail-complexity-and-modeling`'s framing. ⚠️ **"NP-hard ≠ unsolvable" is the correction that most changes
how a software engineer approaches this domain**, **and the practical difficulty drivers
(interacting constraints, tight time windows) matter far more than instance size.**

**Moderate-to-high** in §25.1's specifics. ⚠️ **The ~20× HiGHS-vs-commercial figure and
the "one order of magnitude, not two" framing come from 2025–26 analysis referencing
Mittelmann benchmarks, and I've attributed rather than asserted them.** **The Gurobi
(August 2024) and MindOpt (December 2024) benchmark withdrawals are reported, and the
interpretation offered — that withdrawal signals unflattering results or gamed methodology
— is one commentator's read, which I've labelled as such.** ⚠️ **The structural point is
more reliable than any number: commercial licences often restrict published benchmarking,
which is why GAMS uses anonymized "virtual commercial solver" baselines — so treat all
public rankings as weakly predictive and benchmark your own models.**

**High** in §25.2's sceptical read, and this is the section I'd stand behind most firmly
against the surrounding marketing. ⚠️ **The decisive evidence is a peer-reviewed
systematic review finding that most quantum transport-optimization studies "rely on
synthetic datasets, lack statistical robustness, and omit critical operational
metrics."** **The hardware limits — ~30 binary variables for circuit-model testing, a few
hundred for annealer embedding — come from the technical literature including the QC Ware
paper, which is notably candid about them.** ⚠️ **I've deliberately contrasted that honest
work against the analyst claims of 40–60% cost reductions, and flagged that the latter
don't come from operational deployments.**

⚠️ **Sourcing caution**: **solver vendors publish benchmarks showing they win; quantum
vendors and analysts publish projections showing transformation.** **Where I could anchor
on peer-reviewed work, a systematic review, or a neutral party (the GAMS benchmark
methodology, arXiv comparisons), I did.** ⚠️ **The LLM-as-interface point in §25.2 is my
own synthesis — that the promising direction targets §1 → `logistics-why-projects-fail-complexity-and-modeling`'s failure modes rather than solve
time — and I'd flag it as an argument rather than a finding.**
