---
id: skill-4-choosing-a-tool-40792f3502
purpose: 4 choosing a tool
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-tooling-and-symbolic-computation/SKILL.md
requires: []
links: ["skill-5-symbolic-computation-53191c1342"]
---

## §4. Choosing a Tool

**[VERSIONED for the ecosystem details, DURABLE for the criteria.]**

| Tool | Genuine strengths | ⚠️ Genuine weaknesses |
|---|---|---|
| **MATLAB** | ⚠️ **Superb toolboxes** (Simulink, control, signal processing), excellent docs, industry-standard in control/aero/DSP, Simulink code generation to embedded targets is a real moat | **Cost and licence management**; proprietary; awkward at general programming; deployment is painful |
| **Python (NumPy/SciPy)** | ⚠️ **The default, and the widest ecosystem by far.** Free, general-purpose, and the glue between science and everything else | Loops are slow (§3 → `sci-floating-point-and-numerical-foundations`); packaging has historically been painful; **two-language problem for hot paths** |
| **Julia** | ⚠️ **Genuinely fast without leaving the language**; multiple dispatch is a superb fit for numerical code; excellent for ODEs/SciML | **Smaller ecosystem**; ⚠️ **compile latency ("time to first plot")** and weak AOT/binary story (§4.2) |
| **R** | ⚠️ **Statistics, unmatched.** CRAN, tidyverse, and the best statistical modelling libraries in existence | Awkward outside statistics; performance |
| **Fortran** | ⚠️ **Still the fastest thing for dense array numerics**, and it's what much of LAPACK and legacy HPC actually is. Modern Fortran (2008/2018) is far better than its reputation | Ecosystem, tooling, hiring |
| **C/C++** | Control, performance, Eigen/Armadillo/Blaze, and where libraries get written | Development speed; you own every mistake |
| **Mathematica / Maple** | ⚠️ **Symbolic computation, unmatched** (§5). Excellent for derivation | Cost; proprietary; less good as general numerics |
| **Octave / Scilab** | Free, largely MATLAB-compatible | Slower; toolbox gaps |
| **Rust** | Memory safety, growing numerical ecosystem | Ecosystem immaturity for science |

### 4.1 [DURABLE] The criteria that actually decide it
1. **⚠️ What does your field use?** Being the only Julia user in a MATLAB lab is a real
   cost — code review, collaboration, and inheriting others' work all get harder.
   **This is usually decisive and rarely stated.**
2. **Does the library you need exist?** ⚠️ **A specialist toolbox can outweigh every
   language-level consideration.** MATLAB's Simulink-to-hardware path, R's statistical
   models, and Julia's DifferentialEquations.jl are each near-unique.
3. **Who maintains it in five years?**
4. **Deployment**: does this ship, or run once for a paper?
5. **Licensing**, especially for reproducibility (⚠️ **a proprietary dependency is a
   reproducibility liability** — §14 → `sci-statistics-performance-and-reproducibility`).

### 4.2 ⚠️ The two-language problem, honestly

**[CONTESTED]** Julia was explicitly designed to solve it: **you prototype in a high-level
language, then rewrite the hot path in C or Fortran, and now you maintain two
implementations that can diverge.**

**Julia's case in 2026**: mature by any reasonable measure — **100M+ downloads, 12,000+
registered packages**, and **JuliaHub raised a $65M Series B in April 2026**, which is
meaningful enterprise signal. ⚠️ **But it sits around #32 on TIOBE at ~0.5%**, and the
honest reading of that is contested: TIOBE measures search-result popularity and
**systematically undercounts specialized domains**, but the number is still not large.

**⚠️ The critique deserves airing too.** A 2024 assessment of Julia for scientific machine
learning argued that while the ecosystem provides genuinely useful abstractions,
**"the limitations are severe enough to prevent it from widespread adoption,"** and called
on the community to address language-level issues. **The recurring practical complaints**:
compile latency, and **weak first-class support for ahead-of-time compilation of small
binaries and libraries** — which some practitioners characterize as Julia having traded
the two-language problem for a **"1.5 language problem."**

**⚠️ And note the counter-move**: Python has substantially eroded the premise. **Numba,
Cython, JAX, PyTorch, and now the Array API standard (§17 → `sci-reference`)** mean much high-level Python
numerical code reaches compiled speed without a rewrite. **MathWorks responded too** —
MATLAB can call Python directly and has adopted Python-like broadcasting semantics.

**[DURABLE] The defensible position: pick for ecosystem and colleagues first, performance
second — because the performance gap is now closable in every one of these languages, and
the ecosystem gap is not.**

---
