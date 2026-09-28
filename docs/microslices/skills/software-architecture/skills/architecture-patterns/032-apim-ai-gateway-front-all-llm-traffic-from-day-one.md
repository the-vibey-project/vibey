---
id: skill-apim-ai-gateway-front-all-llm-traffic-from-day-one-fef2d50c99
purpose: apim ai gateway front all llm traffic from day one
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-rag-retrieval-augmented-generation-1f95ecf8dd"]
links: ["skill-ai-agent-architecture-1214916310"]
---

## APIM AI Gateway (Front All LLM Traffic from Day One)
- `azure-openai-token-limit`: TPM enforcement
- `azure-openai-emit-token-metric`: usage to App Insights
- **Semantic caching**: Azure Managed Redis + RediSearch + embeddings model
- **Backend pools**: PTU → PAYG spillover on circuit-breaker
