---
id: skill-15-anti-patterns-053ce7d4bd
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-b4fc0fecdf"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Comparing floats with `==` | Decimal fractions aren't representable (§1.1 → `sci-floating-point-and-numerical-foundations`) |
| Hand-rolled naive summation over a big array | ⚠️ **Error grows with n; use pairwise/Kahan** (§1.1 → `sci-floating-point-and-numerical-foundations`) |
| Treating a parallel result difference as a bug | ⚠️ **FP addition isn't associative** (§1.1 → `sci-floating-point-and-numerical-foundations`, §11 → `sci-statistics-performance-and-reproducibility`) |
| `sqrt(x*x + y*y)` instead of `hypot` | Intermediate overflow (§1.2 → `sci-floating-point-and-numerical-foundations`) |
| The naive quadratic formula | Catastrophic cancellation on one root (§1.1 → `sci-floating-point-and-numerical-foundations`) |
| `-ffast-math` on code you haven't analyzed | ⚠️ **Permits reassociation, assumes no NaN/inf** (§1.1 → `sci-floating-point-and-numerical-foundations`) |
| Never checking the condition number | ⚠️ **κ=10¹⁶ means zero significant digits, silently** (§2 → `sci-floating-point-and-numerical-foundations`) |
| Refining the mesh/step indefinitely | ⚠️ **Total error has a minimum; past it you get worse** (§2 → `sci-floating-point-and-numerical-foundations`) |
| High-degree polynomial fit on raw equispaced data | Vandermonde conditioning + Runge (§2 → `sci-floating-point-and-numerical-foundations`, §9 → `sci-linear-algebra-differential-equations-and-optimization`) |
| **`inv(A) @ b`** | ⚠️ **Slower, less accurate, less stable than `solve`** (§6 → `sci-linear-algebra-differential-equations-and-optimization`) |
| `det(A)` as a singularity test | Overflows; tells you less than κ (§6 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Normal equations for least squares | ⚠️ **Squares the condition number. Use QR** (§6 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Not using Cholesky on an SPD matrix | 2× the speed, free (§6 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Unpreconditioned Krylov on an ill-conditioned system | Won't converge, and that's the default (§6 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Python/MATLAB loop over array elements | ⚠️ **Two to three orders of magnitude** (§3 → `sci-floating-point-and-numerical-foundations`) |
| Vectorizing into an n×n intermediate for an O(n) result | Memory explosion (§3 → `sci-floating-point-and-numerical-foundations`) |
| Explicit ODE solver on a stiff system | ⚠️ **It will crawl. That's the diagnosis** (§7.1 → `sci-linear-algebra-differential-equations-and-optimization`) |
| RK45 for long Hamiltonian integrations | ⚠️ **Energy drift. Use a symplectic integrator** (§7.1 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Default `rtol`/`atol` without thinking | Rarely right for your scaling (§7.1 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Unscaled optimization variables | ⚠️ **The most common non-convergence cause** (§8 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Finite-difference gradients when AD exists | Slower, less accurate, ill-conditioned (§5 → `sci-tooling-and-symbolic-computation`, §8 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Reading only `x` and ignoring the solver exit flag | ⚠️ **"Max iterations" is not convergence** (§8 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Assuming a local optimum is global | Only convex problems promise that (§8 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Unregularized inverse problem | Fits noise beautifully (§8.4 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Deterministic quadrature above ~4 dimensions | Curse of dimensionality; use QMC (§9 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Comparing FFT results across libraries without checking normalization | The 1/N convention differs (§9 → `sci-linear-algebra-differential-equations-and-optimization`) |
| Point estimates with no uncertainty | Half an answer (§10 → `sci-statistics-performance-and-reproducibility`) |
| Per-thread seeding from the clock | ⚠️ **Correlated streams; use counter-based RNG** (§10 → `sci-statistics-performance-and-reproducibility`) |
| MCMC without checking R̂ and ESS | Confident nonsense (§10 → `sci-statistics-performance-and-reproducibility`) |
| Optimizing before profiling | You will guess wrong (§11 → `sci-statistics-performance-and-reproducibility`) |
| Micro-optimizing arithmetic in bandwidth-bound code | Roofline says it can't help (§11 → `sci-statistics-performance-and-reproducibility`) |
| Large numerical data in CSV | Slow, untyped, ⚠️ **lossy on floats** (§12 → `sci-statistics-performance-and-reproducibility`) |
| Writing floats to text at 6 digits | Silent data loss (§12 → `sci-statistics-performance-and-reproducibility`) |
| No units discipline | ⚠️ **Mars Climate Orbiter** (§12 → `sci-statistics-performance-and-reproducibility`) |
| "The plot looks reasonable" as verification | ⚠️ **Code produces numbers whether or not it's right** (§13 → `sci-statistics-performance-and-reproducibility`) |
| No convergence-order test | ⚠️ **The cheapest bug-finder you're not using** (§13 → `sci-statistics-performance-and-reproducibility`) |
| Never heard of manufactured solutions | The most powerful verification tool available (§13 → `sci-statistics-performance-and-reproducibility`) |
| Conflating verification and validation | Different questions; both needed (§13 → `sci-statistics-performance-and-reproducibility`) |
| `requirements.txt` with no pinned versions | ⚠️ **Not an environment** (§14 → `sci-statistics-performance-and-reproducibility`) |
| Seeds not recorded in the output | Untraceable results (§14 → `sci-statistics-performance-and-reproducibility`) |
| Claiming bitwise reproducibility across hardware | ⚠️ **Often impossible; state a tolerance** (§14 → `sci-statistics-performance-and-reproducibility`) |
| "Code available on request" | Empirically equivalent to unavailable (§14 → `sci-statistics-performance-and-reproducibility`) |
| Writing the algorithm instead of calling LAPACK | ⚠️ **Person-centuries of expertise you won't replicate** (§3 → `sci-floating-point-and-numerical-foundations`) |

---
