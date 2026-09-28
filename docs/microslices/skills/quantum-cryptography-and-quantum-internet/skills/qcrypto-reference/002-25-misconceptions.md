---
id: skill-25-misconceptions-1fb9ca2159
purpose: 25 misconceptions
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-reference/SKILL.md
requires: ["skill-24-what-s-live-checked-august-2026-0c8ff4161b"]
links: ["skill-26-numbers-b1b8e53c15"]
---

## §25. Misconceptions

| Misconception | Correction |
|---|---|
| Quantum cryptography and PQC are the same | ⚠️ **Nearly opposites. PQC is what's deployed** (§1 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`) |
| QKD protects against quantum computers | ⚠️ **It addresses key distribution; the threat is to public-key crypto** (§1 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`, §22 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |
| QKD is unhackable | ⚠️ **Real systems have been broken via hardware** (§11 → `qcrypto-security-claims-attacks-and-trusted-nodes`) |
| "Unconditional security" means no assumptions | ⚠️ **It means no COMPUTATIONAL assumptions. Others remain** (§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`) |
| QKD removes the need for classical crypto | ⚠️ **It cannot authenticate. It relocates the dependency** (§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`, §20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |
| QKD prevents eavesdropping | ⚠️ **It DETECTS it. You abort rather than use the key** (§6 → `qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation`) |
| An eavesdropper is stopped | ⚠️ **They can still deny service by disturbing the channel** (§20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |
| Quantum signals can be amplified like classical ones | ⚠️ **No-cloning forbids it. Hence repeaters** (§3 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`, §14 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`) |
| Entanglement allows faster-than-light signalling | ⚠️ **It doesn't. A classical channel is always needed** (§4 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`) |
| A national QKD backbone is end-to-end physics-secured | ⚠️ **Trusted nodes hold the key in the clear** (§13 → `qcrypto-security-claims-attacks-and-trusted-nodes`) |
| Single photons are used in practice | ⚠️ **Attenuated lasers. Hence decoy states** (§6 → `qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation`) |
| Advertised key rates are what you get | ⚠️ **Ask for SECRET key rate with finite-key analysis** (§9 → `qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation`) |
| Satellite QKD is untrusted end-to-end | ⚠️ **The satellite is typically a trusted node** (§17 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`) |
| Quantum internet exists | ⚠️ **Deployed networks are stage 1 of six** (§18 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`) |
| Quantum repeaters are available | ⚠️ **No commercial repeater exists** (§24.1) |
| The 2026 repeater results change migration plans | ⚠️ **They don't. Long engineering runway** (§24.1) |
| Europe investing means agencies were wrong | ⚠️ **Sovereignty and security-per-euro are different arguments** (§24.2) |
| QRNG is required for good randomness | ⚠️ **Any properly certified RNG is acceptable** (§21 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |
| Grover's algorithm breaks AES | ⚠️ **Halves effective strength. AES-256 is fine** (§22 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`) |

---
