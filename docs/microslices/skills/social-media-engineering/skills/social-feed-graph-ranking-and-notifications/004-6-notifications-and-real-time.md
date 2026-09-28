---
id: skill-6-notifications-and-real-time-3d5c86bd57
purpose: 6 notifications and real time
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-feed-graph-ranking-and-notifications/SKILL.md
requires: ["skill-5-ranking-and-recommendation-b0c477387c"]
links: []
---

## §6. Notifications and Real-Time

**Delivery**: WebSocket or SSE for in-app, **APNs/FCM** for push, email and SMS for
fallback. **⚠️ Push tokens expire and rotate — handle invalidation or you leak delivery
failures forever.**

**[DURABLE] The engineering that separates good from awful**: **batching and digest**
(⚠️ **notification fatigue causes permission revocation, and a revoked push permission is
very hard to win back**), **deduplication and collapsing** ("5 people liked your post", not
five notifications), **per-user preferences at real granularity**, **quiet hours and
timezone awareness**, **and read-state sync across devices.**

**⚠️ The ethics are load-bearing here.** Notifications are the most direct attention lever
you have, and **engagement-maximizing notification strategy is where product pressure most
often produces something the team wouldn't defend out loud.** Design the default you'd want
applied to you.

**Real-time presence** (typing indicators, online status) is expensive and
⚠️ **a privacy surface people underestimate** — "last seen" reveals more than users expect.
