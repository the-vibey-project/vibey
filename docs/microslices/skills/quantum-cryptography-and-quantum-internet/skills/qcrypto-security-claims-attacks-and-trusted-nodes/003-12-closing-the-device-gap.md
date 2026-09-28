---
id: skill-12-closing-the-device-gap-60a5d6a970
purpose: 12 closing the device gap
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-security-claims-attacks-and-trusted-nodes/SKILL.md
requires: ["skill-11-attacks-on-real-qkd-systems-644c7ac985"]
links: ["skill-13-trusted-nodes-a9e4b11045"]
---

## §12. Closing the Device Gap

**⚠️ MEASUREMENT-DEVICE-INDEPENDENT QKD (MDI-QKD)**: ⚠️ **both parties send to an untrusted
central node that performs a Bell measurement.** ⚠️ **Removes ALL detector side channels
(§11's worst class) at the cost of rate.** **⚠️ Practical and deployed in testbeds.**
**⚠️ TWIN-FIELD QKD** extends range substantially — ⚠️ **it scales with the square root of
channel transmittance rather than linearly, which lets it beat the repeaterless bound
(§5 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`) without quantum memory.**
**⚠️ DEVICE-INDEPENDENT QKD (DI-QKD)**: ⚠️ **the theoretical ideal — security derived from
observed Bell violation alone, treating the devices as black boxes.** ⚠️ **Requires
extremely high detection efficiency and loophole-free operation, which is why it has been
a laboratory curiosity rather than a technology — until recently** (§24.1 → `qcrypto-reference`).
**⚠️ Note what remains assumed even in DI-QKD**: ⚠️ **the labs don't leak, the random
choices are free, and the devices don't communicate with the adversary.**

---
