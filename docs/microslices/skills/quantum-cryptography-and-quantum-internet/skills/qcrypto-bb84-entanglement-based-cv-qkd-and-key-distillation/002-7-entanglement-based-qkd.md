---
id: skill-7-entanglement-based-qkd-1df6061027
purpose: 7 entanglement based qkd
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation/SKILL.md
requires: ["skill-6-bb84-d8ee64094a"]
links: ["skill-8-continuous-variable-qkd-b7ea6427bd"]
---

## §7. Entanglement-Based QKD

**⚠️ E91 (Ekert, 1991)** uses entangled pairs: ⚠️ **a source distributes one photon to each
party, and correlated measurements produce the key.** **⚠️ Security comes from BELL
INEQUALITY VIOLATION — if the correlations are strong enough to violate Bell, monogamy
(§4 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`) bounds what any eavesdropper can know.**
**⚠️ BBM92** is the practical entangled-source variant.
**⚠️ Advantages**: ⚠️ **the source can sit in the middle and need not be trusted in some
formulations; and no key exists anywhere until measurement, so there is nothing to steal
in advance.**
**⚠️ Disadvantages**: ⚠️ **entangled sources are harder, and rates are lower.**

---
