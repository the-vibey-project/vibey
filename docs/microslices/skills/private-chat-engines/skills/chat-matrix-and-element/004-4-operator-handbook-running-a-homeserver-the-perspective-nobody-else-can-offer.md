---
id: skill-4-operator-handbook-running-a-homeserver-the-perspective-nobody-else-can-offer-79e1cd26f8
purpose: 4 operator handbook running a homeserver the perspective nobody else can offer
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-matrix-and-element/SKILL.md
requires: ["skill-3-the-ecosystem-organisations-money-and-who-s-maintaining-what-verified-f8dec783ce"]
links: ["skill-5-developer-perspective-bdf0fc09a3"]
---

## 4. Operator handbook: running a homeserver (the perspective nobody else can offer)

### 4.1 Sizing honestly
- Personal/friends server (<50 users): a $6 VPS runs Continuwuity or even Synapse comfortably.
  Synapse RAM pressure comes from *joining big federated rooms*, not your user count — federation
  state, not messages, is the resource hog.
- Community (1–5k users): Synapse on 4–8 vCPU/16–32 GB with Postgres on SSD, media on object
  storage/CF cache; split out `media_repo` and `federation_sender` workers early.
- Institutional: ESS on Kubernetes, or Synapse with full worker separation (sync, client reader,
  federation reader/sender, event persisters, media, background, pusher, appservice) behind a
  smart reverse proxy; Postgres HA; TURN (coturn) + LiveKit for calls.

### 4.2 The ops chores that actually burn people
1. **Postgres tuning & state compression** — `state_groups_state` grows without bound; run the
   rust-synapse-compress-state tool routinely; mind autovacuum.
2. **Media discipline** — set retention (`media_retention: local_media_lifetime`,
   remote_media_lifetime) or watch disk forever; consider matrix-media-repo for dedup/CDN.
3. **Key custody** — your server signing keys *are* your identity in federation. Lose them and
   you rejoin every room. Back them up; rotate carefully (old keys must be kept published for
   history validation).
4. **`server_name` vs server** — use delegation (`.well-known`) so user IDs live on the apex
   domain (alice@example.org) while Synapse runs at matrix.example.org. You cannot cleanly change
   server_name later. This is the #1 forever-decision.
5. **Backups that restore** — Postgres dumps + media store + MAS DB + signing keys + TURN creds;
   *test* restores. E2EE rooms are client-side anyway (4S recovery keys per user — train users on
   recovery keys or accept UTD "can't decrypt" tickets).
6. **Federation hygiene** — room ACLs against abusive servers, `m.room.server_acl` events, and
   subscribing to community policy lists.

### 4.3 Moderation under (mostly) E2EE
On Matrix, E2EE means moderators can't read encrypted content they're not sent — but moderation
is *infrastructure + policy*, not content scanning:
- policy-list subscriptions (**Draupnir** is the successor to Mjolnir — moderation bot watching
  shared ban lists), server ACLs, joins-by-knocking/invite, power levels, slow mode, redactions,
  report forwarding to server admins, and deactivation flows. Public unencrypted rooms are fully
  visible to their homes' admins; homeserver operators bear legal duties for what they host —
  EU-facing communities have DSA obligations worth a compliance read.
- Trust & Safety is real labour: the Foundation's report counts moderation at ~30% on top of the
  matrix.org homeserver's infra cost (~20% of total spend) — one reason Premium exists.

### 4.4 Legal exposure checklist (operator)
you become a CDN *and* a postmaster: retention law in your jurisdiction, lawful-request process
(write one before you need it), CSAM hash-matching duties for public unencrypted content,
copyright complaints, sanctions screening for hosted communities, and GDPR data maps (encrypted
events still carry metadata and IPs in logs — rotate those logs).

### 4.5 Cheat: don't self-host
Element's hosted offerings / ESS Community, etke.cc, un-hooked "matrix for hire" providers —
fine for communities that want sovereignty-lite without the on-call.

### 4.6 The honest privacy critique
Federation sprays *metadata* widely: every server in a room learns membership, timing and the
social graph of everyone in it; E2EE protects content only. Retention defaults are
"keep forever". For dissident-grade threat models, Matrix federation metadata is a real exposure —
SimpleX/Session/Briar exist for a reason (→ `chat-the-wider-field`).

---
