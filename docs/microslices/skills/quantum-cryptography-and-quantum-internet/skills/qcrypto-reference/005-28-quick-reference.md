---
id: skill-28-quick-reference-93a13448cd
purpose: 28 quick reference
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-reference/SKILL.md
requires: ["skill-27-sources-1f833e963d"]
links: ["skill-29-method-fb6e827e7e"]
---

## §28. Quick Reference

### 28.1 Picker
| Question | Where |
|---|---|
| Should we deploy QKD? | ⚠️ **Almost certainly PQC instead** (§23 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |
| Is QKD unhackable? | ⚠️ **No. Hardware attacks are demonstrated** (§11 → `qcrypto-security-claims-attacks-and-trusted-nodes`) |
| Does QKD replace classical crypto? | ⚠️ **No — it can't authenticate** (§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`) |
| What does "unconditional" mean? | ⚠️ **No computational assumptions. Others remain** (§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`) |
| Vendor claims physics-level security | ⚠️ **Ask the six questions in §24.2** |
| How far can QKD go? | ⚠️ **Limited by exponential loss; trusted nodes extend it** (§5 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`, §13 → `qcrypto-security-claims-attacks-and-trusted-nodes`) |
| Are quantum repeaters here? | ⚠️ **Threshold crossed in the lab; no product** (§24.1) |
| Does the 2026 news change my plans? | ⚠️ **No** (§24.1) |
| Why is Europe building QKD then? | ⚠️ **Sovereignty is a different argument** (§24.2) |
| Do I need a QRNG? | ⚠️ **A certified RNG is acceptable** (§21 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |
| What actually breaks my crypto? | ⚠️ **Shor's, against public-key. See a crypto reference** (§22 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |

### 28.2 Evaluating a QKD proposal
- [ ] ⚠️ **How is the classical channel authenticated — PQC or pre-shared key?** (§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`)
- [ ] ⚠️ **How many trusted nodes are in the path, and who operates them?** (§13 → `qcrypto-security-claims-attacks-and-trusted-nodes`)
- [ ] ⚠️ **Decoy states implemented?** (§6 → `qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation`)
- [ ] ⚠️ **Countermeasures for detector blinding and Trojan-horse attacks?** (§11 → `qcrypto-security-claims-attacks-and-trusted-nodes`)
- [ ] ⚠️ **Is the quoted rate SECRET key rate with finite-key analysis?** (§9 → `qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation`)
- [ ] ⚠️ **Offered ALONGSIDE PQC, or as a replacement?** (§23 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`)
- [ ] Independent certification, and against what scheme? (§11 → `qcrypto-security-claims-attacks-and-trusted-nodes`)
- [ ] ⚠️ **What is the denial-of-service posture?** (§20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`)
- [ ] ⚠️ **Total cost against a pre-shared-key or PQC alternative** (§23 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`)

---
