---
id: skill-1-the-protocol-stack-fundamentals-stable-8e7c57b845
purpose: 1 the protocol stack fundamentals stable
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-signal/SKILL.md
requires: []
links: ["skill-2-what-signal-the-organisation-is-and-what-it-costs-verified-78128f03fa"]
---

## 1. The protocol stack (fundamentals — stable)

### 1.1 Key establishment: X3DH → PQXDH
Classic Signal sessions start with **X3DH** (Extended Triple Diffie–Hellman): each user has a
long-term identity key (IK), publishes a signed pre-key (SPK) and one-time pre-keys (OPKs) to the
server, and an initiator computes up to four DH combinations to bootstrap a shared secret. The
server's pre-key bundles stand in for online presence — that's what makes messaging asynchronous.

The four combinations, concretely — Alice initiating to an offline Bob:

```
DH1 = DH(IK_A, SPK_B)             // Alice identity key  + Bob signed pre-key
DH2 = DH(EK_A, IK_B)              // Alice ephemeral key + Bob identity key
DH3 = DH(EK_A, SPK_B)             // Alice ephemeral key + Bob signed pre-key
DH4 = DH(EK_A, OPK_B)             // Alice ephemeral key + Bob one-time pre-key (when one is left)
SK  = KDF(DH1 ‖ DH2 ‖ DH3 ‖ DH4)  // HKDF
```

DH1 authenticates Alice to Bob, DH2 authenticates Bob to Alice, DH3/DH4 supply freshness; Alice
verifies the signature on SPK_B before any of it. **A server compromised later cannot reconstruct
SK**: it only ever held public keys, and EK_A was generated for this one session and discarded.

**PQXDH** (shipped 2023) keeps X3DH intact and adds a post-quantum KEM: the responder uploads
an ML-KEM-1024 ("last resort") pre-key, the initiator encapsulates against it, and the KEM secret
is mixed with the DH secret so an attacker must break *both*. Crucially it upgrades **initial
secrecy** against harvest-now-decrypt-later without changing the ratchet — ongoing forward
secrecy and post-compromise healing stayed classical until 2025.

### 1.2 The Double Ratchet
Two ratchets stacked:
- a **DH ratchet**: each new message direction change triggers a fresh ephemeral DH, producing
  new root/chain keys — gives **post-compromise security** (self-healing);
- a **symmetric ratchet**: a hash chain inside each direction giving per-message keys — gives
  **forward secrecy** at message granularity.
Out-of-order delivery is handled by caching skipped message keys (bounded by `MAX_SKIP`).

### 1.3 The Triple Ratchet — SPQR goes to production (verified)
In October 2025 Signal announced **SPQR (Sparse Post-Quantum Ratchet)**: a second, quantum-safe
ratchet layered on the Double Ratchet, making the **Triple Ratchet**. Mechanics per
[Signal's announcement (2 Oct 2025)](https://signal.org/blog/spqr/) and the
[research collaborators' write-up (PQShield)](https://pqshield.com/diving-into-signals-new-pq-protocol/):
- uses **ML-KEM-768** for continuous post-quantum forward secrecy *and* post-compromise security;
- ML-KEM ciphertexts/keys are far too big for a chat message, so SPQR **erasure-codes key
  material into ~42-byte chunks** dribbled across ordinary messages (~40 bytes/message overhead)
  — "sparse" because ratchet steps complete opportunistically rather than blocking send;
- rollout is **heterogeneous with safe downgrade**: new clients attach SPQR data old clients
  ignore; downgrade is only permitted during the first messages of a session and is MAC-protected;
  once the fleet has upgraded, Signal plans an update that **enforces SPQR and archives
  non-protected sessions** — the "full coverage" point (future update, implied 2026);
- implementation is Rust, continuously **formally verified**: ProVerif models plus hax/F*
  transpilation run in CI; academic co-design with Cryspen, PQShield, AIST and NYU (papers at
  Eurocrypt '25 and USENIX Security '25; see also Signal's
  [NIST presentation](https://csrc.nist.gov/csrc/media/presentations/2025/post-quantum-ratcheting-for-signal/post-quantum_ratcheting-schmidt_1.14.pdf)
  and [SPIQE 2025 roadmap talk](https://spiqe.cool/2025/slides/SPIQE-Schmidt-Signal.pdf)).
- Open source at [signalapp/SparsePostQuantumRatchet](https://github.com/signalapp/SparsePostQuantumRatchet).

This is the current state of the art: by Apple's own level-0–3 taxonomy, the Triple Ratchet plus
PQXDH is the "Level 3" pattern (PQ-secured establishment *and* ongoing rekeying) that iMessage
PQ3 pioneered at scale in 2024.

### 1.4 Multi-device and identity: Sesame
Signal doesn't expose device-per-device chat; the **Sesame protocol** fan-outs per-device
sessions under a stable identity, and client-side distribution handles device add/remove. From
a user's perspective one conversation; from the protocol's, N parallel ratchets.

### 1.5 Sealed Sender (metadata hardening)
Normally the server must know the sender to route and rate-limit. **Sealed Sender** encrypts even
the sender identity into the envelope body and authenticates delivery via bearer **delivery
tokens** issued at registration (with profile-key-derived tokens for your contacts). Signal's
servers aim to learn only destination timing — the design explicitly limits the metadata the
operator itself could ever hand over.

### 1.6 Zero-knowledge groups (zkgroup)
Group membership, roles and even your own profile attributes are expressed as **anonymous
credentials** (keyed-verification algebraic MAC schemes, CMZ-family, analysed in the
Chase–Perrin–Zaverucha "Signal Groups / ACME" work). The server authenticates *that you're an
authorised member of group X* without learning *who you are* or who else is in it. Same trick
powers private profile storage.

### 1.7 PIN-protected secrets: SVR
**Secure Value Recovery** lets a 4-digit(+) PIN recover your profile/settings/social-graph seeds
on a new phone without Signal being able to read them: SVR2 ran a memory-hard KDF (Argon2-ish)
inside Intel **SGX enclaves** with a Raft-replicated enclave cluster; SVR3 (announced 2023)
hardens the migration path to future enclave platforms. Lesson for builders: "let users restore a
key from a short secret" forces you into threshold/HSM/enclave engineering — there is no cheap
version.

### 1.8 Private contact discovery: CDSI
Who in your address book is on Signal, without Signal learning your address book: the
**Contact Discovery Service (CDSI/CDSv2, "Ice Lake")** does it inside **SGX enclaves over Path
ORAM** so even memory-access patterns leak nothing (Signal's [2017 preview](https://signal.org/blog/private-contact-discovery/),
[2022 ORAM deep-dive](https://signal.org/blog/building-faster-oram/), repo
[signalapp/ContactDiscoveryService-Icelake](https://github.com/signalapp/contactdiscoveryservice-icelake/)).
Caveat for the threat-model file: researchers at V12 found critical object-lifetime bugs in CDSI
that compromised the enclave on the same Azure SGX hardware Signal uses — responsibly disclosed
and fixed ([v12.sh write-up](https://v12.sh/blog/signal)). Enclaves reduce trust; they never
eliminate it. Since **usernames** (Feb 2024), discovery is largely optional — you can hide your
number entirely and be reached by handle or QR.

### 1.9 Backups, at last (verified)
Until 2025 Signal deliberately had *no* cloud backup (Android had local encrypted ones; iOS had
transfer only). On **8 September 2025 Signal shipped opt-in Secure Backups**
([announcement](https://signal.org/blog/introducing-secure-backups/),
[help centre](https://support.signal.org/hc/en-us/articles/9708267671322-Signal-Secure-Backups)):
zero-knowledge, keyed by a 64-char recovery key generated on-device; free tier = all text (100 MiB)
+ last 45 days of media; **paid tier $1.99/month for 100 GB — Signal's first-ever paid feature**
([TechCrunch](https://techcrunch.com/2025/09/08/signal-introduces-free-and-paid-backup-plans-for-your-chats/)).
Backups are stored unlinked from account or payment identity; media is double-encrypted with size
padding; view-once and <24h-disappearing messages are excluded; backups refresh daily. iOS/Desktop
followed Android.

### 1.10 Group calls
1:1 calls are P2P where possible with Signal-operated **relay** fallback (so IPs need not be
exposed); group calls (up to 50) run through a Signal-operated **SFU** that forwards
per-participant E2E-encrypted streams. "Call relay" is a user toggle — IP-vs-latency.

---
