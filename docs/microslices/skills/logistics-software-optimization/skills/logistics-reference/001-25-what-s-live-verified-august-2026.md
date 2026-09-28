---
id: skill-25-what-s-live-verified-august-2026-c2fd83c536
purpose: 25 what s live verified august 2026
source: src/vibey_tools/skills/plugins/logistics-software-optimization/skills/logistics-reference/SKILL.md
requires: []
links: ["skill-26-anti-patterns-b8c3562f0a"]
---

## §25. What's Live — verified August 2026

### 25.1 ⚠️ The solver landscape
**⚠️ The commercial/open-source gap narrowed, the benchmark situation got murkier, and
GPUs entered LP.**

- **⚠️ The gap is roughly one order of magnitude, not two.** **Analysis in 2025–26 puts
  HiGHS at about 20× slower than the top commercial solvers on Mittelmann benchmarks** —
  ⚠️ **and explicitly notes this is "not the 'two orders of magnitude' that sales
  engineers love to claim."** **The framing worth carrying: ⚠️ "20× slower than
  instantaneous" is still instantaneous for many real applications.**
- **⚠️ HiGHS has become the default open-source choice** — **commercial-grade enough for
  many workloads without licensing complexity** — **and SCIP remains strong (check its
  licence terms for your use case).**
- **⚠️ COPT (Cardinal Optimizer) is a genuine competitor to Gurobi and CPLEX**, **and
  benchmark reports have it leading on several problem categories.** **The commercial
  field is no longer a two-horse race.**

> **⚠️ GOTCHA — the benchmark landscape itself became less trustworthy, and you should
> know this before quoting anyone's numbers.** ⚠️ **Gurobi withdrew from Hans Mittelmann's
> widely-cited benchmarks in August 2024, followed by MindOpt in December.** **One
> commentator's read: when solvers start avoiding public benchmarks it usually means
> either the results aren't flattering or the methodology has been gamed.**
> ⚠️ **Note also that commercial solver licences frequently restrict published
> benchmarking** — **the GAMS MIPfeas benchmark works around this by grouping COPT, CPLEX
> and Xpress into synthetic "Virtual Best/Mean/Worst Commercial Solver" baselines rather
> than naming per-solver results.** **⚠️ Benchmark your OWN models on YOUR instances.
> Published rankings are weakly predictive of your workload.**

- **⚠️ GPU-based first-order LP methods are real and maturing.** **PDLP/cuPDLP variants
  have been incorporated into solvers from Gurobi, COPT, FICO Xpress, HiGHS, Google and
  NVIDIA.** ⚠️ **The honest positioning: on Mittelmann's LP set, commercial simplex and
  barrier methods remain fastest overall and most reliable — one 2026 comparison has COPT
  solving 50 instances against 46 for GPU methods, and roughly 1.8× faster in shifted
  geometric mean.** **But on specific very large structured instances the advantage
  inverts dramatically** — ⚠️ **COPT reported a classic instance solved in under 15
  minutes by cuPDLP-C versus 16 hours by CPU interior point.**
  **⚠️ The read: GPU LP is not a general replacement, and it is a genuine unlock for
  certain large problems including supply chain ones. Test, don't assume.**

### 25.2 ⚠️ Quantum and AI optimization claims
**⚠️ Two hype axes where practitioners need calibration, and they need it in opposite
directions.**

> **⚠️ GOTCHA — quantum optimization for logistics is not commercially real in 2026, and
> the literature saying otherwise has documented methodological problems.**
> ⚠️ **A 2025 systematic review of peer-reviewed quantum-and-quantum-inspired transport
> optimization studies found that although several demonstrate gains over classical
> heuristics, "most rely on synthetic datasets, lack statistical robustness, and omit
> critical operational metrics."** **That is the sentence to remember.**

**⚠️ What the honest technical work actually says:**
- **⚠️ Hardware can't hold real problems.** **NISQ hardware is described as "almost
  universally incompatible with full-scale optimization problems of practical
  importance."** **Circuit-model quantum algorithms can't be tested much beyond ~30 binary
  variables even on simulators; ⚠️ quantum annealers become cumbersome around a few
  hundred variables due to embedding challenges.** **A realistic VRP has orders of
  magnitude more.**
- **⚠️ Everything credible is HYBRID and decomposed.** **The most-cited serious study
  (QC Ware with Aisin, in *Scientific Reports*) handled a real-scale multi-truck routing
  problem only by iteratively generating one truck's subproblem at a time, each around
  2,500 binary variables** — **explicitly to avoid a full embedding that isn't possible.**
- **⚠️ The comparisons are frequently against weak baselines.** **A result like "85% of
  optimal at 95% faster runtime than a genetic algorithm" is measured against a GA** —
  ⚠️ **and a well-tuned classical LNS (§8 → `logistics-constraint-programming-metaheuristics-and-bounds`) is a much stronger baseline that these papers
  typically don't run.**
- **⚠️ Treat the big vendor and analyst numbers with real scepticism.** **Claims of
  "40–60% logistics cost reductions" circulate in industry-analyst material.** ⚠️ **They
  do not come from operational deployments, and the same sources acknowledge persistent
  bottlenecks in data loading, algorithm tuning and hybrid integration with existing ERP
  and WMS.**

**⚠️ On LLMs and optimization — a more nuanced picture, and the useful direction is not
the obvious one:**
⚠️ **LLMs do not solve combinatorial problems; solvers do.** **Where the research is
genuinely promising is LLMs as an INTERFACE to optimization** — **the OptiGuide-style
pattern, where natural-language what-if questions are translated into model
modifications, the solver is re-run, and results are explained back.**
⚠️ **That targets §1 → `logistics-why-projects-fail-complexity-and-modeling`'s real failure modes — constraint elicitation, explainability and
trust — rather than the solve time, which was rarely the bottleneck.** **There is also
active work on ML-guided branching and solution prediction to accelerate MIP within
solvers, with reported primal-gap improvements over solver defaults on specific
benchmarks.** ⚠️ **Both are worth watching; neither replaces knowing §5 → `logistics-why-projects-fail-complexity-and-modeling`.**

---
