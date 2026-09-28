---
id: skill-the-three-core-levers-in-roi-order-1637123157
purpose: the three core levers in roi order
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: []
links: ["skill-token-economics-fundamentals-84afd10b30"]
---

## The Three Core Levers (in ROI order)

1. **Model routing** — route routine traffic to cheaper models, escalate only uncertain requests (60–80% cost reduction on routine queries per Microsoft guidance; validated RouteLLM benchmark: 95% GPT-4 quality at 26% GPT-4 calls, ~48% cheaper)
2. **Prompt caching** — restructure prompts for a stable prefix (Azure: ~50% off input; Anthropic: 90% off cache reads)
3. **Deployment pricing** — Batch API (50% off), PTU reservations (up to 70% off hourly), right-tier matching

**Governance is architecture, not monitoring.** Without per-request token logging and cost attribution, optimization is guesswork.

---
