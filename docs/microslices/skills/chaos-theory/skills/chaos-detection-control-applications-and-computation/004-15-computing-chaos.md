---
id: skill-15-computing-chaos-94a83dcd26
purpose: 15 computing chaos
source: src/vibey_tools/skills/plugins/chaos-theory/skills/chaos-detection-control-applications-and-computation/SKILL.md
requires: ["skill-14-where-it-actually-appears-44778fc561"]
links: []
---

## §15. Computing Chaos

> **⚠️ GOTCHA — every computed chaotic trajectory is wrong, and the honest question is why
> the results mean anything.**
> ⚠️ **Floating-point error is amplified exponentially, exactly like any other
> perturbation.** **After a few dozen Lyapunov times your numerical trajectory has no
> relationship to the true trajectory from your stated initial condition.**
>
> **⚠️ The answer is the shadowing lemma**: for hyperbolic systems, **a numerically
> computed pseudo-trajectory is closely shadowed by a TRUE trajectory of the system from a
> slightly different initial condition.** ⚠️ **So your computed orbit is a real orbit of
> the real system — just not the one you asked for.** **Which is fine, because what you
> want is the statistics of the attractor, and those are robust.**
>
> ⚠️ **The caveat that matters: shadowing is proven for uniformly hyperbolic systems, and
> most systems of interest are not uniformly hyperbolic.** **In practice it's assumed to
> hold approximately. Be aware you are relying on it.**

**Practical rules**: ⚠️ **compare individual trajectories only over short times; compare
statistics over long ones.** **Use a good integrator and verify with a smaller timestep**
(⚠️ **and see a Newtonian-mechanics reference §14 — for Hamiltonian chaos, use a
symplectic integrator, because energy drift will corrupt exactly the phase-space structure
you're studying**). **Discard transients before measuring anything.** **Compute Lyapunov
exponents with repeated Gram-Schmidt renormalization to avoid overflow.**
**⚠️ Ensembles, not single runs** — this is precisely why weather forecasting uses
ensembles.
