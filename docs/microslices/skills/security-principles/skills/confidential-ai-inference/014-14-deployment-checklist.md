---
id: skill-14-deployment-checklist-28e4ad55eb
purpose: 14 deployment checklist
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-13-public-systems-as-publicly-described-5316c45f34"]
links: ["skill-15-common-failure-modes-6ca8b1bb28"]
---

## 14. Deployment checklist

**Threat model and claims**
- [ ] Written threat model naming every party in §2 and what each is trusted for; reviewed with `threat-modeling-playbook`.
- [ ] Public claims say exactly what is protected (prompts, outputs, weights, metadata) and from whom — no broader.

**Platform**
- [ ] Confidential VM on SEV-SNP or TDX at a current TCB; GPU in CC mode (not developer-tools); debug off everywhere.
- [ ] Minimal immutable guest: measured kernel or UKI, dm-verity root, no SSH, shell, package manager or debug endpoints.
- [ ] Guest kernel and drivers hardened for a malicious host; device and shared-memory interfaces reviewed.

**Attestation and binding**
- [ ] Client verifies CPU and GPU evidence, the CPU–GPU binding, freshness and key binding; fails closed.
- [ ] Minimum TCB and accepted TDX statuses defined in policy; host-controlled fields pinned or ignored.
- [ ] TLS or HPKE terminated inside the TEE; no plaintext hop outside it.

**Transparency and supply chain**
- [ ] Reproducible builds; SLSA provenance; signed release manifests including model and tokenizer digests.
- [ ] Manifests in an append-only log with witnesses; clients check inclusion and consistency; monitors running.
- [ ] Source, measurement calculators and a research environment published for independent audit.

**Keys and data**
- [ ] All secrets released by attestation-gated KMS; policy under multi-party control; changes logged.
- [ ] Weights encrypted at rest, decrypted only in the TEE; never on host-visible disk.
- [ ] Logging allow-list; core dumps off; metrics coarsened; abuse-monitoring behaviour published.
- [ ] Stateless request handling; per-user or per-tenant KV and prefix caches.

**Privacy of identity**
- [ ] OHTTP through an independently operated relay; consistent key configuration for all clients.
- [ ] Anonymous tokens for authorization; no identifiers inside encapsulated requests.
- [ ] Response padding and token batching against length and timing side channels.

**Operations**
- [ ] TCB-recovery runbook; key-rotation schedule; incident plan that works without prompt logs.

---
