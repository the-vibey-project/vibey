---
id: skill-15-myths-and-anti-patterns-4afb01dfd9
purpose: 15 myths and anti patterns
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-reference/SKILL.md
requires: ["skill-14-learning-it-b9d7607d1d"]
links: ["skill-16-contested-questions-ce782b808c"]
---

## §15. Myths and Anti-Patterns

| Claim / behaviour | Reality |
|---|---|
| "Tries all possibilities in parallel" | Measurement returns one outcome. **Interference is the mechanism** (§1.2 → `quantum-foundations-and-algorithms`, §1.4 → `quantum-foundations-and-algorithms`) |
| "Solves NP-complete problems efficiently" | **BQP is not believed to contain NP** (§2.1 → `quantum-foundations-and-algorithms`). Grover is quadratic and provably optimal |
| "Exponentially more storage" | 2ⁿ amplitudes exist; **you get n bits out**. No efficient classical-data loading (§1.4 → `quantum-foundations-and-algorithms`, §11.3 → `quantum-applications-and-post-quantum-crypto`) |
| "N qubits" without saying which kind | **Physical ≠ logical.** ~49 physical per logical at distance 7 (§0 → `quantum-foundations-and-algorithms`, §5.3 → `quantum-noise-error-correction-and-hardware`) |
| "Will replace classical computers" | Co-processors for specific subroutines. Everything else stays classical |
| "Quantum computers are just faster" | Different computational model with narrow advantages |
| Comparing a quantum result to a naive classical baseline | Compare against the **best** classical method, on a GPU cluster, with tensor networks (§10.3 → `quantum-software-and-resource-estimation`) |
| Treating a supremacy claim as permanent | **Multiple claims have been dequantized** (§10.3 → `quantum-software-and-resource-estimation`). Wait 6–18 months |
| Quoting Willow as "fault tolerance achieved" | It demonstrated **below-threshold scaling**, not fault tolerance at useful scale (§5.3 → `quantum-noise-error-correction-and-hardware`) |
| Quoting one RSA-breaking qubit number as settled | Estimates vary with assumptions and have fallen repeatedly (§9.2 → `quantum-software-and-resource-estimation`) |
| Assuming quadratic speedups translate to real advantage | **Error-correction overhead and slow logical clocks often eat them** (§9.3 → `quantum-software-and-resource-estimation`) |
| Building a business case on QAOA/VQE advantage | Heuristics with **no proven speedup**; classical often wins (§3 → `quantum-foundations-and-algorithms`, §11.2 → `quantum-applications-and-post-quantum-crypto`) |
| Investing in QML without addressing data loading | The bottleneck that invalidates most proposals (§11.3 → `quantum-applications-and-post-quantum-crypto`) |
| Believing vendor-defined single-number metrics | Ask what it measures and who defined it (§4.3 → `quantum-noise-error-correction-and-hardware`) |
| Ignoring the transpiled circuit | SWAP insertion can multiply gate count several-fold (§8.2 → `quantum-software-and-resource-estimation`) |
| Confusing error mitigation with error correction | Mitigation costs exponential shots and doesn't scale (§4.2 → `quantum-noise-error-correction-and-hardware`) |
| Deploying QKD instead of PQC | **NSA, NCSC, and ANSSI all recommend PQC over QKD** (§12 → `quantum-applications-and-post-quantum-crypto`) |
| Using competition-version PQC parameters | Use the **FIPS** versions; parameters changed (§13.2 → `quantum-applications-and-post-quantum-crypto`) |
| Deferring PQC because "quantum computers don't exist yet" | **HNDL** + **binding regulatory deadlines** (§13.1 → `quantum-applications-and-post-quantum-crypto`, §13.3 → `quantum-applications-and-post-quantum-crypto`) |
| Starting PQC migration with algorithm selection | **Start with the inventory.** That's where programs stall (§13.4 → `quantum-applications-and-post-quantum-crypto`) |
| Learning from analogies instead of linear algebra | You'll have to unlearn them (§14) |

---
