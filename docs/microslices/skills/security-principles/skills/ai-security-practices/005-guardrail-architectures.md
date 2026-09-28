---
id: skill-guardrail-architectures-ddc15ef222
purpose: guardrail architectures
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-output-sanitization-llm05-2025-improper-output-handling-dbb59d9f40"]
links: ["skill-rag-security-llm08-2025-f3c5605bc9"]
---

## Guardrail Architectures

### Layer Model
```
input rail (jailbreak/PII) 
  → retrieval rail (RAG chunks) 
  → execution rail (tool-call gating) 
  → output rail (moderation/PII/format)
```
No single framework covers all ten OWASP items — layer them.

### NVIDIA NeMo Guardrails
- Open-source, Apache 2.0; v0.17.0 (Oct 2025); **NVIDIA labels it beta / "additional hardening required for production"**
- Five rail types: input, dialog, retrieval, execution, output
- Uses the Colang DSL; uniquely models multi-turn dialog
- Integrates: Llama Guard, Presidio PII detection, NemoGuard-8b content-safety/topic-control NIMs
- Supports streaming output checks
- Integrates with LangChain/LangGraph

### Other Options
| Tool | Model | Best For |
|---|---|---|
| **Guardrails AI** | RAIL spec + validator Hub, `num_reasks` for auto re-prompting | Python-centric apps |
| **LLM Guard** (Protect AI) | Input + output scanners | Composable pipeline |
| **Lakera Guard** | Managed API | Minimal integration effort |
| **Azure AI Content Safety** | Managed Azure | Azure-native teams |
| **AWS Bedrock Guardrails** | Managed AWS | AWS-native teams |

### Red-Teaming Tools
Garak, PyRIT, Promptfoo, DeepTeam

---
