---
id: skill-18-quick-reference-21cc860d43
purpose: 18 quick reference
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-reference/SKILL.md
requires: ["skill-17-resources-34b0c167a8"]
links: ["skill-19-sources-and-method-32ce3c3d80"]
---

## §18. Quick Reference

### 18.1 Architecture picker
| Need | Approach |
|---|---|
| Timeline for normal accounts | **Fan-out on write**, store IDs (§3 → `social-feed-graph-ranking-and-notifications`) |
| Timeline including celebrity follows | **Hybrid — merge pulled high-follower posts at read** (§3 → `social-feed-graph-ranking-and-notifications`) |
| Feed pagination | **Cursor, never offset** (§3 → `social-feed-graph-ranking-and-notifications`) |
| Follower lists at scale | Adjacency lists + heavy caching, not a graph DB (§4 → `social-feed-graph-ranking-and-notifications`) |
| Follower counts on huge accounts | Approximate and cached (§4 → `social-feed-graph-ranking-and-notifications`) |
| Ranking | Candidate generation → rank → re-rank → blend (§5 → `social-feed-graph-ranking-and-notifications`) |
| Notifications | Batch, dedupe, collapse, respect quiet hours (§6 → `social-feed-graph-ranking-and-notifications`) |
| Known-violating media | Hash matching before publication (§7 → `social-moderation-abuse-and-regulation`) |
| Coordinated inauthentic behaviour | ⚠️ **Graph and timing analysis, not content** (§8 → `social-moderation-abuse-and-regulation`) |
| Age assurance | ⚠️ **Token + audit ID. Never store the document** (§9.3 → `social-moderation-abuse-and-regulation`) |
| Uploads | Sniff bytes, cap dimensions, transcode, strip EXIF (§10 → `social-media-analytics-privacy-and-presence`) |
| Testing a social feature | Cluster/ego-network randomization (§11 → `social-media-analytics-privacy-and-presence`) |
| Reaching developers yourself | ⚠️ **Own the writing; syndicate second** (§13 → `social-media-analytics-privacy-and-presence`) |

### 18.2 Before you build on a platform API
- [ ] Modelled cost at **projected** volume, and located the cliff? (§1.2 → `social-platform-apis-and-open-protocols`)
- [ ] Read the current terms, including the use-case obligation? (§1.2 → `social-platform-apis-and-open-protocols`)
- [ ] Are the specific endpoints you need still on self-serve? (§1.2 → `social-platform-apis-and-open-protocols`)
- [ ] Abstraction layer, so a terms change is one adapter? (§1.3 → `social-platform-apis-and-open-protocols`)
- [ ] Fallback path and exit plan costed? (§1.3 → `social-platform-apis-and-open-protocols`)
- [ ] Is the platform load-bearing for your core value? ⚠️ **If yes, reconsider** (§1 → `social-platform-apis-and-open-protocols`)

### 18.3 Before you launch anything social
- [ ] Moderation pipeline, including human escalation and appeals (§7 → `social-moderation-abuse-and-regulation`, §9 → `social-moderation-abuse-and-regulation`)
- [ ] Reviewer welfare provisions if humans will see reports (§7 → `social-moderation-abuse-and-regulation`)
- [ ] Rate limits and signup friction (§8 → `social-moderation-abuse-and-regulation`)
- [ ] Age assurance appropriate to your jurisdictions — ⚠️ **not self-declaration** (§9 → `social-moderation-abuse-and-regulation`)
- [ ] Transparency-reporting data collection **from day one** (§9.3 → `social-moderation-abuse-and-regulation`)
- [ ] Statements of reasons on enforcement actions (§9.1 → `social-moderation-abuse-and-regulation`)
- [ ] Upload validation, EXIF stripping, hash matching (§10 → `social-media-analytics-privacy-and-presence`)
- [ ] Deletion that propagates everywhere (§12 → `social-media-analytics-privacy-and-presence`)
- [ ] Block/mute enforced on **every** read path (§4 → `social-feed-graph-ranking-and-notifications`)
- [ ] Counter-metrics alongside engagement metrics (§11 → `social-media-analytics-privacy-and-presence`)

---
