---
id: skill-3-the-no-cloning-theorem-3e15946e77
purpose: 3 the no cloning theorem
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-two-different-things-qubits-no-cloning-and-entanglement/SKILL.md
requires: ["skill-2-qubits-and-measurement-f5d23f044b"]
links: ["skill-4-entanglement-and-bell-inequalities-d2d1b3367f"]
---

## §3. ⚠️ The No-Cloning Theorem

> **⚠️ The single result that makes quantum cryptography possible.**
⚠️ **An unknown quantum state CANNOT be copied. There is no operation that takes |ψ⟩ to
|ψ⟩|ψ⟩ for arbitrary unknown |ψ⟩.** **⚠️ It follows directly from the linearity of quantum
mechanics, which makes it about as fundamental as results get.**
**⚠️ Why it matters**: ⚠️ **classical eavesdropping is passive and undetectable — light in a
fibre can be split and copied with no trace.** ⚠️ **An eavesdropper on a quantum channel
cannot copy the state, so must measure it — and measurement in the wrong basis (§2)
introduces detectable errors.**
> **⚠️ GOTCHA — no-cloning also creates the central ENGINEERING problem** (§14 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`).
> ⚠️ **You cannot amplify a quantum signal, because amplification is copying.** **⚠️ So the
> classical solution to loss — put a repeater every 80 km — is unavailable, and this is
> precisely why quantum networks are hard and why the field needs quantum repeaters.**
> **⚠️ The property that provides the security is the same property that blocks the
> engineering.**

---
