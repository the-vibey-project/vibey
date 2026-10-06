---
id: skill-7-oblivious-http-and-relays-separating-who-you-are-from-what-you-ask-db90ee5e2d
purpose: 7 oblivious http and relays separating who you are from what you ask
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-6-binding-attestation-to-the-channel-and-what-the-client-must-check-9930a43cf7"]
links: ["skill-8-transparency-logs-reproducible-builds-and-binary-transparency-dadaab3f53"]
---

## 7. Oblivious HTTP and relays: separating who-you-are from what-you-ask

**RFC 9458** (*Oblivious HTTP*, January 2024) splits a request across two parties that must not collude.

| OHTTP resource | Sees | Does not see |
|---|---|---|
| **Client** | Everything about its own request | — |
| **Oblivious Relay Resource** | Client IP address, timing, encapsulated size | Request or response content |
| **Oblivious Gateway Resource** | Decrypted request and response | Client IP (only the relay's) |
| **Target Resource** | The request as forwarded by the gateway | Client IP |

- **Encapsulation:** requests are **Binary HTTP** messages (RFC 9292) encrypted with **HPKE** (RFC 9180) to the gateway's public key; responses are encrypted under a key derived from that exchange, so only the requesting client can read the reply.
- **Key configuration:** a key identifier, KEM and KDF/AEAD pairs, served as `application/ohttp-keys`. Discovery via SVCB/HTTPS records is specified in RFC 9540 ⚠️ verify.
- **Key consistency is a privacy requirement.** A malicious gateway can give each client a *unique* key configuration and so tag users. Clients must obtain the same configuration as everyone else — fetched through the relay, pinned in the app, or published in a transparency log — ⚠️ verify the current state of IETF key-consistency drafts.
- **Authorization without identity:** an account token inside the encapsulated request re-links identity to content. Use **Privacy Pass** anonymous tokens (RFC 9576 architecture, RFC 9577 HTTP authentication scheme, RFC 9578 issuance protocols, June 2024) for rate limiting and entitlement.
- **Streaming:** RFC 9458 encapsulates whole messages. Token streaming needs an incremental variant — `draft-ietf-ohai-chunked-ohttp` ⚠️ verify status — and padding to blunt the token-length side channel in §2.
- **Post-quantum:** prompts captured today could be decrypted later if HPKE uses only X25519. Consider a hybrid post-quantum KEM once your HPKE library and the relevant drafts support one ⚠️ verify (see `ai-era-security` §7).

**Combining OHTTP with an attested gateway.** Put the gateway inside a TEE, generate its HPKE key inside the TEE, publish the key configuration *with evidence binding it* (§6), and have the client verify before encapsulating. The cloud then sees only ciphertext, the relay sees only the IP, and the gateway's plaintext view is constrained to attested, published code.

**Collusion assumptions to write down:** relay and gateway run by different organizations; the relay does not log beyond operational need; no shared telemetry. OHTTP is **not a mixnet** — a global passive observer, or a low-volume service with a tiny anonymity set, can still correlate timing and sizes.

---
