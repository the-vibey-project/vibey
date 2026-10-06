---
id: skill-12-reference-architecture-830f2bc1f0
purpose: 12 reference architecture
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-11-updates-rotation-and-incident-response-9783d82355"]
links: ["skill-13-public-systems-as-publicly-described-5316c45f34"]
---

## 12. Reference architecture

```
  Client app (open source, verifies)                 Transparency log  <-- witnesses cosign checkpoints
    | 1. fetch key config + evidence bundle  <------ release manifests: image, measurements, weight digests
    | 2. verify chain, TCB, debug, measurements,           ^
    |    inclusion + consistency, nonce, key binding       | published by reproducible build pipeline
    | 3. HPKE-encapsulate request (Binary HTTP)
    v
  OHTTP relay  (organization A)          sees: client IP, timing, sizes      not: content
    v
  Cloud load balancer / router           sees: ciphertext, sizes, timing    not: content, client IP
    v
  Attested gateway  (CVM, organization B)  HPKE private key released by KMS on attestation
    | 4. decapsulate, check Privacy Pass token, pick node, re-encrypt to node's attested key
    v
  Confidential GPU node(s):  CVM (SEV-SNP or TDX)  +  GPU in CC mode (SPDM session, encrypted bounce buffers)
    | 5. weights decrypted inside with key from KMS; inference; padded streaming response
    v
  response encapsulated to the client's response key, back through relay

  Key broker / KMS  -- releases keys only to evidence matching policy (measurement + TCB + debug off + GPU CC + fresh)
  Verifier          -- client-side library, or a named third-party service (then it is in the trusted set)
```

| Component | Sees plaintext prompt? | Sees client identity? | Trusted for |
|---|---|---|---|
| Client | Yes | Yes | Verifying correctly |
| OHTTP relay | No | IP address | Not colluding with the gateway operator |
| Cloud network and hosts | No | No (relay IP only) | Availability |
| Attested gateway | Yes, inside the TEE | No | Running the published, logged code |
| GPU node | Yes, inside the TEE | No | Running the published, logged code |
| KMS / key broker | No | No | Enforcing the logged release policy |
| Hardware vendors | No (absent compromise) | No | Roots of trust, firmware, endorsements |

Run `threat-modeling-playbook` STRIDE over each arrow: every arrow is a trust boundary, and the two "trusted for" columns are your assumption register.

---
