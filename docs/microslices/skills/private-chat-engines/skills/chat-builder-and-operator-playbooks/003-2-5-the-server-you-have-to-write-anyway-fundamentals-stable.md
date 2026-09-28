---
id: skill-2-5-the-server-you-have-to-write-anyway-fundamentals-stable-20c7089dc8
purpose: 2 5 the server you have to write anyway fundamentals stable
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-2-the-cryptography-stack-as-checklists-ae51596a6c"]
links: ["skill-3-the-metadata-budget-every-service-must-fill-this-table-5dc70bdbf5"]
---

## 2.5 The server you have to write anyway (fundamentals — stable)

Whatever the protocol shape, a centralised engine needs the same five pieces — and the privacy of
the product is decided by what each one is allowed to remember:

| Component | Job | What it may keep |
|---|---|---|
| **Account service** | registration, device authentication, account management | account identifier + public identity keys |
| **Pre-key directory** | the X3DH bootstrap: serve one bundle per request | signed pre-key + one-time pre-keys, **each one-time key deleted on use** |
| **Message queue** | hold ciphertext for offline recipients | undelivered messages only — **delete after authenticated client acknowledgement** |
| **Push service** | wake sleeping clients via APNs/FCM | device token; **never message content** |
| **WebSocket / long-poll** | real-time delivery to connected clients | deliver, then dequeue **only** on an authenticated acknowledgement naming the message — a completed write is not receipt |

> **⚠️ IF YOU KEEP MESSAGES AFTER DELIVERY YOU ARE NOT RUNNING A MESSAGE QUEUE, YOU ARE RUNNING A
> MESSAGE ARCHIVE.** Decide which one you are building, then write it into the metadata budget (§3).

**Delivery doctrine.** A socket write that returns is not a message that arrived. The client can
disconnect, crash, or be killed by the OS between your `write()` succeeding and the ciphertext
reaching durable storage on the device — and if you dequeued on the write, the message is now gone
from the server *and* gone from the recipient, permanently, with no error anywhere. Drop it only
when the client says it has it: an **authenticated** acknowledgement, on the authenticated session
that owns that queue, naming the server-assigned ID of the message it persisted. The same rule
governs long-poll — an HTTP 200 on the response proves less than a socket write, not more — so
long-poll delivery is acknowledged on the *next* request, not by the response completing. The price
is that delivery becomes **at-least-once**: a client that persists a message and then loses the
connection before acknowledging will be sent it again. That is the correct trade (a duplicate is a
UI problem, a loss is a broken product), and it is handled, not avoided — give every message a
stable server-assigned ID, have the client discard an ID it has already stored, and make the
acknowledgement itself idempotent so a replayed ack is a no-op rather than an error. Then bound each
queue by age and by depth, or a device that never comes back turns your queue into the archive the
warning above forbids.

**The queue is per device, not per recipient.** The checklist above requires per-device session
fan-out (the Sesame pattern), and delivery has to match it. Hold one queue entry per *device*, and
drop that entry only on an acknowledgement from *that* device. A single recipient-level entry
dequeued on the first acknowledgement to arrive is a message the recipient's phone confirms and
their laptop never receives — and it fails silently in the worst way, because from the server's
side the message was delivered and acknowledged, so nothing anywhere reports an error. So fan a
message out to every registered device of the recipient, track acknowledgement per device, and
retain each copy until that device acknowledges it or its own bound expires. What a device that
registers *later* is owed is a linked-device history policy — a decision you make deliberately in
the metadata budget (§3), not an accident of which device happened to acknowledge first.

**Storage doctrine.** The ideal database holds account registrations, public keys, pre-keys and
undelivered messages. It does **not** hold delivered messages, who-messaged-whom, social graphs or
connection logs. Where a feature forces you to keep some metadata — group membership is the usual
case — keep the minimum and delete it when it stops being needed. Postgres for the relational side,
Redis for the queue; session state belongs to the client, never the server.

☑ **Rate-limit pre-key fetches per account.** An attacker who drains a user's one-time pre-keys
degrades or blocks delivery to them: pre-key exhaustion is a denial-of-service surface, not only a
capacity parameter. §2's "last-resort" pre-key is the graceful half of the answer; the rate limit is
the other half.
