---
id: skill-ptu-spillover-ga-august-2025-4b13d2dd89
purpose: ptu spillover ga august 2025
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-azure-pricing-models-ecbfa2d9cf"]
links: ["skill-prompt-caching-the-cache-golden-rule-a106b67d1b"]
---

## PTU Spillover (GA August 2025)

Routes PTU overage to a Standard deployment on non-200 responses (429 PTU-exhausted; 400 long-context >128K on gpt-4.1 PTU; 500/503).

**Enable via:**
- `spilloverDeploymentName` (all requests)
- `x-ms-spillover-deployment` header (per-request)

**Billing:** PTU requests = hourly only; spilled requests = standard token rates.

**Pattern**: size PTU for average load; spill peaks to PAYG. Monitor by splitting `Azure OpenAI Requests` metric by `ModelDeploymentName` + `StatusCode`.

---
