---
id: skill-section-7-post-quantum-cryptography-pqc-401de13328
purpose: section 7 post quantum cryptography pqc
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-6-controls-for-agentic-systems-4eacbc54c6"]
links: ["skill-section-8-10-point-agentic-security-design-checklist-9a315ee0f1"]
---

## SECTION 7 — Post-Quantum Cryptography (PQC)

### Finalized NIST Standards (August 13, 2024)
- **FIPS 203 (ML-KEM)** — from CRYSTALS-Kyber; key encapsulation / key exchange
- **FIPS 204 (ML-DSA)** — from CRYSTALS-Dilithium; digital signatures
- **FIPS 205 (SLH-DSA)** — from SPHINCS+; stateless hash-based signatures
- **FN-DSA (FALCON)** — forthcoming (fourth standard)

### Why Key Exchange Migration Is Urgent NOW
"Harvest now, decrypt later" is an active threat: adversaries archive today's encrypted traffic to decrypt once they have a quantum computer. Any data with a >10-year confidentiality requirement is already at risk.

### Migration Priority
1. **Migrate key exchange first:** hybrid TLS 1.3 with **X25519MLKEM768**
2. **Defer signature migration** — lower urgency, larger performance/payload tradeoff

### Implementation State (mid-2026)
- **OpenSSL 3.5** (April 2025): full ML-KEM/ML-DSA/SLH-DSA support
- **OpenSSH 10+:** mlkem768x25519 is the default key exchange
- **52% of human-generated web traffic** was post-quantum encrypted by early December 2025 (Cloudflare Radar 2025 Year in Review) — nearly doubled from 29% at year-start
- **Apple iOS 26 / macOS Sequoia:** PQC enabled by default (September 2025)
- **US EO 14144** (January 2025): pushes federal PQC procurement
- Cloudflare targets full PQC by 2029; Azure and other cloud providers rolling out PQC across services

### Strategic Goal: Crypto-Agility
Inventory all cryptographic usage, abstract algorithms behind interfaces, and ensure you can swap algorithms without architectural changes. This is more valuable than any single algorithm choice.

---
