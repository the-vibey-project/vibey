---
id: skill-prompt-caching-the-cache-golden-rule-a106b67d1b
purpose: prompt caching the cache golden rule
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-ptu-spillover-ga-august-2025-4b13d2dd89"]
links: ["skill-context-window-engineering-d9607b02e3"]
---

## Prompt Caching — The Cache Golden Rule

**Stable content first, dynamic content last.**

Order:
1. System prompt (most stable)
2. Tool definitions
3. Static documents/corpus
4. Conversation history (older first)
5. Current user message (most dynamic, last)

**A single byte of drift before the cached boundary invalidates the entire prefix.** A documented production failure: team's system prompt opened with `f"Today is {datetime.now().date()}…"` which dropped cache hit rate to ~1%.

### Azure/OpenAI Caching
- Automatic; no opt-in required
- ~50% input discount (some 2026 sources cite up to 90% on newer families); no write penalty
- Minimum: ≥1,024 tokens with identical first 1,024-token prefix
- Cache hits accrue every 128 tokens after the initial 1,024
- Verify via `cached_tokens` in `prompt_tokens_details`
- In-memory caches: clear after 5–10 min of inactivity (max 1h)
- GPT-4.1 / GPT-5 family: extended retention up to 24h via `prompt_cache_retention: "24h"`
- Use `prompt_cache_key` to improve routing/hit rate
- Regional/model-version splits do NOT share caches

### Anthropic Caching
- Explicit `cache_control` breakpoints (≤4 per request)
- Cache read = 0.1× input cost (90% off)
- Cache write = 1.25× (5-min TTL) or 2× (1-hr TTL)
- Break-even: ~2–3 cache reads per write
- Expanded to a 5M-token cache
- Real-world result: one developer cut $8,000→$800/month on a RAG system

### Google Gemini Caching
- Explicit user-managed cache objects with multi-day TTLs

### Caveats
- Tool-definition churn invalidates the tool-list cache
- Compacting conversation history destroys its cached prefix

---
