---
id: skill-14-learning-it-b9d7607d1d
purpose: 14 learning it
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-reference/SKILL.md
requires: []
links: ["skill-15-myths-and-anti-patterns-4afb01dfd9"]
---

## §14. Learning It

**[DURABLE] Prerequisites, honestly:** **linear algebra is essential and non-negotiable**
(complex vector spaces, unitary and Hermitian matrices, tensor products, eigendecomposition
— tensor products in particular are where most people stall). Probability, and comfort with
complex numbers. **Physics background is helpful but genuinely not required** for the
computing side. Programming: Python.

**The path**: linear algebra → qubits and single-qubit gates → multi-qubit gates and
entanglement → the standard algorithms (Deutsch–Jozsa → Bernstein–Vazirani → Grover →
Shor) → noise → error correction → whichever application domain you care about.

**⚠️ The failure mode is skipping the linear algebra.** Every popular-science analogy
(the coin that's both heads and tails, "trying all answers at once") actively obstructs
understanding, and you will have to unlearn them. **Work through Nielsen & Chuang's early
chapters or Qiskit's textbook with the math in front of you**, and run everything on a
simulator as you go.

---
