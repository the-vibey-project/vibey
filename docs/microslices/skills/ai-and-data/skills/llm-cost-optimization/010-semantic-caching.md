---
id: skill-semantic-caching-16745e0396
purpose: semantic caching
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-apim-ai-gateway-reference-architecture-691f919943"]
links: ["skill-advanced-prompt-engineering-b07ad86f03"]
---

## Semantic Caching

**APIM + Redis Enterprise pattern** for FAQ/support bots:
- Embed query → vector search cache → return if cosine similarity above threshold (~0.95)
- Add `rate-limit` after lookup to protect backend if cache is unavailable
- Tune `score-threshold` (lower = stricter match)

**Output cache** (simple TTL) cuts FAQ/deterministic traffic 30–80%.

**When NOT to use semantic caching**: personalized queries, real-time data, high-diversity query patterns.

---
