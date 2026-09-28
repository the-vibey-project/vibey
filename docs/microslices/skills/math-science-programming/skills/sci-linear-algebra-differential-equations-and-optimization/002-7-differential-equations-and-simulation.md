---
id: skill-7-differential-equations-and-simulation-8466f9074a
purpose: 7 differential equations and simulation
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-linear-algebra-differential-equations-and-optimization/SKILL.md
requires: ["skill-6-linear-algebra-a33ab9478a"]
links: ["skill-8-optimization-f687e43c41"]
---

## §7. Differential Equations and Simulation

### 7.1 ODEs

**[DURABLE] The single most important question: is your system stiff?**

**⚠️ Stiffness means widely-separated time scales** — a fast transient alongside slow
dynamics. **The tell: an explicit solver takes absurdly tiny steps and crawls**, not
because accuracy demands it but because stability does. **Chemical kinetics, circuit
simulation, and reaction-diffusion are routinely stiff.**

| | **Non-stiff** | **Stiff** |
|---|---|---|
| Methods | Explicit RK (Dormand–Prince RK45), Adams–Bashforth | ⚠️ **Implicit: BDF, Radau, Rosenbrock** |
| Cost per step | Cheap | Expensive — solves a nonlinear system, needs a Jacobian |
| **Use when** | Smooth, comparable time scales | ⚠️ **Explicit is crawling** |

**⚠️ Structure-preserving integrators matter more than accuracy order for long runs**:
**symplectic integrators for Hamiltonian systems** (⚠️ **they conserve energy over
astronomically long integrations where a "more accurate" RK method drifts**), and
**geometric integrators generally.** **If you're doing orbital mechanics or molecular
dynamics and using RK45, that's likely the bug.**

**Also**: **adaptive stepping with error control** (⚠️ **set `rtol` and `atol` deliberately
— the defaults are rarely right for your scaling**), **event detection** for
discontinuities, **DAEs** (index matters), and **sensitivity analysis / adjoints** for
gradients through a solve.

**Libraries**: **SUNDIALS** (CVODE/IDA/ARKODE — ⚠️ **the reference implementation, wrapped
by nearly everything**), **`scipy.integrate.solve_ivp`**, **DifferentialEquations.jl**
(⚠️ **the most comprehensive ODE ecosystem anywhere, and a genuine reason to consider
Julia**), MATLAB's `ode45`/`ode15s`.

### 7.2 PDEs

**The discretization families**: **finite difference** (simple, structured grids),
**finite volume** (⚠️ **conservative by construction — the right choice for fluids and
anything with conservation laws**), **finite element** (complex geometry, rigorous error
theory), **spectral** (⚠️ **exponential convergence for smooth problems on simple
domains**), and **meshless/particle** methods.

**⚠️ The CFL condition** governs explicit time-stepping stability: your time step is
bounded by the mesh spacing over the wave speed. **Refining the mesh forces smaller time
steps**, which is why explicit schemes get expensive quadratically.

**Frameworks**: **FEniCS/Firedrake** (⚠️ **write the weak form, get a solver — genuinely
remarkable**), **deal.II**, **MFEM**, **OpenFOAM** (CFD), **SU2**, **Gmsh** for meshing,
**ParaView/VisIt** for visualization.

**⚠️ And the practical truth: meshing is usually the hard part, not solving.** Budget
accordingly.

### 7.3 Scientific machine learning
**[VERSIONED]** **PINNs**, **neural ODEs**, **operator learning (DeepONet, Fourier Neural
Operator)**, and hybrid physics-ML models. ⚠️ **Promising and genuinely oversold: for
classical forward problems on well-posed domains, a good conventional solver is usually
faster and far more reliable.** The stronger cases are inverse problems, surrogate models
for repeated queries, and problems where the governing equations are partly unknown.

---
