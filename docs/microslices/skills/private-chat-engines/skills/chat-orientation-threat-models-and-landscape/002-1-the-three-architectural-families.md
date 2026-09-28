---
id: skill-1-the-three-architectural-families-fe4009a21b
purpose: 1 the three architectural families
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-orientation-threat-models-and-landscape/SKILL.md
requires: ["skill-0-how-to-use-this-dossier-5547acde83"]
links: ["skill-2-threat-model-taxonomy-the-questions-that-decide-everything-418ce14054"]
---

## 1. The three architectural families

Every private chat engine falls into one of three families. Almost every design decision —
cost, privacy, failure modes, what you as an operator or developer can do — follows from which
family it belongs to.

### Family A: Centralised end-to-end-encrypted
*Signal, WhatsApp, Wire, Threema, iMessage, Olvid*

One company runs the only servers it will talk to. Encryption keys live on devices; the server
mostly shuttles ciphertext. **The operator story is non-existent**: you cannot self-host these;
you can only be a user or an ecosystem developer. The privacy battle is fought on **metadata**
(who talked to whom, when) because content is already opaque to the server. The engineering
battle is fought on **key management at scale** (multi-device, recovery, backups) and
**trust minimisation** (enclaves, zero-knowledge credentials, sealed sender, key transparency).

### Family B: Centralised, server-encrypted cloud
*Telegram*

Everything is encrypted in transit and at rest on Telegram's servers, but **Telegram holds the
keys** — that's what makes multi-device sync, 200,000-member groups, searchable history and
channels possible. E2EE ("Secret Chats") exists only for 1:1 mobile chats and is off by default.
The operator story is about **operating communities and bots on someone else's infrastructure**,
and the trust story is: you trust Telegram with all default content everywhere.

### Family C: Federated / decentralised
*Matrix, XMPP, Session, SimpleX, Briar, Delta Chat, Nostr*

Many independently operated servers (or none at all) interoperate or relay. **The operator story
is the product here** — you can run the infrastructure, and in Matrix's case national governments
do. Costs shift to whoever runs servers; privacy adds a new edge case (federation exposes more
metadata to more parties, and every homeserver is its own legal and moderation jurisdiction).
The spectrum inside this family runs from "federated servers" (Matrix, XMPP) to "relays with no
user identifiers" (SimpleX) to "onion-routed swarms" (Session) to "no network at all" (Briar).

The trade that never goes away: **convenience requires someone to see more**. Sync, search,
discovery, notifications, group management, abuse reporting — each one is metadata or content
visibility that someone has to be trusted with, or an engineering trick that avoids it.

---
