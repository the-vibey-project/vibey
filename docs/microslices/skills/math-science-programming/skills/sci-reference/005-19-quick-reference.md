---
id: skill-19-quick-reference-3613ba3c78
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-reference/SKILL.md
requires: ["skill-18-the-canon-e6ede1a78c"]
links: ["skill-20-sources-and-method-8f64c281a2"]
---

## §19. Quick Reference

### 19.1 Numbers to hold
- **float64 eps ≈ 2.22e-16**; ~15–17 significant digits
- **float32 eps ≈ 1.19e-7**; ~6–9 digits
- **error ≈ κ(A) × eps** — ⚠️ **κ=10⁸ costs you half your digits**
- **Optimal finite-difference step ≈ √eps ≈ 1.5e-8** (for a well-scaled problem)
- **Cholesky ≈ ⅓n³; LU ≈ ⅔n³; QR ≈ 2mn²**
- **BLAS-3 is the only level that reaches peak FLOPS**
- ⚠️ **Above ~4 dimensions, quadrature loses to Monte Carlo**

### 19.2 When the numbers are wrong
1. **Check for NaN/inf** and where they first appear (⚠️ `np.seterr`, or a debugger trap)
2. **Check the condition number** (§2 → `sci-floating-point-and-numerical-foundations`)
3. **Check scaling** — are quantities O(1)? (§1.2 → `sci-floating-point-and-numerical-foundations`, §8 → `sci-linear-algebra-differential-equations-and-optimization`)
4. **Check the solver's exit status**, not just its output (§8 → `sci-linear-algebra-differential-equations-and-optimization`)
5. **Check units** (§12 → `sci-statistics-performance-and-reproducibility`)
6. **Run a convergence study** — does the error behave as theory says? (§13 → `sci-statistics-performance-and-reproducibility`)
7. **Check conservation** — is energy/mass conserved? (§13 → `sci-statistics-performance-and-reproducibility`)
8. **Compare against an analytical case or a manufactured solution** (§13 → `sci-statistics-performance-and-reproducibility`)
9. **Check tolerances** — are `rtol`/`atol` appropriate for your scale? (§7.1 → `sci-linear-algebra-differential-equations-and-optimization`)

### 19.3 Method picker
| Problem | Use |
|---|---|
| Solve Ax=b, general | LU (`solve`) — ⚠️ **never `inv`** |
| Solve Ax=b, symmetric positive definite | **Cholesky** |
| Least squares | **QR** — not normal equations |
| Rank / structure / ill-conditioned | **SVD** |
| Large sparse SPD | **CG + preconditioner** |
| Large sparse general | **GMRES/BiCGSTAB + preconditioner** |
| ODE, non-stiff | RK45 (`solve_ivp`, `ode45`) |
| ODE, stiff | **BDF / Radau** (`ode15s`, CVODE) |
| Hamiltonian, long integration | **Symplectic integrator** |
| PDE, conservation laws | **Finite volume** |
| PDE, complex geometry | **Finite element** (FEniCS/deal.II) |
| Smooth 1-D integral | Gauss–Legendre / `quad` |
| High-dimensional integral | **Monte Carlo / Sobol QMC** |
| Gradients of a program | ⚠️ **Automatic differentiation** (§5 → `sci-tooling-and-symbolic-computation`) |
| Convex optimization | **CVXPY / JuMP** + a conic solver |
| Constrained nonlinear | **IPOPT / SQP** |
| Parameter uncertainty | Bootstrap, or MCMC (§10 → `sci-statistics-performance-and-reproducibility`) |
| Deriving equations | ⚠️ **Symbolic, then generate code** (§5 → `sci-tooling-and-symbolic-computation`) |

---
