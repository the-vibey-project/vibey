---
id: skill-1-mls-rfc-9420-and-wire-the-standards-track-finally-ships-e64265a4dd
purpose: 1 mls rfc 9420 and wire the standards track finally ships
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-the-wider-field/SKILL.md
requires: []
links: ["skill-2-whatsapp-the-default-e2ee-of-the-planet-now-partially-pried-open-3a3336804e"]
---

## 1. MLS (RFC 9420) and Wire — the standards track finally ships

**Messaging Layer Security** is the IETF-standardised group-E2EE protocol (RFC 9420, March 2023),
co-initiated by *Wire* with Mozilla, Cisco, Google, Cloudflare, Meta and academia. Its engine is
**TreeKEM**: members sit in a ratchet tree, and a membership change costs **O(log n)** work
instead of the sender-keys/Double-Ratchet's roughly linear cost — which is why Signal-style
groups cap around the low thousands while MLS targets tens of thousands, and why MLS is the
protocol everyone now wants to *converge on*:

- **Wire** — the enterprise messenger (Berlin) — declared **MLS GA across its whole product on
  24 April 2025** ([announcement](https://wire.com/en/blog/wire-mls-is-now-generally-available)),
  replacing its own Proteus protocol; production-tested at 2,000-member channels with 8 devices
  each, calls to 150, and positioning for scale to "hundreds of thousands"
  ([Wire MLS explainer, Dec 2025](https://wire.com/en/blog/messaging-layer-security-mls-explained) ·
  [support pages](https://support.wire.com/hc/en-us/articles/12434725011485-Messaging-Layer-Security-MLS)).
  Wire claims 1,800+ customers and is explicitly chasing German **BSI VS-NfD classified-use
  approval** and EU sovereignty buyers — and frames MLS cipher-suite agility as its post-quantum
  plan ([architecture post, May 2026](https://wire.com/en/blog/secure-communication-architecture-e2ee-mls-identity)).
  ⚠️ "PQ-ready via agility" ≠ "PQ deployed": no shipped PQ ciphersuite is verified in this dossier.
- **Matrix** named MLS a **Matrix 3.0 candidate** (see `chat-matrix-and-element`).
- **Nostr** gained MLS group messaging via the Marmot protocol/NIP-EE (see §8).
- **RCS** — the GSMA's Universal Profile adopted **MLS** as the basis for cross-platform E2EE
  between Android and iOS, which would make RCS by far the largest MLS deployment in existence if
  and when it reaches carrier scale. ⚠️ Treat the *standard* as adopted and the *rollout* as
  unverified in this dossier: check the GSMA, Apple and Google shipping statements before quoting
  a date, a version, or a coverage figure. It is also the single biggest reason MLS — not the
  Signal Protocol — is the convergence target for new group-messaging work.
- **IETF MIMI** (More Instant Messaging Interoperability) is building cross-provider interop *on*
  MLS: hub/follower server model over mutually-authenticated HTTPS, consent flows, message
  franking for abuse reports, minimal-metadata rooms with pseudonymous credentials, hub-proxied /
  Oblivious-HTTP asset download. **Status: Internet-Drafts, not RFCs** —
  [draft-ietf-mimi-protocol-06 (updated Apr 2026)](https://datatracker.ietf.org/doc/draft-ietf-mimi-protocol/),
  [arch -03 (Jul 2026)](https://www.ietf.org/archive/id/draft-ietf-mimi-arch-03.html),
  [content format -09 (Jul 2026)](https://datatracker.ietf.org/doc/draft-ietf-mimi-content/09/).
  Authors span Cisco, Matrix.org Foundation, Phoenix R&D. Milestones have slipped; knock/invite
  and identity-authentication remain open work.

---
