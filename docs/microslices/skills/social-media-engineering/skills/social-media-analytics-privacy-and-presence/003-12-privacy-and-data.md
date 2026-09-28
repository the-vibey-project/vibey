---
id: skill-12-privacy-and-data-ed5850248d
purpose: 12 privacy and data
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-media-analytics-privacy-and-presence/SKILL.md
requires: ["skill-11-analytics-and-experimentation-a02ce4fbf8"]
links: ["skill-13-your-own-presence-as-a-developer-b6dbd8a998"]
---

## §12. Privacy and Data

**[DURABLE]** **Data minimization** (⚠️ **the data you didn't collect can't leak, be
subpoenaed, or be repriced by a regulator**), **purpose limitation**, **retention limits
with actual enforcement**, and **⚠️ deletion that genuinely propagates** — through
timelines that were fanned out (§3 → `social-feed-graph-ranking-and-notifications`), caches, CDNs, search indexes, backups, and analytics
warehouses. **Most "deleted" content in social systems is not deleted everywhere, and that
is both a legal and an ethical problem.**

**Rights infrastructure you'll need**: **data export** (GDPR portability), **deletion
requests**, **access requests**, and **⚠️ the "what about content others created that
mentions you" question**, which has no clean answer.

**And the specific social-media hazards**: **⚠️ inference risk** — the social graph reveals
things users never disclosed (a person's connections can reveal orientation, health status,
or political affiliation they never stated); **location leakage** via EXIF (§10),
check-ins, and timing; **and cross-platform correlation** by third parties.

---
