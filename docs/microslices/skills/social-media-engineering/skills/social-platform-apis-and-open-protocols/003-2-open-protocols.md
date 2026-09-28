---
id: skill-2-open-protocols-02e21e1f8c
purpose: 2 open protocols
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-platform-apis-and-open-protocols/SKILL.md
requires: ["skill-1-platform-apis-eb32247b43"]
links: []
---

## §2. Open Protocols

**[VERSIONED — the structural alternative, and the two camps have not merged.]**

### 2.1 ActivityPub

**W3C standard since 2018**, powering **Mastodon, Pixelfed, PeerTube, Lemmy** and — notably
— **Meta's Threads**. **The model is server-to-server federation**: every user is an
**actor** with an **inbox** and an **outbox**; servers deliver activities to each other.
**Identity is tied to your instance** (`@you@server.social`), which is both the model's
simplicity and its central weakness.

**Scale**: **Mastodon around 10.5 million accounts**, with the **wider Fediverse around
11 million** including Pixelfed and others. ⚠️ **Decentralization makes accurate counts
genuinely hard, and the 2022 surge has been followed by a steady decline in active users
and servers.**

### 2.2 AT Protocol

**Bluesky's protocol**, launched 2023, general registration February 2024.
**Over 40 million registered users**, with third-party estimates putting **monthly actives
in the low tens of millions** by early 2026 — ⚠️ **and registered-versus-active is the
distinction that matters here.**

**The architectural difference is the point**: ATProto separates **Personal Data Servers**
(your repository), **Relays** (firehose aggregation), **App Views** (indexing and
presentation), and **Labelers** (moderation as a separate, subscribable service).
**⚠️ Account portability is the design goal ActivityPub doesn't achieve**: moving your
entire identity, follows, and post history to a different server **without the old
server's cooperation**, via **DIDs** rather than server-scoped handles. **Custom feed
algorithms are a first-class, third-party-buildable primitive**, which is genuinely
unusual.

**⚠️ The honest critique**: **the protocol is decentralized; the main application is still
largely centralized**, and running a full relay is expensive enough that few do.
**Bluesky's centralized onboarding is also why adoption outpaced Mastodon's** — the
trade-off is real in both directions.

### 2.3 ⚠️ They don't interoperate

**As of 2026, ActivityPub and AT Protocol do not natively interoperate**, and this is not
an oversight — ⚠️ **the data models differ enough that a clean bridge is genuinely hard.**
ActivityPub co-author **Evan Prodromou** argued Bluesky should simply implement
ActivityPub; **Bluesky's position was that ActivityPub couldn't deliver the account
portability they wanted**, and native ActivityPub support **is not on the Bluesky
roadmap.**

**Bridges exist** — **Bridgy Fed** is the main one, now under the **A New Social**
nonprofit — ⚠️ **and the EFF's own guidance is candid about the seams: you can edit posts
on Mastodon but not Bluesky, so a bridged edit doesn't propagate; replies can get lost;
and account ownership gets strange** when you federate from a website rather than a
conventional account.

**[DURABLE] If you're building on either**: **the firehose is the interesting primitive**
(both give you one), **moderation is your problem** (§7 → `social-moderation-abuse-and-regulation`) and neither protocol solves it for
you, **and instance-level blocking is a social mechanism with technical consequences** you
need to model.
