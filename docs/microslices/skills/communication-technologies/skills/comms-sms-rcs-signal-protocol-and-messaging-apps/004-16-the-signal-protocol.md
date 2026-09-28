---
id: skill-16-the-signal-protocol-55e2dcd3cc
purpose: 16 the signal protocol
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-sms-rcs-signal-protocol-and-messaging-apps/SKILL.md
requires: ["skill-15-rcs-7140ef0b94"]
links: ["skill-17-the-messaging-landscape-ea19aee3ca"]
---

## §16. ⚠️ The Signal Protocol

> **⚠️ The most consequential piece of applied cryptography in consumer software, and it is
> worth understanding because it underpins WhatsApp and others too.**
```
⚠️ ⚠️ X3DH (extended triple Diffie-Hellman)  ⚠️ ASYNCHRONOUS key
   agreement — ⚠️ you can establish a shared secret with someone
   who is OFFLINE, using prekeys they published in advance.
   ⚠️ This is the thing that made E2EE work for mobile messaging
   at all
⚠️ ⚠️ THE DOUBLE RATCHET  ⚠️ two ratchets combined
   ⚠️ A DH ratchet: new key material each time the conversation
      changes direction
   ⚠️ A symmetric ratchet: a new key for every single message
   ⚠️ ⚠️ FORWARD SECRECY  ⚠️ compromising today's key does not
      decrypt yesterday's messages
   ⚠️ ⚠️ POST-COMPROMISE SECURITY (self-healing) ⚠️ — the
      genuinely remarkable property: if an attacker steals your
      keys, the conversation RECOVERS security once a message
      is exchanged in each direction. ⚠️ Very few systems offer
      this
⚠️ SEALED SENDER hides the sender from the server — ⚠️ a real
   metadata reduction (§24), though not a complete one
⚠️ PQXDH  ⚠️ post-quantum key agreement added to X3DH — Signal
   shipped this ahead of most of the industry (see a
   cryptography reference §26)
⚠️ ⚠️ MLS (Messaging Layer Security, RFC 9420)  ⚠️ THE OTHER
   IMPORTANT PROTOCOL. ⚠️ Designed for EFFICIENT LARGE GROUPS —
   Signal's pairwise approach scales poorly past a few hundred —
   and for INTEROPERABILITY between different implementations.
   ⚠️ This is what RCS adopted (§28.1)
⚠️ ⚠️ THE HARD PART IS NOT THE CRYPTOGRAPHY, IT IS KEY
   VERIFICATION (§23). ⚠️ Safety numbers exist; almost nobody
   checks them
```

---
