---
id: skill-7-moderation-at-scale-cec37c1536
purpose: 7 moderation at scale
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-moderation-abuse-and-regulation/SKILL.md
requires: []
links: ["skill-8-spam-bots-and-abuse-a36b61dcc5"]
---

## §7. Moderation at Scale

**[DURABLE] The hardest problem in this document, and the one engineering can only
partially address.**

**The layered pipeline everyone converges on:**
```
1. PREVENTION      rate limits, friction, account age gates, verification
2. AUTOMATED       hash matching (PhotoDNA/CSAM, known-violating media),
                   classifiers, heuristics
3. USER REPORTING  with abuse-of-reporting handling and prioritization
4. HUMAN REVIEW    queues, tooling, escalation
5. APPEALS         ⚠️ now legally required in the EU (§9)
6. TRANSPARENCY    reporting, also legally required
```

**⚠️ The realities that break naive designs:**
- **Scale**: at any real volume, human review of everything is impossible and automation
  alone is inadequate. **You will build a triage system, so design it deliberately.**
- **Context**: the same words are abuse or reclamation depending on speaker, audience, and
  history. ⚠️ **Classifiers do not have that context.**
- **Adversaries adapt** — every filter is a spec for evading it (§8).
- **⚠️ Reviewer welfare is a real duty of care.** Exposure to violent and abusive content
  causes documented psychological harm; **rotation, counselling, blurring by default and
  volume limits are not optional if you employ or contract reviewers.**
- **Cultural and linguistic coverage** — ⚠️ **most systems are dramatically weaker outside
  English, and this is where the most serious real-world harms have occurred.**
- **False positives have real costs** to real people, and appeals must actually work.

**[DURABLE] The structural point**: **CSAM detection has legal mandatory-reporting
obligations** (NCMEC in the US) and hash-matching participation is effectively expected;
**terrorism and violent extremism have their own regimes**; and ⚠️ **"we're too small to
need moderation" stops being true the moment you're large enough to be worth abusing —
which is much sooner than most teams plan for.**

---
