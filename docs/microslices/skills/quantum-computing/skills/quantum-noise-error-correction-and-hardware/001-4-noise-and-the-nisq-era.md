---
id: skill-4-noise-and-the-nisq-era-69c489f1e4
purpose: 4 noise and the nisq era
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-noise-error-correction-and-hardware/SKILL.md
requires: []
links: ["skill-5-error-correction-and-fault-tolerance-bbd626470d"]
---

## §4. Noise and the NISQ Era

### 4.1 What goes wrong

**[DURABLE]** Quantum states are fragile in ways classical bits are not:
- **Decoherence** — coupling to the environment destroys the state. **T1** (energy
  relaxation / amplitude damping) and **T2** (dephasing) are the two lifetimes, and
  **T2 ≤ 2·T1** always.
- **Gate errors** — imperfect control. Single-qubit errors ~10⁻⁴–10⁻³, two-qubit errors
  ~10⁻³–10⁻² on current hardware, depending heavily on platform.
- **Measurement/readout errors** — often the largest single error source, ~1%.
- **Crosstalk** — operating one qubit disturbs its neighbours.
- **Leakage** — the qubit escapes the computational subspace into a third level.
- **Correlated and non-Markovian noise** — the assumption-breaker for many error models,
  and a live research area.

**The core tension**: circuit depth × error rate must stay small. At 10⁻³ two-qubit error,
you get roughly 1000 gates before errors dominate. **Useful algorithms need millions to
billions.** That gap is the entire justification for §5.

### 4.2 Error mitigation (not correction)

**[DURABLE] Mitigation reduces bias in expectation values; it does not fix the
computation.** The distinction matters: correction (§5) makes arbitrarily long computations
possible, mitigation buys you a factor at exponentially growing sampling cost.

- **Zero-noise extrapolation (ZNE)** — run at amplified noise levels, extrapolate to zero.
- **Probabilistic error cancellation (PEC)** — invert the noise channel by sampling;
  **provably correct, exponentially costly in sampling overhead**.
- **Readout error mitigation** — cheap, effective, do it always.
- **Dynamical decoupling** — pulse sequences that echo away slow dephasing during idle time.
- **Symmetry verification / post-selection** — throw away runs that violate a known
  conserved quantity.
- **Twirling / randomized compiling** — turn coherent errors into stochastic ones, which
  are much better behaved.

**⚠️ Every mitigation technique costs exponentially more shots as circuits grow.** They
extend the NISQ regime; they do not scale to useful algorithms.

### 4.3 Benchmarking

Beyond raw qubit count: **randomized benchmarking** and **cycle benchmarking** for gate
fidelity, **quantum volume** (IBM's single-number metric, now widely seen as saturating),
**CLOPS** (speed), **algorithmic qubits** (IonQ's metric — ⚠️ vendor-defined), and
**application-level benchmarks**. **[DURABLE] Be suspicious of any single-number metric,
especially one the vendor invented.**

### 4.4 Barren plateaus

**[DURABLE, and it's the most important negative result of the NISQ era.]** For many
parameterized quantum circuits, gradients vanish **exponentially in the number of qubits**,
making variational training (VQE, QAOA, QML) infeasible at scale. Causes include circuit
expressiveness, entanglement, noise, and global cost functions. Mitigations (local cost
functions, shallow structured ansätze, smart initialization) exist — but **there is a
significant result showing that provable absence of barren plateaus may imply classical
simulability**, i.e. the circuits you can train may be exactly the ones you didn't need a
quantum computer for. That tension is unresolved and it is central to §16.3 → `quantum-reference`.

---
