---
id: skill-owasp-llm-top-10-2025-edition-6ec23902cb
purpose: owasp llm top 10 2025 edition
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-the-three-core-truths-170fd88f9f"]
links: ["skill-prompt-injection-llm01-2025-the-unfixable-risk-0bac2abfd2"]
---

## OWASP LLM Top 10 (2025 Edition)

| Rank | Risk | Key Point |
|---|---|---|
| LLM01 | **Prompt Injection** | #1 for second consecutive edition; both direct and indirect; cannot be fully patched at input layer |
| LLM02 | Sensitive Information Disclosure | — |
| LLM03 | Supply Chain (model provenance) | Pickle-based RCE, malicious weights, poisoned training data |
| LLM04 | Data and Model Poisoning | — |
| LLM05 | **Improper Output Handling** | Treating model output as trusted → XSS, SQLi, SSRF, RCE |
| LLM06 | **Excessive Agency** | Over-permissioned tools, agentic misuse |
| LLM07 | System Prompt Leakage | — |
| LLM08 | **Vector and Embedding Weaknesses** | RAG security — new in 2025 edition |
| LLM09 | Misinformation (renamed Overreliance) | — |
| LLM10 | **Unbounded Consumption** | "Denial of Wallet" — new in 2025 edition |

---
