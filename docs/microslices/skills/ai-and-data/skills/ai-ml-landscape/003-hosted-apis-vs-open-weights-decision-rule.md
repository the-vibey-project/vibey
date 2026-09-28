---
id: skill-hosted-apis-vs-open-weights-decision-rule-1034e4ac4c
purpose: hosted apis vs open weights decision rule
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-frontier-model-landscape-mid-2026-e6270fd91a"]
links: ["skill-model-selection-strategy-staged-66b37a7e34"]
---

## Hosted APIs vs Open Weights — Decision Rule

| Factor | Hosted API | Open Weights |
|---|---|---|
| Peak capability, zero ops | ✓ | |
| Privacy, air-gap, data residency | | ✓ |
| Fine-tuning control | | ✓ |
| Predictable cost at sustained high QPS | | ✓ |
| Fastest to start | ✓ | |

**Open-weight options**: DeepSeek-V4 (MIT-licensed, 1M context, 1.6T/49B active MoE), Qwen3, Meta Llama 4, Mistral, IBM Granite 4.0.

**Threshold to self-host**: sustained high QPS where API spend exceeds fully-loaded GPU fleet cost, or a hard data-residency requirement.

---
