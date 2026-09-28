---
id: skill-2-what-quantum-computers-can-and-cannot-do-9afa341e95
purpose: 2 what quantum computers can and cannot do
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-foundations-and-algorithms/SKILL.md
requires: ["skill-1-foundations-83d68260c0"]
links: ["skill-3-the-algorithm-canon-f38e6c9ddb"]
---

## §2. What Quantum Computers Can and Cannot Do

### 2.1 The complexity picture

**[DURABLE]** **BQP** (bounded-error quantum polynomial time) is the class of problems a
quantum computer solves efficiently. Known relationships:
- **P ⊆ BQP ⊆ PSPACE.** Quantum computers can do everything classical ones can.
- **BQP is not known to contain NP.** ⚠️ **Quantum computers are not believed to solve
  NP-complete problems efficiently.** This is the most consequential fact in the field and
  the most frequently misreported.
- **Factoring is in BQP** and is *not* believed NP-complete — it's in NP ∩ co-NP, suspected
  to be strictly between P and NP-complete. **Shor's algorithm exploits a specific
  structure (periodicity), not general search power.**
- Grover gives **quadratic** speedup on unstructured search — so for NP-complete problems
  you get √(2ⁿ) instead of 2ⁿ, which is a real but modest improvement that **does not make
  intractable problems tractable**.

**[DURABLE] The honest summary of where speedups live:**

| Speedup | Problems | Confidence |
|---|---|---|
| **Exponential** | Factoring, discrete log, **simulating quantum systems**, some hidden-subgroup and number-theoretic problems | High for these specific cases |
| **Polynomial (usually quadratic)** | Unstructured search, some optimization, Monte Carlo amplitude estimation | High, but the constant factors and error-correction overhead may eat it (§9.3 → `quantum-software-and-resource-estimation`) |
| **Claimed but contested** | Most optimization heuristics, most quantum machine learning | **Low.** Many have been "dequantized" (§10.3 → `quantum-software-and-resource-estimation`) |
| **None expected** | Databases, web serving, general software, most business computing | Very high |

**[DURABLE] The strongest and least-hyped case is quantum simulation.** Feynman's original
1982 motivation: simulating quantum systems on classical computers costs exponential
resources; a quantum computer simulates them natively. Chemistry and materials science
remain the most defensible application, and notably, **it's the one where the exponential
advantage isn't in doubt.**

---
