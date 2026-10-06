---
id: skill-5-remote-attestation-the-ietf-rats-model-rfc-9334-9d53a24197
purpose: 5 remote attestation the ietf rats model rfc 9334
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-4-gpu-confidential-computing-and-the-cpu-gpu-path-40ad89339f"]
links: ["skill-6-binding-attestation-to-the-channel-and-what-the-client-must-check-9930a43cf7"]
---

## 5. Remote attestation: the IETF RATS model (RFC 9334)

**RFC 9334** (*Remote ATtestation procedureS (RATS) Architecture*, January 2023) gives the vocabulary every design review should use.

### Roles

| Role | In a confidential inference deployment |
|---|---|
| **Attester** | The confidential VM plus GPU, producing evidence |
| **Verifier** | Appraises evidence against policy — a client library, your service, or a SaaS verifier |
| **Relying Party** | Acts on the result — the client deciding to send a prompt; the KMS deciding to release a key |
| **Endorser** | Vouches for the attester's signing capability — AMD (VCEK chain), Intel (PCK chain), NVIDIA (device CA) |
| **Reference Value Provider** | Publishes expected measurements — your reproducible release pipeline, NVIDIA RIMs |
| **Verifier Owner / Relying Party Owner** | Set the appraisal policies |

### Conceptual messages

- **Evidence** — signed claims about the attester (the SNP report, TDX Quote, CCA token, GPU report).
- **Endorsements** — vendor statements that make the evidence trustworthy (certificate chains, TCB info).
- **Reference Values** — the measurements you expect.
- **Appraisal Policy for Evidence** — the verifier's rules; **Appraisal Policy for Attestation Results** — the relying party's rules.
- **Attestation Results** — the verifier's signed verdict (often a JWT or EAT) consumed by the relying party.

**Topologies:** in the **passport model** the attester obtains an attestation result and presents it to the relying party; in the **background-check model** the relying party forwards raw evidence to a verifier. CPU-plus-GPU is a **composite attester** — each component's evidence must be appraised and linked.

### Measurements

- **Launch measurement:** SEV-SNP `MEASUREMENT`, TDX `MRTD`, CCA Realm Initial Measurement. Covers only what was loaded at launch — everything later must be *chained*.
- **Runtime measurements:** TDX `RTMR`s, CCA extensible measurements, and **TPM PCRs** (including a **vTPM** inside the CVM, hosted by a paravisor or SVSM). A vTPM is only meaningful if its attestation key is bound to the hardware report (for example, its public key hash in `REPORT_DATA`).
- **Event logs:** a PCR or RTMR value is an opaque hash chain. The verifier must **replay the event log** (TCG PC Client firmware event log, or the kernel's IMA log) to recompute the register *and then appraise each event*.

### Freshness

RFC 9334 discusses nonces, timestamps and epoch identifiers. For interactive inference, use a **client-chosen nonce** in `REPORT_DATA` or the equivalent, or a short-lived signed attestation result whose validity window your policy bounds. Cached evidence without freshness invites replay of a report from a since-revoked TCB.

### Formats and open implementations

- **EAT** — *The Entity Attestation Token* (RFC 9711, 2025) ⚠️ verify the RFC number and date.
- **CoRIM** — Concise Reference Integrity Manifest (`draft-ietf-rats-corim`) for reference values and endorsements ⚠️ verify status.
- **EAR** — EAT Attestation Results (`draft-ietf-rats-ar4si` and related) ⚠️ verify status.
- **Veraison** (open-source verifier components) and **Trustee** (the Confidential Containers key broker and attestation service) are vendor-neutral starting points.

### Verifier services (third parties join your trusted set)

Intel Trust Authority; Microsoft Azure Attestation; Google Cloud Attestation (used by Confidential Space); NVIDIA Remote Attestation Service; AWS Nitro Enclaves attestation documents verified directly or by AWS KMS ⚠️ verify current product names. Delegating appraisal adds the verifier to the trusted set; verifying on the client removes it but means shipping collateral, revocation data and policy updates to every client.

---
