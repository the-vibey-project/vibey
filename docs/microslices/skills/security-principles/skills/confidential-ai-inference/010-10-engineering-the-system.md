---
id: skill-10-engineering-the-system-ea23bd2dd7
purpose: 10 engineering the system
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-9-verifiable-inference-beyond-tees-6972b55a95"]
links: ["skill-11-updates-rotation-and-incident-response-9783d82355"]
---

## 10. Engineering the system

### Key release on attestation

Never bake secrets into images. The gateway's HPKE and TLS keys, weight-decryption keys and any log-encryption keys are released by a key broker **only to evidence that satisfies policy**:

- **Azure Key Vault Premium / Managed HSM Secure Key Release** — a release policy evaluated over Microsoft Azure Attestation token claims ⚠️ verify claim names.
- **AWS KMS with Nitro Enclaves** — key-policy condition keys on the attestation document, such as `kms:RecipientAttestation:ImageSha384` and `kms:RecipientAttestation:PCR<n>`.
- **Google Cloud Confidential Space** — workload identity federation with attribute conditions over the attestation token (image digest, support attributes) ⚠️ verify.
- **Confidential Containers Trustee** — a key broker service with policy (for example Rego) over appraised evidence.

Policy content: pinned measurement *or* "signed by the release key **and** included in the transparency log"; minimum TCB; debug off; GPU in CC mode; freshness. The **policy itself is a trust point** — whoever can edit it can release keys to anything. Put it under multi-party control, log every change, and treat KMS audit logs (which record each release and the evidence presented) as security records.

### Model-weight protection

- Encrypt weights at rest per shard (AEAD); decrypt only inside the CVM; move to the GPU only over the CC path.
- Never write plaintext weights to host-visible storage — use memory, or dm-crypt with a key held inside the TEE.
- Put weight and tokenizer digests in the release manifest so clients know *which* model answered.
- Be honest about the limit: weights are plaintext in CVM and GPU memory, so physical and side-channel attacks (§2) still apply, and **model extraction through the API is out of TEE scope** entirely.

### Logging without leaking prompts

- **Allow-list, not deny-list:** log only enumerated fields — status codes, bucketed latencies, model version, token counts if necessary. No request bodies, token text, embeddings, retrieved documents or tool arguments.
- **Disable core dumps and verbose GPU error dumps** in the measured image; they contain prompts.
- **Watch cardinality and joins:** precise per-request token counts with timestamps can re-identify content when joined with relay logs. Aggregate, coarsen, or add calibrated noise.
- **The logging code is attested code** — reviewers should be able to read the exporter configuration in the published source and confirm nothing else leaves.
- **Abuse monitoring:** if classifiers run inside the TEE, publish what they flag and what (if anything) leaves the boundary. An undisclosed exception is the most common way a confidential design quietly stops being one.

### Stateless design

- No persistent storage of prompts or outputs; conversation history, if any, is kept by the client and re-sent.
- **KV and prefix caches** are per-request state: isolate per user or tenant, or disable cross-user sharing (§2).
- Zero buffers after each request where the runtime allows; restart nodes on a schedule; generate ephemeral keys per boot.
- No SSH, no shell, no remote-exec, no debug or profiling endpoints in production images; remote management limited to a measured, narrow API.
- **Non-targetability:** the routing layer outside the TEE should not be able to steer a chosen user to a chosen node. Prefer client-side choice among attested nodes, or routing that cannot see identity (OHTTP plus anonymous tokens).

---
