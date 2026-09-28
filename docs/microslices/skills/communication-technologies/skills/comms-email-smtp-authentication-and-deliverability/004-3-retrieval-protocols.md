---
id: skill-3-retrieval-protocols-6a55ccaa33
purpose: 3 retrieval protocols
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-email-smtp-authentication-and-deliverability/SKILL.md
requires: ["skill-2-smtp-and-email-architecture-2dfbd07720"]
links: ["skill-4-message-format-978595998d"]
---

## §3. Retrieval Protocols

**⚠️ POP3** downloads and traditionally deletes — ⚠️ **a single-device model that predates
people having several.**
**⚠️ IMAP** keeps mail on the server with folders, flags and server-side search —
⚠️ **the model that matches how people actually use email, and it is complex enough that
implementations differ in maddening ways.**
**⚠️ JMAP** is the modern replacement: ⚠️ **JSON over HTTP, designed for mobile with
efficient synchronization and push, and it is genuinely better — with the usual federated
adoption problem** (§1).
**⚠️ Exchange/ActiveSync and Gmail's API** are the proprietary equivalents, ⚠️ **and the
calendar and contacts integration is a large part of why organizations stay on them.**
**⚠️ The practical consequence for users**: ⚠️ **IMAP means your mail lives on a server
someone else controls, which is the assumption §7 has to work around.**

---
