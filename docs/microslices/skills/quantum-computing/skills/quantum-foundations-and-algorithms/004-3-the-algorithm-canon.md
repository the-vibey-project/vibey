---
id: skill-3-the-algorithm-canon-f38e6c9ddb
purpose: 3 the algorithm canon
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-foundations-and-algorithms/SKILL.md
requires: ["skill-2-what-quantum-computers-can-and-cannot-do-9afa341e95"]
links: []
---

## §3. The Algorithm Canon

| Algorithm | Does | Speedup | Reality check |
|---|---|---|---|
| **Deutsch–Jozsa** | Distinguishes constant vs. balanced functions | Exponential (oracle) | Pedagogical only — no use |
| **Bernstein–Vazirani**, **Simon's** | Hidden string / hidden period | Exponential (oracle) | Pedagogical; Simon's inspired Shor |
| **Shor's (1994)** | Factoring, discrete log | **Exponential** | ⚠️ **Breaks RSA, DH, ECC.** Needs millions of physical qubits (§9.2 → `quantum-software-and-resource-estimation`) |
| **Grover's (1996)** | Unstructured search | **Quadratic**, provably optimal | Halves effective symmetric key strength → AES-256 stays safe |
| **Quantum Phase Estimation** | Eigenvalues of a unitary | — | The subroutine underneath Shor and much of chemistry |
| **HHL (2009)** | Linear systems `Ax=b` | Exponential *with heavy caveats* | ⚠️ Sparse/well-conditioned A only; prepares `|x⟩`, doesn't give you x; needs QRAM. **Often dequantizable** |
| **Quantum simulation** (Trotter, qubitization, LCU) | Simulate quantum systems | **Exponential** | **The most defensible application** |
| **Amplitude estimation** | Monte Carlo | Quadratic | Finance interest; overheads are severe |
| **VQE** | Ground-state energies | **Heuristic — no proven speedup** | NISQ-era workhorse; ⚠️ barren plateaus (§4.4 → `quantum-noise-error-correction-and-hardware`) |
| **QAOA** | Combinatorial optimization | **Heuristic — no proven speedup** | Heavily studied; **classical algorithms often match or beat it** |
| **Quantum annealing** (D-Wave) | Ising/QUBO problems | **Disputed** | A different model entirely; not universal; §16.4 → `quantum-reference` |

**[DURABLE] Note the split.** The algorithms with *proven* exponential speedups all need
fault-tolerant hardware that doesn't exist yet. The algorithms that run on today's hardware
(VQE, QAOA) are **heuristics with no proven advantage**. That gap is the central honest
fact about the field's present moment, and most vendor messaging is designed to obscure it.
