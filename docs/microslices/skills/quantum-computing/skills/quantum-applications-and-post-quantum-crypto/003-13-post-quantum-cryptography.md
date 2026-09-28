---
id: skill-13-post-quantum-cryptography-246c9f6706
purpose: 13 post quantum cryptography
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-applications-and-post-quantum-crypto/SKILL.md
requires: ["skill-12-quantum-networking-and-sensing-dce2c7ef2e"]
links: []
---

## §13. Post-Quantum Cryptography

**[DURABLE] This is the part of quantum computing with the most immediate, concrete
consequences for ordinary organizations — and it does not depend on when quantum computers
arrive.**

### 13.1 The threat

**Shor's algorithm breaks RSA, Diffie-Hellman, and elliptic-curve cryptography.** Grover
halves the effective security of symmetric ciphers, so **AES-256 remains fine** and
SHA-384/512 are recommended.

**⚠️ "Harvest now, decrypt later" (HNDL) is why the timeline argument is a distraction.**
An adversary recording encrypted traffic today can decrypt it whenever a
cryptographically-relevant quantum computer exists. **If your data must stay confidential
for 10+ years, it is already exposed.** This applies to health records, state secrets,
long-lived financial data, and anything with a legal retention requirement.

### 13.2 The standards

**[VERSIONED]** NIST finalized three standards on **13 August 2024** after an eight-year
competition:

| FIPS | Algorithm | Purpose | Basis |
|---|---|---|---|
| **FIPS 203** | **ML-KEM** (CRYSTALS-Kyber) | Key encapsulation | Lattice |
| **FIPS 204** | **ML-DSA** (CRYSTALS-Dilithium) | Digital signatures | Lattice |
| **FIPS 205** | **SLH-DSA** (SPHINCS+) | Signatures | Hash-based — conservative backup |

**NIST also selected HQC in March 2025** as a fifth algorithm and additional KEM.
**HQC is code-based rather than lattice-based, providing a mathematically different backup
to ML-KEM** in case lattice assumptions fall — **its standard is still being drafted**, so
it is not yet deployable. **Use the FIPS names in procurement documents and specs.**

**⚠️ Use the FIPS versions, not the competition versions** — parameters changed during
standardization. And **prefer hybrid (classical + PQC) constructions** during transition:
ETSI and the EU explicitly encourage hybrids, and they protect you if a PQC algorithm is
broken (which has happened to competition candidates — SIKE and Rainbow were both broken
classically during the process).

### 13.3 The deadlines — now binding, not advisory

**[VERSIONED — verify against the current text; this is the highest-consequence table in
the document.]**

**NIST (IR 8547 transition roadmap):** quantum-vulnerable algorithms including **RSA and
ECC are deprecated after 2030 and disallowed after 2035**. Algorithms at the **112-bit
security level are deprecated after 2030 and disallowed after 2035** regardless.

**US federal civilian — this became obligation in 2026:**
- **EO 14412 ("Securing the Nation Against Advanced Cryptographic Attacks," June 2026)**
  mandates accelerated government-wide PQC migration, sets binding deadlines for high-value
  assets, and **directs the Federal Acquisition Regulatory Council to require contractor
  compliance** with NIST PQC standards.
- **OMB M-26-15** sets the phased schedule: agencies named a PQC migration lead by late
  July 2026 and owed a full migration plan by late October 2026; **inventories and planning
  through 2027, pilots through 2028, key establishment migrated by 31 December 2030,
  digital signatures by 31 December 2031, remaining systems by 2035.** It directs agencies
  to fold PQC into cloud migrations and hardware refresh cycles rather than run it
  standalone, and requires identification of systems that cannot support PQC or hybrid.
- **EO 14144** requires **TLS 1.3 (or successor) across federal systems by 2 January 2030.**

**US national security systems (NSA CNSA 2.0)** — excluded from the OMB track and moving
faster, with **ML-KEM-1024 and ML-DSA-87** specified alongside AES-256 and SHA-384/512:
software and firmware signing leads (**exclusive CNSA 2.0 use from 1 January 2027**),
**all new NSS acquisitions CNSA 2.0 compliant from 1 January 2027**, networking equipment
**by 2030**, operating systems / custom applications / cloud services **by 2033**, and
**full quantum resistance across all NSS by 2035**. ⚠️ **These extend across the defense
supply chain**, affecting contractors and vendors.

**EU** — the NIS Cooperation Group roadmap (June 2025): **initial national roadmaps and
awareness by 31 December 2026; high-risk use cases addressed by 31 December 2030; full
transition by 31 December 2035**, with a focus on standardized, tested hybrid solutions.

**UK NCSC** — three-phase guidance to 2035. **Australia (ASD)** is more aggressive,
advising elimination of classical public-key cryptography **by 2030**.

### 13.4 How to migrate

**[DURABLE]** In order: **(1) inventory your cryptography** — this is the hard part and
where every program stalls; you cannot migrate what you can't find, and it lives in TLS
configs, code signing, VPNs, HSMs, embedded firmware, third-party libraries, and vendor
products. **(2) Prioritize by data lifetime and HNDL exposure.** **(3) Build crypto-agility**
so the *next* migration is cheaper. **(4) Push vendors** — much of your exposure is in
products you don't control. **(5) Deploy hybrid first.** **(6) Watch the embedded and IoT
long tail**, where devices have 15-year lifetimes and no update path.

**Realistic enterprise timeline: 42–54 months from start to compliance.** The practical
dates arrive years before the printed ones, because hardware refresh cycles and vendor
readiness gate you.
