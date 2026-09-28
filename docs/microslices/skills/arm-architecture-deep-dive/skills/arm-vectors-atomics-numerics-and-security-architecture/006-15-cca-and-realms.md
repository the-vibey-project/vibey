---
id: skill-15-cca-and-realms-ad1d3faa2e
purpose: 15 cca and realms
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-vectors-atomics-numerics-and-security-architecture/SKILL.md
requires: ["skill-14-pointer-authentication-bti-and-mte-06b0de8b99"]
links: []
---

## §15. CCA and Realms

**⚠️ Confidential Compute Architecture (ARMv9)** adds a ⚠️ **REALM world alongside Secure and
Non-secure — a fourth security state.**
**⚠️ The goal is confidential computing**: ⚠️ **a workload whose memory and state the
HYPERVISOR and host OS cannot read, so a cloud tenant need not trust the cloud operator's
software stack.**
**⚠️ The Realm Management Monitor (RMM)** at a new level manages realms; ⚠️ **the hypervisor
still schedules and allocates resources but cannot inspect realm memory — the separation of
management from access is the architectural trick.**
**⚠️ Attestation** lets a remote party verify what is running inside a realm (see a
digital-logic reference §22 on measured boot).
**⚠️ The comparison** is with Intel TDX and AMD SEV-SNP — ⚠️ **same problem, different
architecture, and none of them defends against a compromised root of trust or physical
attack.**
**⚠️ Maturity**: ⚠️ **the architecture is specified and silicon and software support are
still arriving; treat deployment claims sceptically.**

---

# PART IV — SYSTEM ARCHITECTURE
