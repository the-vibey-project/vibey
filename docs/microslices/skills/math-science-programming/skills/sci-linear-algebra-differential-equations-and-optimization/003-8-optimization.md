---
id: skill-8-optimization-f687e43c41
purpose: 8 optimization
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-linear-algebra-differential-equations-and-optimization/SKILL.md
requires: ["skill-7-differential-equations-and-simulation-8466f9074a"]
links: ["skill-9-interpolation-quadrature-transforms-d4e73a5ed1"]
---

## §8. Optimization

**[DURABLE] Classify the problem before choosing a method — this is most of the work.**

```
Is it convex?          → YES: a global optimum exists and is findable. Say so, and exploit it
                         NO: you get a local optimum. Multi-start, or accept it
Do you have gradients? → AD (§5) is almost always available and almost always worth it
Constraints?           → Linear (LP/QP), nonlinear (SQP, interior point), or none
Smooth?                → Non-smooth needs subgradient/proximal methods
Expensive to evaluate? → Bayesian optimization / surrogate methods
Discrete?              → MILP, or see a theory-of-computation reference on NP-hardness
```

| Class | Methods | Tools |
|---|---|---|
| **LP / QP / conic** | Simplex, interior point | ⚠️ **Gurobi, CPLEX, Mosek (commercial, much faster); HiGHS, OSQP, SCS, Clarabel (open)** |
| **Smooth unconstrained** | BFGS, L-BFGS, Newton, trust region | scipy.optimize, NLopt, Optim.jl |
| **Constrained nonlinear** | SQP, interior point | **IPOPT**, SNOPT, `scipy` SLSQP |
| **Least squares** | Levenberg–Marquardt, Gauss–Newton | Ceres, `least_squares` |
| **Global / derivative-free** | Nelder–Mead, CMA-ES, DIRECT, differential evolution | NLopt, pymoo |
| **Modelling layers** | — | **CVXPY**, JuMP.jl, Pyomo, AMPL |

> **⚠️ GOTCHA — the optimization failure modes that waste the most time:**
> - **Not scaling variables.** ⚠️ **If one variable is ~10⁻⁶ and another ~10⁶, the solver
>   sees a pathological problem. Non-dimensionalize.** This is the most common cause of
>   "the optimizer won't converge."
> - **Finite-difference gradients when AD was available.** Slower, less accurate, and it
>   inherits §2 → `sci-floating-point-and-numerical-foundations`'s differentiation ill-conditioning.
> - **⚠️ Believing a local optimum is global** in a non-convex problem.
> - **Ignoring the exit flag.** ⚠️ **Solvers return status codes and people read only `x`.**
>   "Max iterations reached" is not convergence.
> - **Reformulating a convex problem into a non-convex one** by accident — CVXPY's
>   disciplined convex programming rules exist to prevent exactly this.

**⚠️ §8.4 Inverse and ill-posed problems** deserve their own note: fitting parameters to
data is often **ill-posed**, and the fix is **regularization** — Tikhonov/ridge, L1/lasso,
total variation — with the regularization parameter chosen by **L-curve or cross-
validation**, not by eye. **An unregularized inverse problem fits noise beautifully.**

---
