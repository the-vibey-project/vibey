---
id: skill-2-qubits-and-measurement-f5d23f044b
purpose: 2 qubits and measurement
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-two-different-things-qubits-no-cloning-and-entanglement/SKILL.md
requires: ["skill-1-two-completely-different-things-27c17c31ca"]
links: ["skill-3-the-no-cloning-theorem-3e15946e77"]
---

## §2. Qubits and Measurement

**⚠️ A qubit can be in SUPERPOSITION** — ⚠️ **α|0⟩ + β|1⟩ — and the coefficients are
amplitudes, not probabilities, which is why interference is possible.**
```
⚠️ MEASUREMENT IS DESTRUCTIVE AND BASIS-DEPENDENT
   ⚠️ Measuring collapses the state to an eigenstate of the
      measured observable
   ⚠️ ⚠️ MEASURING IN THE WRONG BASIS gives a RANDOM result AND
      destroys the original information. This is the mechanism
      QKD exploits (§6)
⚠️ CONJUGATE BASES  ⚠️ rectilinear {|0⟩,|1⟩} and diagonal
   {|+⟩,|−⟩} are mutually unbiased — a state definite in one is
   maximally uncertain in the other
⚠️ PHYSICAL ENCODINGS  polarization · time-bin (⚠️ robust in fibre) ·
   phase · frequency · ⚠️ continuous variables (§8)
```
**⚠️ The uncertainty principle is the deeper statement**: ⚠️ **not "measurement disturbs"
as a practical limitation, but that conjugate properties do not simultaneously have
definite values.**

---
