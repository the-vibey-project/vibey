---
id: skill-azure-monitor-metrics-reference-690c72d795
purpose: azure monitor metrics reference
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-rate-limiting-429-handling-e5f510eca5"]
links: ["skill-cost-unit-economics-ae3f1aaa90"]
---

## Azure Monitor Metrics Reference

**Key metrics to track:**
- `ProcessedPromptTokens`, `GeneratedTokens`, `TokenTransaction` (Processed Inference = prompt+generated)
- `InputTokens`, `OutputTokens`, `TotalTokens`
- `ProvisionedUtilizationV2` (PTU utilization)
- `AzureOpenAIContextTokensCacheMatchRate` (`Prompt Token Cache Match Rate`)
- `FineTunedTrainingHours`
- Latency: Time to Response, Time to Last Byte, Time Between Tokens — **do NOT use the legacy Cognitive Services `Latency` metric**

**Dimensions**: split by `ModelDeploymentName` / `ModelName`.

**Export**: diagnostic settings → Log Analytics (KQL); build workbooks/Managed Grafana dashboards.

**`llm-emit-token-metric` policy** supports OpenAI, Anthropic Messages, and Google Vertex schemas.

---
