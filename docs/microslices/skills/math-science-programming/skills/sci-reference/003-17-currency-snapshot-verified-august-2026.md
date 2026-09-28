---
id: skill-17-currency-snapshot-verified-august-2026-b101cffa6a
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-reference/SKILL.md
requires: ["skill-16-contested-questions-b4fc0fecdf"]
links: ["skill-18-the-canon-e6ede1a78c"]
---

## §17. Currency Snapshot — verified August 2026

**[DURABLE] §1 → `sci-floating-point-and-numerical-foundations`, §2 → `sci-floating-point-and-numerical-foundations`, §3 → `sci-floating-point-and-numerical-foundations`, §6–§13 → `sci-linear-algebra-differential-equations-and-optimization`, `sci-statistics-performance-and-reproducibility` are numerical analysis and do not move. IEEE 754 is from
1985.** What follows is the tooling layer.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **⚠️ Python Array API standard** | **The genuine structural change in the Python numerical stack.** A common specification across NumPy, CuPy, PyTorch, JAX, Dask. **NumPy 2.0 adopted it (NEP 47/56)** in the main namespace, `numpy.linalg` and `numpy.fft`. **Four years on from the first release (2021.12)**, adoption is broad. ⚠️ **The payoff: downstream libraries write array-agnostic code once and users get GPU execution with a minimal code change** — reported benchmarks include **up to ~52× speedups across scikit-learn and SciPy**, and a Ridge+MaxAbsScaler benchmark at **~50× (PyTorch) and ~49× (CuPy) vs NumPy** | Medium |
| **SciPy / scikit-learn** | Both adopting the standard progressively; scikit-learn uses `array_api_compat`. ⚠️ **Note a subtlety: the standard routes to `numpy.linalg` rather than `scipy.linalg`, which differ subtly** — scikit-learn dispatches conservatively for backward compatibility | Medium |
| **CuPy** | **v14 (Feb 2026)** — NumPy v2 semantics, bfloat16, CUDA pip wheels, broader NumPy/SciPy API coverage. **60M downloads, 10k GitHub stars** | Medium |
| **⚠️ Julia** | **100M+ downloads, 12,000+ registered packages.** **JuliaHub raised a $65M Series B in April 2026.** **TIOBE ~#32 at ~0.50% (April 2026)** — ⚠️ **but TIOBE measures search popularity and systematically undercounts specialized domains.** Persistent criticisms: **compile latency; weak first-class AOT compilation of small binaries** (PackageCompiler.jl/StaticCompiler.jl not considered first-class); a 2024 assessment argued limitations are **"severe enough to prevent widespread adoption"** for scientific ML | Medium |
| **MATLAB** | Retains the academic and industrial stronghold in control, DSP and Simulink workflows. ⚠️ **MathWorks has responded to Python's rise** — direct Python calling from MATLAB, and adoption of more aggressive broadcasting semantics | Low |
| **⚠️ Reproducibility** | **>70% of researchers report failing to reproduce another group's findings.** Life-sciences replication estimates: **10–25% reproducing robustly.** **Nature's 2026 reproducibility special issue: a multi-team effort found ~half of behavioural-science claims replicated.** Institutional response: artifact evaluation committees and reproducibility badges at major venues — ⚠️ **though research questions whether badges reliably reflect reproducibility quality** | Low |
| **Numerical reproducibility** | **Intel MKL offers conditional numerical reproducibility** by curtailing instruction-set extensions — ⚠️ **at a performance cost, and requiring consistent thread counts.** Underlying causes remain **out-of-order FP arithmetic in parallel reductions and non-associativity** | Low |
| **Regulatory** | ⚠️ **EU AI Act high-risk obligations phasing in through August 2026** touch scientific software in high-risk domains (medical devices, decision support): technical documentation, data governance, human oversight, traceability, post-market monitoring | Medium |

**Goes stale fastest:** the Array API adoption state and Julia's trajectory.
**Essentially never stale:** §1 → `sci-floating-point-and-numerical-foundations`, §2 → `sci-floating-point-and-numerical-foundations`, §6 → `sci-linear-algebra-differential-equations-and-optimization`, §7.1 → `sci-linear-algebra-differential-equations-and-optimization`'s stiffness framing, §13 → `sci-statistics-performance-and-reproducibility`, §15.

---
