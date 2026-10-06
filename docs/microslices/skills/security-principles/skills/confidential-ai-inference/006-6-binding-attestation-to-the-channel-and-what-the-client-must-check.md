---
id: skill-6-binding-attestation-to-the-channel-and-what-the-client-must-check-9930a43cf7
purpose: 6 binding attestation to the channel and what the client must check
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-5-remote-attestation-the-ietf-rats-model-rfc-9334-9d53a24197"]
links: ["skill-7-oblivious-http-and-relays-separating-who-you-are-from-what-you-ask-db90ee5e2d"]
---

## 6. Binding attestation to the channel — and what the client must check

An attestation report by itself proves that *some* genuine TEE produced it. It does not prove that the bytes you are about to encrypt will reach *that* TEE. An attacker can relay your challenge to a genuine TEE and serve you from elsewhere (a relay or diversion attack). The fix is to **bind a key generated inside the TEE to the evidence**: put `hash(public key ‖ nonce)` into `REPORT_DATA` (SNP), `REPORTDATA` (TDX), the realm challenge (CCA) or the `public_key`/`user_data` fields (Nitro).

Binding patterns:
- **RA-TLS / attested certificates:** the TEE generates its TLS key and embeds evidence in an X.509 extension; the client verifies evidence instead of (or as well as) WebPKI.
- **Post-handshake attestation over a TLS exporter:** evidence covers a value from the TLS 1.3 exporter (RFC 8446 §7.5, RFC 5705; channel binding type `tls-exporter`, RFC 9266), proving the evidence belongs to this session.
- **Attested HPKE keys:** the gateway publishes an HPKE public key together with evidence binding it; the client encrypts each request to that key. This is the natural fit for OHTTP (§7).
- **Standards work:** the IETF is working on attestation in TLS (for example `draft-fossati-tls-attestation` and the SEAT working group) ⚠️ verify current names and status.

**Terminate TLS or HPKE inside the TEE.** A load balancer or API gateway outside the TEE that terminates TLS defeats everything above it.

### The client checklist

1. **Signature chain** to a pinned vendor root (AMD ARK, Intel SGX Root CA, NVIDIA device CA, Arm CCA platform root), with revocation checked.
2. **TCB at or above your minimum** — not merely "valid". Reject `OutOfDate` TDX statuses and SNP reported TCBs below policy.
3. **Debug disabled** — SNP policy debug bit clear, TDX debug attribute clear, GPU not in a developer-tools mode, Nitro not in debug mode (its PCRs read as zeros in debug mode).
4. **Launch and runtime measurements match published reference values**, with event logs replayed and appraised.
5. **The release is in the transparency log** — inclusion proof against a checkpoint consistent with the last one you saw, cosigned by your required witnesses (§8).
6. **Freshness** — your nonce, or a result inside your validity window.
7. **Channel binding** — the key you encrypt to is the key in the evidence.
8. **GPU evidence verified and bound** to the CPU evidence; CC mode on.
9. **Model identity** — the weight digest (or the key-release policy that gates the weight key) is in the measured state.
10. **Host-controlled fields** (`HOST_DATA`, `MRCONFIGID`, `MROWNER`) treated as untrusted unless pinned.
11. **Fail closed.** No "continue anyway", no silent fallback to a non-confidential endpoint.

---
