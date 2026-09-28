---
id: skill-10-computational-nanoscience-8b2f901a6e
purpose: 10 computational nanoscience
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-computational-methods-and-safety/SKILL.md
requires: []
links: ["skill-11-safety-and-environmental-behaviour-6105b2e710"]
---

## §10. Computational Nanoscience

**⚠️ This is where a computational background applies directly, and the field is
fundamentally a multiscale simulation problem.**

### 10.1 The method ladder
```
Method              Length        Time         Accuracy      Cost
Quantum Monte Carlo  ~10 atoms    —            ⚠️ benchmark   brutal
CCSD(T)              ~50 atoms    —            "gold std"    ⚠️ O(N⁷)
DFT                  100s–1000s   ps           good-ish      ⚠️ O(N³)
Tight binding        10⁴–10⁵      ns           approximate   O(N)–O(N³)
MLIP (§10.3)         10⁵–10⁷      ⚠️ ns–µs      near-DFT      O(N)
Classical MD         10⁶–10⁹      µs–ms        force-field    O(N)
Coarse-grained       10⁶+         ms–s         topological    O(N)
Continuum/FEM        macroscale   —            constitutive   —
```
**⚠️ The central problem of the field is that the interesting phenomena sit in the gap
between what's accurate and what's affordable.**

### 10.2 DFT — what you need to know to use it honestly
**Hohenberg-Kohn**: ground-state energy is a functional of electron density `n(r)` — ⚠️ **3
variables instead of 3N.** **Kohn-Sham**: map to non-interacting electrons in an effective
potential, solved self-consistently.

**⚠️ The exchange-correlation functional is the approximation, and it is not systematically
improvable** — you cannot converge to the right answer by turning a dial.
```
LDA      overbinds; underestimates bandgaps badly
GGA (PBE) the workhorse; ⚠️ still underestimates bandgaps ~30–50%
meta-GGA (SCAN)  better geometries and energetics
Hybrid (HSE, B3LYP)  ⚠️ much better gaps, ~10-100× the cost
GW / BSE  ⚠️ proper excited states and optical spectra; expensive
DFT+U     for correlated d/f electrons
```
**⚠️ The failure modes to know**: **bandgaps are systematically underestimated** (a
well-known consequence of the derivative discontinuity, not a bug you can tune away);
**van der Waals is absent from standard functionals** — ⚠️ **you must add a dispersion
correction (Grimme D3/D4) or you will get layered materials and molecular crystals badly
wrong**; **strongly correlated systems** are genuinely hard; and **finite-temperature and
entropy effects are not included** unless you do extra work.

**Practical**: plane-wave codes (VASP, Quantum ESPRESSO, ABINIT) vs localized-basis
(Gaussian, FHI-aims, CP2K). ⚠️ **Convergence testing on cutoff energy and k-point mesh is
mandatory and routinely skipped** — an unconverged calculation produces confident numbers.

### 10.3 ⚠️ Machine-learned interatomic potentials — the genuine change

**[VERSIONED — §14.2 → `nano-reference`.]** **The premise**: train a model on DFT energies and forces, then
run MD at near-DFT accuracy for **orders of magnitude less cost.**

**Architecture lineage**: Behler-Parrinello descriptors → GAP (Gaussian process) →
**equivariant message-passing GNNs** — ⚠️ **equivariance under rotation/translation/
permutation is built into the architecture rather than learned, which is why these models
are so data-efficient.** **MACE, NequIP, Allegro, CHGNet, M3GNet, GRACE, MatterSim.**

**⚠️ The shift that matters: foundation models.** Instead of fitting a potential per system
— which took months of expert effort and thousands of DFT calculations — **general-purpose
models trained on large public datasets now run stable MD across a wide range of chemistry
out of the box.** MACE-MP-0 demonstrated this across **solids, liquids, gases, chemical
reactions, interfaces, and even small-protein dynamics.**

> **⚠️ GOTCHA — foundation MLIPs are not a free lunch, and the literature is explicit
> about it.** **They "do not yet achieve the accuracy required to predict reaction
> barriers, phase transitions, and material stability"** out of the box. **Fine-tuning is
> normally required** for a specific task, and it works well — ⚠️ **frozen transfer
> learning reaches chemical accuracy with orders of magnitude less data than training from
> scratch.**
>
> **Two more traps**: ⚠️ **some architectures predict forces directly rather than as the
> energy gradient, and those models do not conserve energy in MD** — which silently
> corrupts any thermodynamic result. And ⚠️ **benchmark leaderboard position does not
> guarantee physical soundness**; check energy conservation and phonon behaviour, not just
> the error metric.

**⚠️ The workflow discipline that follows**: **MLIPs pre-screen; DFT validates.** Treat
model output as a hypothesis generator over a large candidate space, then verify the
survivors with physics. **Anyone reporting a discovery on ML prediction alone has skipped
the step that matters.**

### 10.4 Molecular dynamics and multiscale
**Integrate Newton's equations** with a force field; **~1–2 fs timestep** set by the
fastest vibration (⚠️ **C–H stretch; constraining it via SHAKE/RATTLE buys you 2 fs**).
**Thermostats** (Nosé-Hoover, Langevin) and **barostats**; **periodic boundary conditions**;
**Ewald/PME** for long-range electrostatics.
**⚠️ The timescale problem is fundamental**: interesting events (nucleation, folding, rare
transitions) take microseconds to seconds; you can afford nanoseconds to microseconds.
**Enhanced sampling** — metadynamics, umbrella sampling, replica exchange — buys the gap by
biasing and then unbiasing.

**Kinetic Monte Carlo** for rare-event dynamics on a lattice (growth, diffusion).
**Phase field** and **FEM** for continuum. **⚠️ Coupling scales is the unsolved general
problem** — handshake regions, boundary condition mismatch, and spurious wave reflection at
interfaces.

**Software worth knowing**: LAMMPS, GROMACS, ASE (⚠️ **the Python glue for atomistic work —
learn this first**), pymatgen, Materials Project, AiiDA and FireWorks for workflow
management, OVITO/VMD for visualization.

---
