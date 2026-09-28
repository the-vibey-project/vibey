---
id: skill-emerging-patterns-893d12ab17
purpose: emerging patterns
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-agentic-system-design-security-a3eeb4b322"]
links: ["skill-anti-patterns-to-avoid-c3f0a25a8b"]
---

## Emerging Patterns

### Voice RAG
Azure OpenAI Realtime API (GA Aug 2025): WebRTC/WebSocket/SIP, ~250–500ms end-to-end. Pattern: Realtime API → function call → AI Search retrieval → grounded spoken response.

### Streaming RAG
Event Hubs → Stream Analytics → AI Search push API; Cosmos DB change feed → embedding pipeline.

### Text-to-SQL
Beats RAG for exact aggregations/joins/filters. Pattern: schema injection → NL→SQL→execute→synthesize. Evaluate on Spider/BIRD benchmarks.

---
