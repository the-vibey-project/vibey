---
id: skill-14-anti-patterns-c40c7780f9
purpose: 14 anti patterns
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-reference/SKILL.md
requires: []
links: ["skill-15-contested-questions-40bfb9b7ba"]
---

## §14. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Building a product whose core value depends on one platform's API | ⚠️ **Apollo. Nine days' notice. $20M/year** (§1.1 → `social-platform-apis-and-open-protocols`) |
| No abstraction layer over platform APIs | Terms change; you want to change one adapter (§1.3 → `social-platform-apis-and-open-protocols`) |
| Budgeting on current volume | ⚠️ **The X read cap is a $10k cliff, then Enterprise** (§1.2 → `social-platform-apis-and-open-protocols`) |
| Auto-posting links without checking the URL surcharge | ⚠️ **~13× a plain post on X** (§1.2 → `social-platform-apis-and-open-protocols`) |
| Designing follow/like features without checking write availability | ⚠️ **Removed from X self-serve, April 2026** (§1.2 → `social-platform-apis-and-open-protocols`) |
| Assuming the free tier persists | It hasn't, anywhere (§1.1 → `social-platform-apis-and-open-protocols`) |
| Scraping a platform that prohibits it in its terms | Contractual exposure (§1.2 → `social-platform-apis-and-open-protocols`) |
| Treating ActivityPub and ATProto as interchangeable | ⚠️ **They don't natively interoperate and won't soon** (§2.3 → `social-platform-apis-and-open-protocols`) |
| Assuming a bridge is transparent | Edits don't propagate; replies get lost (§2.3 → `social-platform-apis-and-open-protocols`) |
| Quoting Bluesky's registered users as active users | Registered ≠ MAU (§2.2 → `social-platform-apis-and-open-protocols`) |
| Pure fan-out on write | ⚠️ **A 50M-follower account is 50M writes** (§3 → `social-feed-graph-ranking-and-notifications`) |
| Pure fan-out on read | Latency scales with following count (§3 → `social-feed-graph-ranking-and-notifications`) |
| Storing hydrated content in timelines | Deletions and edits become unfixable (§3 → `social-feed-graph-ranking-and-notifications`) |
| Offset pagination on a live feed | Duplicates and gaps (§3 → `social-feed-graph-ranking-and-notifications`) |
| Applying blocks only at write time | Later blocks don't clean history (§3 → `social-feed-graph-ranking-and-notifications`) |
| Exact follower counts at celebrity scale | Cache approximately; accept eventual consistency (§4 → `social-feed-graph-ranking-and-notifications`) |
| A general graph database for "get followers of X" | Usually the wrong tool (§4 → `social-feed-graph-ranking-and-notifications`) |
| Visibility checks on some read paths | ⚠️ **One missed path is a data leak** (§4 → `social-feed-graph-ranking-and-notifications`) |
| Optimizing purely for engagement | ⚠️ **Reliably degrades the product; outrage wins** (§5 → `social-feed-graph-ranking-and-notifications`, §11 → `social-media-analytics-privacy-and-presence`) |
| Notification strategy tuned for reach | Fatigue → permission revocation → unrecoverable (§6 → `social-feed-graph-ranking-and-notifications`) |
| "We're too small to need moderation" | ⚠️ **False the moment you're worth abusing** (§7 → `social-moderation-abuse-and-regulation`) |
| Automated moderation with no human escalation | Context is what classifiers lack (§7 → `social-moderation-abuse-and-regulation`) |
| Moderation tooling with no reviewer welfare provision | ⚠️ **Documented psychological harm; a duty of care** (§7 → `social-moderation-abuse-and-regulation`) |
| English-only classifiers on a global product | Where the worst real-world harms have happened (§7 → `social-moderation-abuse-and-regulation`) |
| Content-based spam detection only | ⚠️ **Behaviour and graph structure are harder to fake** (§8 → `social-moderation-abuse-and-regulation`) |
| Detection heuristics based on "looks human-written" | Generated content is cheap now (§8 → `social-moderation-abuse-and-regulation`) |
| **Age gate by self-declaration** | ⚠️ **Reddit fined £14.5M; explicitly deemed insufficient** (§9.2 → `social-moderation-abuse-and-regulation`) |
| Assuming non-EU headquarters exempts you from the DSA | ⚠️ **"Substantial connection" is the test** (§9.1 → `social-moderation-abuse-and-regulation`) |
| Storing ID documents to prove age | ⚠️ **You created a worse liability. Take a token** (§9.3 → `social-moderation-abuse-and-regulation`) |
| No appeals mechanism | Legally required in the EU (§9.1 → `social-moderation-abuse-and-regulation`) |
| Retrofitting transparency reporting | ⚠️ **You can't reconstruct data you didn't collect** (§9.3 → `social-moderation-abuse-and-regulation`) |
| Trusting client-supplied content type on upload | Sniff the bytes (§10 → `social-media-analytics-privacy-and-presence`) |
| Serving user-supplied SVG from your origin | ⚠️ **Script execution** (§10 → `social-media-analytics-privacy-and-presence`) |
| Decoding uploads before capping dimensions | Decompression bombs (§10 → `social-media-analytics-privacy-and-presence`) |
| Not stripping EXIF | ⚠️ **GPS coordinates. A recurring real incident** (§10 → `social-media-analytics-privacy-and-presence`) |
| "Deleting" content only from the primary store | Timelines, caches, CDN, search, backups, warehouse (§12 → `social-media-analytics-privacy-and-presence`) |
| A/B testing a social feature without cluster randomization | ⚠️ **Network effects break independence** (§11 → `social-media-analytics-privacy-and-presence`) |
| Treating the social graph as non-sensitive | ⚠️ **It reveals what users never disclosed** (§12 → `social-media-analytics-privacy-and-presence`) |
| Building a personal brand as a career strategy | ⚠️ **Serendipity is the real mechanism, and it's slow** (§13 → `social-media-analytics-privacy-and-presence`) |
| Advice that ignores who pays the harassment cost | It isn't evenly distributed (§13 → `social-media-analytics-privacy-and-presence`) |

---
