---
id: skill-threat-modeling-reference-stride-applied-to-ai-agents-6b9d6c6fee
purpose: threat modeling reference stride applied to ai agents
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-8-10-point-agentic-security-design-checklist-9a315ee0f1"]
links: ["skill-rag-security-pattern-d327e92958"]
---

## Threat-Modeling Reference: STRIDE Applied to AI/Agents

| STRIDE | AI/Agentic Mapping |
|--------|-------------------|
| **S**poofing | Agent impersonation, identity abuse (ASI03) |
| **T**ampering | Prompt/RAG/memory poisoning (LLM04, ASI06), tool definition rug-pulls (ASI04) |
| **R**epudiation | Missing audit logs for agent actions and tool calls |
| **I**nformation disclosure | Sensitive info leakage (LLM02), system-prompt leakage (LLM07), data exfiltration via XPIA |
| **D**enial of service | Unbounded consumption / Denial of Wallet (LLM10), cascading failures (ASI08) |
| **E**levation of privilege | Excessive agency (LLM06), tool misuse (ASI02), privilege abuse (ASI03) |

Augment STRIDE with MITRE ATLAS technique mapping and CSA MAESTRO layered analysis for comprehensive agentic threat models.

---
