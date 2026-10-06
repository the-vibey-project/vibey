---
id: skill-15-common-failure-modes-6ca8b1bb28
purpose: 15 common failure modes
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-14-deployment-checklist-28e4ad55eb"]
links: ["skill-16-sources-e5e5ef47f3"]
---

## 15. Common failure modes

1. **Attesting to nobody** — the server produces evidence but no client checks it, or the client logs a failure and continues.
2. **Unbound evidence** — the report carries no key or nonce, so a relay attack goes undetected.
3. **TLS terminated outside the TEE** at a cloud load balancer or API gateway.
4. **Launch-only measurement** — firmware measured, but the root filesystem, container image or weights loaded afterwards are not chained.
5. **Accepting any valid TCB** — no minimum version, so a patched-but-not-enforced vulnerability stays exploitable.
6. **Debug or developer modes in production** on the CPU or GPU.
7. **CPU attested, GPU not** — or both attested but not bound to each other.
8. **Opaque PCR comparisons** without event-log replay, so nobody knows what was actually measured.
9. **Unpublished or irreproducible images** — attestation pins a binary nobody outside can inspect.
10. **Transparency without consistency checks or witnesses**, leaving split-view equivocation open.
11. **Prompts in logs, traces, crash dumps or error reports** emitted by the attested code itself.
12. **Identity leaked inside OHTTP** — account tokens or device identifiers in the encapsulated request — or relay and gateway run by the same organization.
13. **Per-client OHTTP key configurations** that let the gateway tag users.
14. **Cross-user prefix or KV caches** creating timing side channels.
15. **Unpadded token streaming** leaking response lengths.
16. **KMS policy editable by one administrator** with no log, silently widening key release.
17. **Treating a third-party verifier as neutral** without listing it in the trusted set.
18. **Over-claiming** — "even we cannot see your data" while abuse monitoring, telemetry or support tooling quietly exports content.

---
