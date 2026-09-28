---
id: skill-9-interpolation-quadrature-transforms-d4e73a5ed1
purpose: 9 interpolation quadrature transforms
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-linear-algebra-differential-equations-and-optimization/SKILL.md
requires: ["skill-8-optimization-f687e43c41"]
links: []
---

## §9. Interpolation, Quadrature, Transforms

**Interpolation**: ⚠️ **Do not fit high-degree polynomials to equispaced points** —
**Runge's phenomenon** makes the error explode at the endpoints. **Use splines (cubic, or
monotone PCHIP if overshoot matters), or Chebyshev nodes** if you control the sampling.
**Interpolation ≠ regression**: interpolation passes through every point (⚠️ **including
the noise**); fit a smoother if the data is noisy.

**Quadrature**: **Gauss–Legendre** (exceptional for smooth integrands), **adaptive
Clenshaw–Curtis**, **QUADPACK** under `scipy.integrate.quad`. ⚠️ **For dimensions above
~4, deterministic quadrature dies to the curse of dimensionality — use Monte Carlo or
quasi-Monte Carlo (Sobol), whose error is dimension-independent.** Handle **singularities
and infinite domains with a variable transformation**, not brute force.

**Transforms**: **FFT** — ⚠️ **O(n log n), and the workhorse of signal processing and
spectral methods.** **FFTW** is the reference implementation. Know the pitfalls:
**aliasing** (sample above Nyquist), **spectral leakage** (window your data), **and the
normalization convention differs between libraries** — ⚠️ **check whether the 1/N is on the
forward or inverse transform before comparing results across tools.**
