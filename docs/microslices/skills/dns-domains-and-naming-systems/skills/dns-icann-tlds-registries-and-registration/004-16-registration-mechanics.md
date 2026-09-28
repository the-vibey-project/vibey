---
id: skill-16-registration-mechanics-087b2f7db9
purpose: 16 registration mechanics
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-icann-tlds-registries-and-registration/SKILL.md
requires: ["skill-15-the-registry-registrar-registrant-model-c33c4795d6"]
links: []
---

## §16. Registration Mechanics

**⚠️ EPP (Extensible Provisioning Protocol)** is how registrars talk to registries —
⚠️ **create, update, transfer, delete, and the authorization code that proves you may move a
domain.**
**⚠️ The lifecycle**: ⚠️ **available → registered → expired → AUTO-RENEW GRACE (~45 days,
recoverable at normal price) → REDEMPTION (~30 days, recoverable at a substantial fee) →
PENDING DELETE (5 days, nothing can be done) → dropped.**
⚠️ **Knowing this sequence is what lets you recover an accidentally lapsed domain — and
knowing the redemption fee is real is what motivates auto-renew.**
**⚠️ Transfers**: ⚠️ **unlock, get the auth code, initiate at the gaining registrar, approve;
⚠️ the 60-day lock after registration or a previous transfer is standard and catches
people mid-migration.**
**⚠️ Add Grace Period** and the historical abuse of it — ⚠️ **DOMAIN TASTING, registering in
bulk and refunding within five days, which was killed by making the refunds costly.**
**⚠️ ICANN fees, verification requirements** (⚠️ **failing to respond to a registrant
verification email suspends the domain, which surprises people**).
