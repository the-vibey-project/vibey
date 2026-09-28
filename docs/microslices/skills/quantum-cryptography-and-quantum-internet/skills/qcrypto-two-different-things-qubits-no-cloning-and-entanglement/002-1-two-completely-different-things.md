---
id: skill-1-two-completely-different-things-27c17c31ca
purpose: 1 two completely different things
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-two-different-things-qubits-no-cloning-and-entanglement/SKILL.md
requires: ["skill-0-routing-cc1520aff4"]
links: ["skill-2-qubits-and-measurement-f5d23f044b"]
---

## §1. ⚠️ Two Completely Different Things

```
⚠️ POST-QUANTUM CRYPTOGRAPHY (PQC)
   ⚠️ Classical maths, ordinary computers, software upgrade
   ⚠️ Lattice/hash/code-based problems believed hard for quantum
   ⚠️ Works over the existing internet, end to end, at any distance
   ⚠️ Provides KEY EXCHANGE *AND* SIGNATURES/AUTHENTICATION
   ⚠️ Standardized (FIPS 203/204/205) and being deployed NOW
   ⚠️ THIS IS WHAT EVERY MAJOR AGENCY RECOMMENDS

⚠️ QUANTUM KEY DISTRIBUTION (QKD)
   ⚠️ Physics, special hardware, dedicated fibre or line of sight
   ⚠️ Security from quantum mechanics, not computational hardness
   ⚠️ Distance-limited; needs trusted nodes or repeaters (§13, §14)
   ⚠️ Provides KEY DISTRIBUTION ONLY — ⚠️ NO AUTHENTICATION
   ⚠️ Niche deployment; ⚠️ several agencies recommend against (§20)
```
> **⚠️ GOTCHA — the deepest confusion is that QKD does NOT protect against quantum
> computers in the way people assume.** ⚠️ **The quantum computing threat is to classical
> PUBLIC-KEY cryptography (§22 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`). QKD addresses key distribution — and because it needs
> authentication it cannot supply, it must be combined with classical cryptography anyway
> (§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`).** **⚠️ So QKD does not remove the classical dependency; it relocates it.**
> ⚠️ **This is not a fringe criticism — it is the central structural objection made by
> national agencies** (§20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`).

---

# PART I — THE PHYSICS
