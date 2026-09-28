---
id: skill-12-ai-ml-services-607931e3af
purpose: 12 ai ml services
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-storage-databases-analytics-and-observability/SKILL.md
requires: ["skill-11-analytics-e379175f99"]
links: ["skill-13-observability-3dad571535"]
---

## §12. AI/ML Services

```
Managed platform  SageMaker      Azure ML / Foundry   Vertex AI
Model API         ⚠️ Bedrock      ⚠️ Azure OpenAI      ⚠️ Vertex / Gemini API
Own accelerator   Trainium/Inferentia  —              ⚠️ TPUs
```
**⚠️ The multi-model API layer is where the competition now sits**: **Bedrock, Azure AI
Foundry and Vertex all offer several model families behind one interface with
enterprise-grade data handling.** ⚠️ **The practical differentiators are which models are
available, in which regions, with what data-residency and retention commitments — and
those change frequently enough that any specific claim here would be stale.** **Check the
current model availability matrix rather than trusting a comparison article.**
**⚠️ GPU and accelerator capacity is genuinely constrained** (§21.2 → `hyperscaler-reference`) — **availability by
region, and the need for quota requests and sometimes capacity commitments, is now a real
architectural constraint rather than a formality.**

---
