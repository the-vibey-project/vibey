---
id: skill-28-method-a5817d7bf5
purpose: 28 method
source: src/vibey_tools/skills/plugins/cryptography-and-encryption/skills/crypto-reference/SKILL.md
requires: ["skill-27-quick-reference-ea0f9e658f"]
links: []
---

## §28. Method

**§1–§22 → `crypto-what-it-solves-threat-models-randomness-hashes-and-macs`, `crypto-symmetric-aead-public-key-and-signatures`, `crypto-passwords-tls-pki-messaging-and-disk-encryption`, `crypto-implementation-failures-key-management-and-agility`, `crypto-advanced-constructions-blockchain-and-policy` rests on settled cryptography and long-established engineering practice** —
**the primitives, the AEAD recommendation, the failure-mode catalogue, and key management
discipline.** ⚠️ **None of it needed verification; nonce reuse has been catastrophic for
decades and Kerckhoffs published in 1883.**

**Two searches were run in August 2026**, on **post-quantum migration** and **TLS
certificate lifetimes** — ⚠️ **both chosen because they are §19 → `crypto-implementation-failures-key-management-and-agility`'s crypto-agility lesson
arriving as hard deadlines, and both change what you should be building today rather than
being interesting background.**

**Confidence.** **High** in §7 → `crypto-symmetric-aead-public-key-and-signatures`, §17 → `crypto-implementation-failures-key-management-and-agility` and §18 → `crypto-implementation-failures-key-management-and-agility`, which are the sections I'd most want read.
⚠️ **"Encryption without authentication is broken" is the single most actionable rule here,
and the malleability of unauthenticated ciphertext is the thing people who have only read
about "encryption" reliably don't know.** ⚠️ **§17 → `crypto-implementation-failures-key-management-and-agility`'s nonce reuse entry is the specific
failure I'd flag hardest — it is catastrophic, it is easy to do accidentally via counters
that reset, and in GCM it can expose the authentication key entirely.** **§18 → `crypto-implementation-failures-key-management-and-agility` is the honest
answer to where systems actually fail.**

**High** on §23.1's standards and dates, which trace to NIST's own publications and are
consistent across academic and industry sources: ⚠️ **FIPS 203/204/205 finalized August
2024, IR 8547's 2030 deprecation and 2035 disallowance, CNSA 2.0's algorithm selections, and
the key sizes.** ⚠️ **The June 2026 executive order and OMB memo details come via secondary
reporting rather than the primary documents and I've attributed them as such.** ⚠️ **The
point I'd most want carried is the AES-256 clarification — PQC migration is a public-key
problem, and the widespread belief that quantum computers break symmetric encryption is
simply wrong.** **⚠️ The SIKE/Rainbow breaks during evaluation are the honest reason hybrid
deployment is standard, and I've included them because the marketing around PQC rarely
mentions that two candidates fell mid-competition.**

**High** on §23.2's schedule, which comes from the ballot itself and is reported identically
across many CAs: ⚠️ **SC-081v3 passed 11 April 2025; 200 days from March 2026, 100 from
March 2027, 47 from March 2029, with DCV reuse falling to 10 days.**
⚠️ **The vote tally and the DigiCert 199-day detail are single-source and marked as
reported.** ⚠️ **Sourcing caution stated in-section: nearly all commentary here comes from
certificate authorities and certificate-lifecycle-management vendors who sell the automation
this creates demand for — which is why I've included the criticism that short expiry may be
substituting for fixing revocation, and that the beneficiaries voted for it.**
