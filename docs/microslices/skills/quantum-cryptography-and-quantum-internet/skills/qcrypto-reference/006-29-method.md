---
id: skill-29-method-fb6e827e7e
purpose: 29 method
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-reference/SKILL.md
requires: ["skill-28-quick-reference-93a13448cd"]
links: []
---

## §29. Method

**§1–§23 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`, `qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation`, `qcrypto-security-claims-attacks-and-trusted-nodes`, `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`, `qcrypto-official-position-qrng-quantum-threat-and-choosing` rests on settled quantum information theory and a well-documented attack
literature** — **no-cloning, BB84, privacy amplification, the photon-number-splitting and
detector-blinding attacks, and the repeater architecture.** ⚠️ **None of it needed
verification; BB84 is from 1984 and the no-cloning theorem from 1982.**

**Two searches were run in August 2026**, on **agency positions on QKD** and **quantum
repeater and network milestones** — ⚠️ **the first because I was going to assert a strong
claim about official scepticism and wanted it verified rather than remembered, the second
because §14 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`'s bottleneck is exactly where a genuine change would show up.**

**Confidence.** **High** in §1 → `qcrypto-two-different-things-qubits-no-cloning-and-entanglement`, §10 → `qcrypto-security-claims-attacks-and-trusted-nodes` and §11 → `qcrypto-security-claims-attacks-and-trusted-nodes`, which are the sections I'd most want read.
⚠️ **The QKD/PQC distinction is the single most useful thing here because the conflation is
near-universal in popular coverage.** ⚠️ **§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`'s authentication bootstrap is the structural
argument that decides the practical question: QKD cannot authenticate, so it needs either
classical public-key crypto or a pre-shared symmetric key — and in the second case you
could have used the symmetric key directly.** **⚠️ §11 → `qcrypto-security-claims-attacks-and-trusted-nodes` matters because "secure by physics"
is a claim about the protocol while every real break has been against the apparatus.**

**High** on §20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`, which traces to NCSC's own publication and to NSA's stated position as
reported consistently across many independent sources: ⚠️ **the NCSC will not support QKD
for government or military applications and states plainly that QKD does not provide
authentication; NSA does not recommend it for NSS; ANSSI calls it niche and not
sufficiently mature; CNSA 2.0 rejects it.**
⚠️ **I have deliberately included the published rebuttal, because this is a genuine
technical disagreement and the rebuttal's framing — that the assessment depends on which
technological epoch you assume — is a fair point that §24.1 partially vindicates.**
⚠️ **The DoD ban and the 2030 deadline come via secondary reporting rather than the
memorandum itself and are marked as reported.**

**High** on §24.1's headline result, which was published in Nature and is reported
consistently: ⚠️ **550 ± 36 ms coherence against 450 ms generation time over 10 km of
trapped-ion-linked fibre, plus the DI-QKD figures.**
⚠️ **The significance framing — that coherence exceeding generation time is the threshold
enabling multi-stage repeaters — is the sources' own and is the part worth carrying.**
⚠️ **I have been careful to pair it with the explicit statement that no commercial repeater
exists and that migration planning should not assume one, because the temptation to read a
Nature result as a deployment signal is exactly the error this section should prevent.**
**⚠️ Sourcing caution: several supporting items come from quantum-industry outlets with an
interest in the field appearing to advance, so I anchored on the primary journal reports
where possible and marked the rest.**
