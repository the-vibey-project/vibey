---
id: skill-7-email-encryption-3fd1dda0aa
purpose: 7 email encryption
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-email-smtp-authentication-and-deliverability/SKILL.md
requires: ["skill-6-deliverability-9647d54f44"]
links: []
---

## §7. Email Encryption

**⚠️ Transport encryption (§2) protects the hop, not the message**, ⚠️ **and the provider
reads everything.**
**⚠️ PGP/GPG** — ⚠️ **decentralized web of trust, no forward secrecy, and famously unusable
for non-experts; ⚠️ the EFAIL research showed real vulnerabilities in how clients handled
it.**
**⚠️ S/MIME** — ⚠️ **certificate-authority based, better organizational tooling, and
therefore common in enterprise and government and rare elsewhere.**
> **⚠️ GOTCHA — neither encrypts the SUBJECT LINE or the metadata** (§24 → `comms-encryption-metadata-interoperability-and-policy`). ⚠️ **Who you
> emailed, when, and about what (per the subject) remains visible even with the body
> encrypted.**

**⚠️ Provider-based approaches** (Proton, Tutanota) ⚠️ **encrypt within their own systems and
fall back to links or plain mail outside — which is §1's trade in miniature.**
**⚠️ The honest assessment**: ⚠️ **email encryption has failed to achieve meaningful
adoption in thirty years, and if you need confidential messaging the practical answer is to
use something else** (§16 → `comms-sms-rcs-signal-protocol-and-messaging-apps`, §17 → `comms-sms-rcs-signal-protocol-and-messaging-apps`).

---

# PART II — TELEPHONY
