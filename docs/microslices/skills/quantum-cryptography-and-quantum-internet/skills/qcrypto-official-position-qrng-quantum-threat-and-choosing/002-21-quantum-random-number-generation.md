---
id: skill-21-quantum-random-number-generation-0d13076d04
purpose: 21 quantum random number generation
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-official-position-qrng-quantum-threat-and-choosing/SKILL.md
requires: ["skill-20-the-official-position-7bcc15f1a1"]
links: ["skill-22-the-quantum-computing-threat-2efe278e36"]
---

## §21. Quantum Random Number Generation

**⚠️ The quantum security technology that is uncontroversially useful, and it deserves
separating from QKD.**
⚠️ **Measurement outcomes on a quantum superposition are fundamentally, not merely
practically, unpredictable — which makes a genuine entropy source.**
**⚠️ Implementations**: **photon path splitting, vacuum fluctuation measurement, phase
noise in lasers.**
**⚠️ The sober framing**: ⚠️ **NSA's position is that any RNG certified by appropriate
standards is acceptable if correctly implemented — so QRNG is fine, and is not
categorically required.** **⚠️ In practice a well-implemented OS CSPRNG seeded properly
(see a cryptography reference) is sufficient for almost all purposes, and QRNG's real value
is as a high-quality entropy source for seeding, and where certification demands it.**
⚠️ **Note that a QRNG still needs post-processing and health testing — a raw quantum source
with a device bias is just a biased source.**

---
