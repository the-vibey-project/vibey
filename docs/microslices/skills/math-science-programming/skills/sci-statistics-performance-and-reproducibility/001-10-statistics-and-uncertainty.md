---
id: skill-10-statistics-and-uncertainty-b70b7cd8ad
purpose: 10 statistics and uncertainty
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-statistics-performance-and-reproducibility/SKILL.md
requires: []
links: ["skill-11-performance-and-parallelism-36e18650e2"]
---

## §10. Statistics and Uncertainty

**[DURABLE] The section engineers most often skip and most often need.**

**Fitting**: ⚠️ **least squares assumes Gaussian errors** — if yours aren't, use the right
likelihood. **Weighted least squares** when uncertainties differ. **Robust regression**
(Huber, RANSAC) when outliers exist. ⚠️ **Report parameter uncertainties, not just point
estimates** — the covariance matrix from the fit is the minimum.

**Uncertainty quantification**: **propagation of uncertainty** (linear, via the Jacobian),
**Monte Carlo propagation** (⚠️ **more honest for nonlinear models**), **bootstrap** for
distribution-free confidence intervals, and **sensitivity analysis** (Sobol indices) to
find which input actually drives your output.

**Bayesian inference**: **MCMC** (⚠️ **NUTS/HMC in Stan, PyMC, NumPyro, Turing.jl — and
check R̂ and effective sample size, because an unconverged chain produces confident
nonsense**), **variational inference** for speed, **nested sampling** for evidence.

**Random numbers**: ⚠️ **Use a modern generator (PCG64, Philox) via a proper API — never
`rand()` from C's standard library for anything scientific.** **Seed explicitly and record
the seed** (§14). ⚠️ **For parallel work, use counter-based generators or explicitly split
streams — naively seeding per-thread from the clock produces correlated streams**, which is
a genuinely nasty and hard-to-detect bug.

---
