---
id: skill-18-imessage-and-facetime-2c4813ad78
purpose: 18 imessage and facetime
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-sms-rcs-signal-protocol-and-messaging-apps/SKILL.md
requires: ["skill-17-the-messaging-landscape-ea19aee3ca"]
links: []
---

## §18. iMessage and FaceTime

**⚠️ End-to-end encrypted since launch**, ⚠️ **with device-specific keys and Apple
distributing the key directory — ⚠️ which is the trust assumption: Apple could in principle
add a device to your account, and Contact Key Verification exists to detect exactly that.**
**⚠️ PQ3** added post-quantum ratcheting, ⚠️ **making it one of the first large-scale
deployments** (see a cryptography reference).
**⚠️ The backup gotcha** (§23 → `comms-encryption-metadata-interoperability-and-policy`): ⚠️ **iCloud Backup historically included message keys, so
messages were recoverable by Apple — Advanced Data Protection changes this and is
opt-in.**
**⚠️ FaceTime** is E2EE peer-to-peer or via relays; ⚠️ **the blue/green bubble distinction is
a real security distinction and also a famously effective lock-in mechanism, which is a
large part of why RCS and §25 → `comms-encryption-metadata-interoperability-and-policy` exist.**

---

# PART IV — REAL-TIME AND COLLABORATION
