---
id: skill-azure-api-management-apim-8ef604f319
purpose: azure api management apim
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-data-lakes-lakehouses-0e973d9cf5"]
links: ["skill-load-balancing-decision-matrix-75537f2ba4"]
---

## Azure API Management (APIM)

**Tiers:** Consumption / Basic / Standard / Premium / Developer (plus v2 tiers)

**APIM AI Gateway capabilities:**
- `azure-openai-token-limit`: TPM enforcement
- `azure-openai-emit-token-metric`: usage to App Insights split by subscription/IP/custom dimension
- **Semantic caching**: `azure-openai-semantic-cache-store/lookup` using Azure Managed Redis + RediSearch + an embeddings model
- **Backend pools**: round-robin/weighted/priority load balancing and circuit breaker to spill **PTU → PAYG**
- Unified model API across providers

**Semantic caching gotcha:** Silently no-ops if the external Redis cache lacks RediSearch or isn't wired as an APIM external cache. Set similarity threshold carefully: too loose returns wrong cached answers.
