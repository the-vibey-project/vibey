---
id: skill-8-spam-bots-and-abuse-a36b61dcc5
purpose: 8 spam bots and abuse
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-moderation-abuse-and-regulation/SKILL.md
requires: ["skill-7-moderation-at-scale-cec37c1536"]
links: ["skill-9-regulation-and-compliance-16c6366c59"]
---

## §8. Spam, Bots, and Abuse

**[DURABLE] Adversarial engineering — assume a motivated opponent who reads your
documentation.**

**The attack surface**: bulk account creation, **coordinated inauthentic behaviour**
(⚠️ **the hard one — individually plausible accounts acting in concert**), engagement
farming, scraping (see a web-scraping reference), impersonation, phishing in DMs, spam in
replies and mentions, **brigading and targeted harassment**, and vote or metric
manipulation.

**Defences, roughly in order of value**: **friction at signup** (email/phone verification,
⚠️ **and an awareness that this trades against accessibility and privacy**),
**rate limiting per account, per IP, per device, and per behaviour pattern**,
**behavioural signals over content signals** (⚠️ **timing, sequence, and network structure
are much harder to fake than text**), **graph analysis for coordination** — clusters
behaving identically are the signal — **device and browser fingerprinting** (privacy
trade-off, and increasingly regulated), **shadow-limiting rather than hard blocking**
(⚠️ **so the adversary doesn't learn immediately that they were caught — though this is
ethically contested when applied to real users**), and **reputation systems that decay.**

**⚠️ And the AI-era additions**: **generated content at volume is cheap now**, which breaks
detection heuristics built on "does this look human-written"; **and provenance signals
(C2PA and similar) are the direction of travel** but not yet dependable.

---
