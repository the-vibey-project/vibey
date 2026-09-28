---
id: skill-5-ranking-and-recommendation-b0c477387c
purpose: 5 ranking and recommendation
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-feed-graph-ranking-and-notifications/SKILL.md
requires: ["skill-4-the-social-graph-6ddbd4cf5b"]
links: ["skill-6-notifications-and-real-time-3d5c86bd57"]
---

## §5. Ranking and Recommendation

**[DURABLE] The structure is stable even as the models change.**

```
CANDIDATE GENERATION  → thousands of candidates from many sources (follows,
                        engagement-based, embedding-similarity, trending, ads)
     ↓
RANKING               → a model scores each; predicted engagement, dwell, quality
     ↓
RE-RANKING / POLICY   → diversity, freshness, source variety, safety filters,
                        author-frequency caps, business rules
     ↓
BLENDING              → merge organic, ads, recommendations
```

**⚠️ The problems that are genuinely hard and remain so**: **the feedback loop** — you
train on what you showed, so the model learns your past choices as much as user preference;
**engagement ≠ satisfaction**, and optimizing for the former reliably degrades the latter
(⚠️ **outrage, cliffhangers, and low-quality-but-clickable content all win on engagement
metrics**); **cold start** for new users and new content; **filter bubbles and diversity**,
which need explicit objectives because they never emerge from engagement optimization;
and **⚠️ explainability**, which is now partly a regulatory requirement (§9 → `social-moderation-abuse-and-regulation`).

**[DURABLE] The design lesson that matters most: what you measure becomes what you build.**
Choosing your objective function is a product-values decision wearing an engineering
costume, and **"we just show people what they engage with" is a choice, not a neutrality.**

---
