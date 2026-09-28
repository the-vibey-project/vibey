---
id: skill-1-foundations-83d68260c0
purpose: 1 foundations
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-foundations-and-algorithms/SKILL.md
requires: ["skill-0-routing-f2679346f1"]
links: ["skill-2-what-quantum-computers-can-and-cannot-do-9afa341e95"]
---

## §1. Foundations

### 1.1 The qubit

**[DURABLE]** A classical bit is 0 or 1. A qubit is a unit vector in a two-dimensional
complex Hilbert space:

```
|ψ⟩ = α|0⟩ + β|1⟩        where α, β ∈ ℂ  and  |α|² + |β|² = 1
```
`α` and `β` are **probability amplitudes**. On measurement in the computational basis you
get `0` with probability `|α|²` and `1` with probability `|β|²`, **and the state collapses**.

**n qubits require 2ⁿ complex amplitudes to describe.** 300 qubits is more amplitudes than
there are atoms in the observable universe. **This is the entire source of the hope** — and
also the source of the most persistent misconception (§1.4).

### 1.2 The four things that make it work

| Property | What it means | Why it matters |
|---|---|---|
| **Superposition** | A state can be a linear combination of basis states | You can act on many amplitudes at once |
| **Interference** | Amplitudes are complex and can cancel | **This is the actual mechanism.** Algorithms work by making wrong answers destructively interfere |
| **Entanglement** | Joint states not expressible as a product of individual states | Correlations with no classical analogue; the source of exponential state-space |
| **Measurement** | Probabilistic, and destroys superposition | **The bottleneck.** You get n bits out of a 2ⁿ-amplitude state |

**[DURABLE] Interference, not superposition, is the resource.** The naive story —
"it tries all answers in parallel" — is wrong (§1.4). A quantum algorithm works only if you
can arrange the amplitudes so that wrong answers cancel and right ones reinforce. **That
arrangement requires exploitable mathematical structure in the problem**, which is why
quantum speedups are rare and specific rather than general.

### 1.3 Gates and circuits

**Single-qubit gates** are 2×2 unitary matrices — rotations on the Bloch sphere:
- **X** (NOT), **Y**, **Z** — the Pauli gates.
- **H** (Hadamard) — creates superposition: `H|0⟩ = (|0⟩+|1⟩)/√2`. The workhorse.
- **S**, **T** — phase gates. **The T gate is the expensive one** (§5.4 → `quantum-noise-error-correction-and-hardware`, §9 → `quantum-software-and-resource-estimation`).
- **Rx(θ), Ry(θ), Rz(θ)** — arbitrary rotations.

**Two-qubit gates** create entanglement: **CNOT**, **CZ**, **iSWAP**, and the
hardware-native ones (**Mølmer–Sørensen** on ions). **[DURABLE] Two-qubit gates are
roughly an order of magnitude worse in fidelity than single-qubit gates on every
platform**, and they are what limits circuit depth.

**Universality**: `{H, T, CNOT}` is universal — any unitary can be approximated to
arbitrary precision. **Clifford gates alone (H, S, CNOT) are NOT universal and are
classically simulable in polynomial time (Gottesman–Knill).** This is why the T gate is
both essential and expensive: **it's precisely the non-classical part.**

**No-cloning theorem [DURABLE]**: an unknown quantum state cannot be copied. This forbids
naive error correction by redundancy (hence §5 → `quantum-noise-error-correction-and-hardware`), forbids "just measure and retry"
debugging, and underlies QKD's security argument (§12 → `quantum-applications-and-post-quantum-crypto`).

**Reversibility**: quantum gates are unitary and therefore reversible. Classical
irreversible operations must be embedded reversibly, which costs ancilla qubits — a real
factor in resource estimates.

### 1.4 The misconceptions, up front

> **⚠️ GOTCHA — "It tries all possibilities in parallel."** This is the single most
> damaging popular framing. You *can* put a register in superposition over all inputs, but
> **measurement gives you one random outcome.** Without interference engineering, that's
> just an expensive random number generator. Grover's quadratic (not exponential) speedup
> exists precisely because unstructured search offers no structure to interfere against —
> and **Grover's is provably optimal**, so no cleverness gets you further.

> **⚠️ GOTCHA — "Exponentially more storage."** 2ⁿ amplitudes exist in the mathematics, but
> **you cannot read them out.** n qubits yield n classical bits per measurement. Quantum
> computers are not memory devices, and **there is no efficient way to load a large
> classical dataset into a quantum state** — the QRAM problem, which quietly invalidates
> many proposed quantum machine-learning speedups (§11.3 → `quantum-applications-and-post-quantum-crypto`).

---
