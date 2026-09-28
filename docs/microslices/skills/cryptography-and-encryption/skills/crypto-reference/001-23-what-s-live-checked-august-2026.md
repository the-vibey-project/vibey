---
id: skill-23-what-s-live-checked-august-2026-a719c82920
purpose: 23 what s live checked august 2026
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-reference/SKILL.md
requires: []
links: ["skill-24-misconceptions-317781149b"]
---

## §23. What's Live — checked August 2026

> **⚠️ Two migrations are underway simultaneously, and both are §19 → `crypto-implementation-failures-key-management-and-agility`'s lesson arriving as
> a deadline. Verify current status — these have specific dates that are moving through.**

### 23.1 ⚠️ Post-quantum cryptography: standards settled, deadlines now real
**⚠️ The largest cryptographic transition in the history of deployed systems, and the
algorithm question is closed — only sequencing and timing remain open.**

- **⚠️ THE STANDARDS, finalized August 2024 after an eight-year process:**
```
⚠️ ML-KEM (FIPS 203)  ⚠️ from CRYSTALS-Kyber. Module-lattice KEM,
   IND-CCA2. ⚠️ Replaces RSA and ECDH KEY EXCHANGE
   ⚠️ Public keys ~800–1568 bytes, ciphertexts ~768–1568 bytes
⚠️ ML-DSA (FIPS 204)  ⚠️ from CRYSTALS-Dilithium. Lattice signatures
   ⚠️ ~2420–4595 bytes — replaces ECDSA and RSA signing
⚠️ SLH-DSA (FIPS 205)  ⚠️ from SPHINCS+. Hash-based, ⚠️ security
   resting SOLELY on hash properties — a structural hedge against
   lattice cryptanalysis. ⚠️ Signatures ~7856–49856 bytes
⚠️ HQC selected March 2025 as a code-based BACKUP KEM;
   a Falcon-based signature standard is expected
```
- **⚠️ THE DEADLINES.** ⚠️ **NIST IR 8547 (initial public draft, November 2024) schedules
  RSA-2048 and ECC P-256 — the ~112-bit-security algorithms — DEPRECATED BY 2030 and
  DISALLOWED AFTER 2035.** ⚠️ **Reporting indicates a June 2026 executive order (14412)
  treats the 2030 date as a compliance deadline for federal high-value assets, with OMB
  guidance directing alignment to IR 8547 and 2035 for full migration.**
  ⚠️ **NSA CNSA 2.0 requires national security systems to migrate by 2030–2035, specifying
  ML-KEM-1024 and ML-DSA-87 alongside AES-256 and SHA-384/512.** ⚠️ **The EU published a
  coordinated roadmap in June 2025 with national strategies and cryptographic inventories
  expected by end-2026 and critical infrastructure high-risk transition by 2030.**
- **⚠️ AES-256 DOES NOT NEED REPLACING.** ⚠️ **PQC migration is about PUBLIC-KEY
  cryptography, where Shor's algorithm applies.** **⚠️ Symmetric algorithms face Grover's
  algorithm, which roughly halves effective key strength — and AES-256 already accommodates
  that.** ⚠️ **This is the single most common misunderstanding of the whole transition.**

> **⚠️ GOTCHA — "HARVEST NOW, DECRYPT LATER" is why this is urgent despite no quantum
> computer existing.** ⚠️ **An adversary recording encrypted traffic today can decrypt it
> retrospectively once a cryptographically relevant quantum computer exists.**
> **⚠️ Therefore: any data encrypted today with RSA or ECC that must stay confidential for
> more than roughly 5–10 years is ALREADY exposed.** ⚠️ **The relevant question is not
> "when will quantum computers arrive" but "how long must this stay secret, plus how long
> will migration take" — and if that sum exceeds the arrival date, you are already late.**

**⚠️ Why HYBRID deployment is the norm, and this is the nuance that gets lost.**
⚠️ **In TLS, ML-KEM is deployed combined with classical ECDH — X25519MLKEM768 — providing
security against both classical and quantum adversaries simultaneously.** ⚠️ **NIST
explicitly endorses hybrids during the transition, and the reason is honest caution: the
PQC candidates represent a comparatively young attack surface.**
⚠️ **The cautionary evidence is concrete: SIKE and Rainbow were BROKEN DURING the NIST
evaluation — SIKE by a polynomial-time attack in 2022 — demonstrating that absence of known
attacks differs fundamentally from proof of hardness.** ⚠️ **And implementations have proven
fragile, with side-channel attacks reported recovering ML-KEM and Dilithium keys from both
masked and unmasked implementations** (§17 → `crypto-implementation-failures-key-management-and-agility`).
**⚠️ The practical obstacles are §19 → `crypto-implementation-failures-key-management-and-agility`'s**: ⚠️ **larger keys and signatures break size
assumptions in protocols and constrained hardware, and the cryptographic INVENTORY problem
is the real blocker — organizations cannot migrate what they have not found.**

### 23.2 ⚠️ TLS certificate lifetimes are collapsing toward 47 days
**⚠️ §13 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`'s unsolved revocation problem being addressed by making certificates expire fast
instead — and it is forcing automation across the entire web.**

- **⚠️ CA/Browser Forum Ballot SC-081v3, proposed by Apple and passed 11 April 2025** —
  ⚠️ **reportedly 29 votes in favour, none opposed, with five abstentions.**
- **⚠️ THE SCHEDULE:**
```
⚠️ Until 15 March 2026   398 days (DCV reuse 398 days)
⚠️ From 15 March 2026    200 days (DCV reuse 200 days)
⚠️ From 15 March 2027    100 days
⚠️ From 15 March 2029    ⚠️ 47 days, ⚠️ DCV reuse 10 DAYS
```
- **⚠️ The DCV reuse collapse is the part that actually forces the change.** ⚠️ **At 47-day
  validity with 10-day domain-control-validation reuse, domain ownership must be re-proved
  roughly 35 times per year per domain.** ⚠️ **Email-based validation and manual HTTP file
  placement are not viable at that frequency — ACME automation via DNS-01 or HTTP-01
  becomes effectively the only practical method.**
- **⚠️ The stated rationale** is §13 → `crypto-passwords-tls-pki-messaging-and-disk-encryption`'s: ⚠️ **shorter lifetimes reduce the window in which a
  certificate remains valid after its information is no longer accurate, and the ballot
  explicitly treats revocation's limitations as given and uses expiry as the workaround.**

> **⚠️ GOTCHA — a practical detail that catches people: the ballot numbers are NOT what CAs
> issue.** ⚠️ **DigiCert, for instance, moved to a 199-day maximum from 24 February 2026
> rather than 200 — validity limits are precise to the second, so CAs issue just under the
> cap.** **⚠️ Don't build automation that assumes exactly 200.**
> **⚠️ Scope limit worth knowing: this covers PUBLICLY TRUSTED TLS certificates only.**
> ⚠️ **Private/internal PKI is unaffected and can still issue multi-year certificates; code
> signing and S/MIME operate under different rules.**

**⚠️ The honest criticism, which is worth recording.** ⚠️ **The change is not universally
regarded as pure security benefit: critics note that CAs and certificate lifecycle
management vendors profit from the acceleration, and that using short expiry as a substitute
for working revocation may be pragmatic engineering or may be accumulating technical debt —
that question is genuinely open.**
⚠️ **Note also that much of the available commentary comes from CAs and CLM vendors selling
the solution, which I have weighted accordingly.**
**⚠️ The operational advice is unambiguous regardless**: ⚠️ **inventory every publicly
trusted certificate and its renewal method now; identify infrastructure without ACME
support, because that is where the risk concentrates; and treat the 2026 step as the forcing
function rather than waiting for 2029.** ⚠️ **A separate ballot (SC-085v2) requiring CAs to
validate DNSSEC took effect on the same March 2026 date.**

---
