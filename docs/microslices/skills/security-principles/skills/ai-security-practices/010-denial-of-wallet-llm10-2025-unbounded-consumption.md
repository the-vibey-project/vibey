---
id: skill-denial-of-wallet-llm10-2025-unbounded-consumption-0370c770f1
purpose: denial of wallet llm10 2025 unbounded consumption
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-secrets-management-for-ai-services-7902448662"]
links: ["skill-critical-next-js-react-cves-2025-2026-64d6893eaf"]
---

## Denial of Wallet (LLM10:2025 Unbounded Consumption)

**Threat:** "excessive and uncontrolled inferences, leading to denial of service (DoS), economic losses, model theft, and service degradation." Bills can be business-ending.

### Controls
- Set explicit `max_tokens` on **every** call
- **Token-based limiting** (input+output tokens) AND **cost-based caps**, not just request counts
- Pre-count tokens with `tiktoken` before sending
- Per-user/per-API-key/per-endpoint limits
- Timeouts and throttling
- Provider dashboard hard/soft spend caps
  - OpenAI: billing limits → 429 on hard limit
  - Anthropic: monthly cap + alerts (essential — billing is post-usage)
- Continuous logging/monitoring; graceful degradation

### Python Rate Limiting
- **slowapi** (Starlette/FastAPI, v0.1.9): Redis/Memcached backends; custom `key_func` for per-user/per-key limits; token-bucket/sliding-window via `limits`
- **fastapi-limiter** (Redis async)
- Atomic Redis+Lua token buckets for distributed limiting

### Next.js Rate Limiting
- **@upstash/ratelimit** (connectionless HTTP, v2.0.8): `fixedWindow`/`slidingWindow`/`tokenBucket`; multi-region; ephemeral in-memory DDoS cache
- **Arcjet:** rate limiting + bot detection + shield, `aj.protect(req)`

---
