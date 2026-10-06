---
id: skill-11-updates-rotation-and-incident-response-9783d82355
purpose: 11 updates rotation and incident response
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-10-engineering-the-system-ea23bd2dd7"]
links: ["skill-12-reference-architecture-830f2bc1f0"]
---

## 11. Updates, rotation and incident response

- **Release flow:** reproducible build → sign → publish manifest to the transparency log → update reference values in the KMS policy → staged rollout. Clients accept only logged releases; retire old releases by removing them from the accepted set and giving reference values a validity period.
- **TCB recovery:** when AMD, Intel or NVIDIA publish a firmware or microcode fix with a TCB or security-version bump, raise the minimum TCB in client and KMS policy after the grace period. Old-TCB reports remain *cryptographically* valid (the SNP VCEK is per-TCB), so only policy rejects them.
- **Key rotation:** rotate OHTTP/HPKE key configurations on a fixed schedule with key identifiers; generate TLS keys per boot; rotate weight-encryption keys with re-encryption; version KMS policies.
- **Incident triggers:** a vendor security bulletin, a new side-channel or physical-attack paper, a monitor seeing an unexpected log entry, a spike in attestation failures, or anomalous key-release events.
- **Response:** freeze rollouts; raise minimum TCB or revoke affected measurements; **assume every key released to an affected TCB or measurement is compromised** and rotate it; drain and re-provision nodes; publish a disclosure.
- **Forensics by design:** you deliberately have no prompt logs. Plan investigations around release manifests, the transparency log, KMS release audit records and attestation-failure telemetry — and say so in your incident plan.

---
