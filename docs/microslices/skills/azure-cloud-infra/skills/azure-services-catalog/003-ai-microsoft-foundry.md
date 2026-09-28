---
id: skill-ai-microsoft-foundry-145aa80e22
purpose: ai microsoft foundry
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: ["skill-storage-redundancy-decision-matrix-a79219fb84"]
links: ["skill-cost-optimization-35c90c4630"]
---

## AI & Microsoft Foundry

### Platform History and Current State
- Azure AI Studio → Azure AI Foundry (Ignite 2024) → **Microsoft Foundry** (Ignite 2025, now GA)
- 1,900+ models from OpenAI, Meta, and more (11,000+ including community models per Microsoft marketing)

### Two Project Models (Not at Full Feature Parity)
- **Hub-based projects:** built on Azure ML (`Microsoft.MachineLearningServices`); legacy path
- **Foundry projects:** built on Cognitive Services (`Microsoft.CognitiveServices/account`); **all new generative-AI investment goes here** — new model-centric features available only here
- An existing Azure OpenAI resource can be upgraded to a Foundry resource preserving endpoint and keys

### Agent Capabilities
- **Foundry Agent Service** (GA May 2025): connected agents for multi-agent orchestration without external orchestrators
- **Workflows** (visual + YAML, preview from Ignite 2025): coordinate multiple agents
- Agent types: managed no-code **Prompt agents** (GA) and **Hosted agents** (preview), both behind the Responses API
- Tools: Code Interpreter, Logic Apps (1,400+ connectors), Functions, OpenAPI, MCP, Deep Research, Agent2Agent (A2A)

### Microsoft Agent Framework
- Open-source successor to **both Semantic Kernel and AutoGen** (now in maintenance mode)
- Public preview October 1, 2025; **1.0 GA April 2026**
- Five stable orchestration patterns: sequential, concurrent, handoff, group chat, Magentic
- Native MCP and A2A support

### Deployment Options
| Option | When to Use |
|---|---|
| **Standard deployment** (preferred) | Foundry resource, no hub required, regional/data-zone/global processing |
| **Serverless API endpoints** (MaaS) | Pay-per-token, OpenAI/partner models, hub required |
| **Managed compute** | Hugging Face/NVIDIA NIM/custom models, billed per compute-hour |

### PTU vs Pay-as-You-Go
- **Pay-as-you-go (standard/token-based):** variable, experimental, or low-volume workloads
- **PTU (Provisioned Throughput Units):** production with predictable traffic needing guaranteed latency; billed hourly per PTU regardless of usage
- **Critical:** quota does not guarantee capacity — **deploy the model first, then buy the matching reservation**
- Spillover routes PTU overflow (429s) to a standard deployment

### When to Choose What
- **Microsoft Foundry:** end-to-end generative-AI/agent apps and the broad catalog — the default
- **Raw Azure OpenAI:** only when you need OpenAI models alone (upgrade path to Foundry recommended)
- **Azure Machine Learning:** custom model training, full MLOps, and the model registry

### Vector Search for RAG
- **Azure AI Search:** default for Azure-native teams — hybrid (BM25 + vector) search, built-in semantic ranker, security trimming, indexer-managed ingestion
- **pgvector:** cheaper for small corpora already on PostgreSQL
- **Cosmos DB vector search:** globally distributed apps already on Cosmos
- At ≤100k vectors, all options are fast enough — decision driver is features, cost model, and operational ownership

### APIM as AI Gateway
A major 2024–2026 pattern:
- `azure-openai-token-limit` policy for TPM throttling per subscription key
- Backend pool load balancing (round-robin/weighted/priority) and circuit breakers honoring `Retry-After`
- Route to PTU first, spill over to pay-as-you-go across regions on 429s
- `azure-openai-emit-token-metric` → Application Insights for per-team showback
- APIM is integrated into Microsoft Foundry; not a separate offering
- Azure-Samples/AI-Gateway repo provides 30+ deployable Bicep/policy labs

---
