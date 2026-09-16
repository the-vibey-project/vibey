# Private Chat Engines Plugin

A research dossier on private messaging: the architectural families every messenger falls into,
then Signal, Telegram and Matrix taken one at a time, then everyone else worth knowing, then the
two perspectives that matter in practice — what you would write in the design doc of a
private-chat product, and what you would tape inside the rack of a private-chat deployment.

One dossier, split into 6 skills so a task loads only the part it needs.

**The framing that organizes the whole set** — every private chat engine belongs to one of three
families, and almost every design decision follows from which:

- **Centralised end-to-end-encrypted** (Signal, WhatsApp, Wire, Threema, iMessage, Olvid). One
  company runs the only servers it will talk to. **There is no operator story** — you can be a
  user or an ecosystem developer, nothing else. The privacy fight is over metadata, because
  content is already opaque to the server.
- **Centralised, server-encrypted cloud** (Telegram). Encrypted in transit and at rest, but the
  operator holds the keys — which is exactly what makes sync, huge groups, searchable history and
  channels possible. The operator story is running communities and bots on someone else's
  infrastructure.
- **Federated / decentralised** (Matrix, XMPP, Session, SimpleX, Briar, Delta Chat, Nostr).
  **Running the infrastructure is the product.** Costs shift to whoever runs servers, and
  federation exposes more metadata to more parties — every homeserver its own legal and
  moderation jurisdiction.

The trade that never goes away: **convenience requires someone to see more.** Sync, search,
discovery, notifications, group management, abuse reporting — each is metadata or content
visibility somebody has to be trusted with, or an engineering trick that avoids it.

Reference, not tutorial. The dossier separates three kinds of claim and says which is which:
**stable fundamentals** (protocol mechanics — how a double ratchet works does not go stale),
**dated specifics** (verified against live sources in September 2026, with links and dates
inline), and **reported-but-thin items**, flagged as such and never dressed up as verified.
Section numbers are **per skill**, not shared: each file is a self-contained dossier entry.

## Skills

- **chat-orientation-threat-models-and-landscape** (§0–§5) — ⚠️ The three architectural families
  and what follows from each; the threat-model taxonomy that decides everything else; the
  September 2026 comparison matrix; the timeline; the five forces reshaping private chat.
  **Read this first.**
- **chat-signal** (§1–§6) — The protocol stack everyone else's cryptography is named after;
  ⚠️ trust minimisation as the actual product — sealed sender, enclave contact discovery, key
  transparency, post-quantum ratcheting; the organisation and what it costs; the legal posture;
  ⚠️ what to do when there is no server to run; honest weaknesses.
- **chat-telegram** (§1–§7) — MTProto and the cloud-chat architecture; ⚠️ why default chats are
  not end-to-end encrypted and what that buys; the Durov prosecution and the compliance turn;
  scale and economics; operating communities; ⚠️ the richest developer ecosystem, with a leash.
- **chat-matrix-and-element** (§1–§6) — The federated protocol, Olm and Megolm; Matrix 2.0;
  ⚠️ the organisations, the money, and who is maintaining what; the homeserver operator handbook —
  the perspective no other entry can offer; the developer surface.
- **chat-the-wider-field** (§1–§13) — ⚠️ MLS (RFC 9420) and Wire; WhatsApp; iMessage PQ3;
  Threema; Olvid; ⚠️ SimpleX, Session and Briar and what each trades away; Nostr; XMPP with
  OMEMO; Delta Chat; the dead and the dormant; ⚠️ the policy annex.
- **chat-builder-and-operator-playbooks** (§1–§12) — ⚠️ Choose the protocol shape before touching
  crypto; the cryptography stack as checklists; ⚠️ the metadata budget every service must fill
  in; abuse and trust-and-safety under E2EE; the unglamorous 80%; maintained libraries; ops and
  incident checklists; budget intuition; the Signalgate lesson generalised.

## Related plugins

- `communication-technologies` covers messaging as one slice of a broader communications
  reference — email and SMTP, telephony and SS7, SMS/RCS, WebRTC, push — alongside the Signal
  protocol and the messaging landscape. Reach for it when the question spans communication as a
  whole.
- `cryptography-and-encryption` covers the primitives and constructions underneath: symmetric
  and AEAD, public key and signatures, key management, implementation failures.
- `tor-and-onion-networks` is the sibling reference for anonymity networks, where the property
  being protected is who is talking rather than what is said.

Reach for this plugin when the question is about a specific messenger, or about designing or
operating one.
