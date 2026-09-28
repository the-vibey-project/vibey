---
id: skill-apim-ai-gateway-reference-architecture-691f919943
purpose: apim ai gateway reference architecture
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-model-routing-cascades-d39b8daf17"]
links: ["skill-semantic-caching-16745e0396"]
---

## APIM AI Gateway — Reference Architecture

**Deploy APIM as the AI gateway for every Azure OpenAI deployment.** This enables per-consumer token limits, per-team cost attribution, semantic caching, PTU→standard spillover routing, and content safety — all before the request reaches the model.

### Five AI-Gateway Policies
| Policy | Function |
|---|---|
| `llm-token-limit` | Per-key TPM/quota enforcement with prompt-token pre-calculation |
| `llm-emit-token-metric` | Per-consumer token metrics to App Insights (up to 5 custom dimensions) |
| `llm-semantic-cache-lookup` / `store` | Redis-backed vector semantic cache |
| `llm-content-safety` | Azure Content Safety integration |
| Backend pool + circuit breaker | Priority/weighted routing + circuit breakers per backend |

### Backend Pool Pattern
PTU backend (priority 1) → PAYG Standard (priority 2 / overflow). Circuit breaker per backend. `retry` policy honoring `Retry-After`.

### Reference Implementation
Azure-Samples/apim-genai-gateway-toolkit

### Cost Attribution
- Subscription keys map to cost attribution
- JWT enables per-user attribution
- Up to 5 custom dimensions on `llm-emit-token-metric`
- Note Azure Monitor's 10-dimension/50,000-time-series limits when designing custom dimensions

---
