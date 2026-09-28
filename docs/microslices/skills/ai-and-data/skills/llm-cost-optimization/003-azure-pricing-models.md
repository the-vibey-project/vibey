---
id: skill-azure-pricing-models-ecbfa2d9cf
purpose: azure pricing models
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-token-economics-fundamentals-84afd10b30"]
links: ["skill-ptu-spillover-ga-august-2025-4b13d2dd89"]
---

## Azure Pricing Models

### Standard (PAYG)
- Per-token billing; quota in TPM/RPM
- **Global Standard**: routed worldwide, highest throughput, lowest rate
- **Data Zone Standard**: US/EU data residency
- **Regional Standard**: single region, highest per-token cost
- Prompt caching and Batch discounts apply automatically

### PTU (Provisioned Throughput Units)
- Reserved capacity; predictable latency
- Hourly: ~$1/PTU/hr (GPT-4o Global, Jan 2025)
- Monthly reservation: up to 64% off hourly
- 1-year reservation: up to 70% off (~$0.30/PTU/hr)
- Minimums: 15 PTU (Global/Data Zone, increments of 5), 50 PTU (Regional, increments of 50)
- PTU sizing depends on output:input ratios (gpt-5: 1 output = 8 input tokens; gpt-4.1: 1 output = 4 input)
- **Best practice**: deploy first, then buy the reservation — reservations guarantee discount, not capacity
- Cached tokens count 0% toward PTU utilization (100% off on Provisioned)

### Break-Even: PTU vs PAYG
- PTU generally wins above ~50% sustained utilization and ~150–200M tokens/month on GPT-4o
- This is a practitioner rule-of-thumb — not a single official Microsoft figure
- Bursty workloads may justify PTU earlier than the token volume suggests (for latency predictability)

### Batch API
- **50% off** Global Standard pricing
- Async, 24h SLA (often 1–6h in practice)
- Up to 50K requests / 200MB per input file
- **Ideal for**: evals, nightly summarization, classification queues, embedding refreshes

### Azure Credits Warning
- Microsoft for Startups credits (up to $150K) cover only "models sold directly by Azure" (Azure OpenAI)
- **Does NOT cover** third-party Marketplace models (Anthropic Claude, Meta Llama via Marketplace, etc.) — a documented billing trap that hit ≥20 startups with surprise invoices in early 2026
- Filter the catalog by "Direct from Azure" to stay covered
- Billing data lags 24–72h

---
