---
id: skill-rate-limiting-429-handling-e5f510eca5
purpose: rate limiting 429 handling
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-embeddings-cost-optimization-476dec2c3e"]
links: ["skill-azure-monitor-metrics-reference-690c72d795"]
---

## Rate Limiting & 429 Handling

| Error | Meaning | Response |
|---|---|---|
| 429 | TPM/RPM quota or PTU 100% utilized | Respect `Retry-After`; exponential backoff with jitter |
| 503 | Capacity/server issue | Backoff + failover to another deployment |

Azure returns `x-ratelimit-*` headers. The APIM circuit breaker handles this automatically at the gateway layer.

---
