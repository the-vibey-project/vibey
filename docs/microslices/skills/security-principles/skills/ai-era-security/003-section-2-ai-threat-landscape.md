---
id: skill-section-2-ai-threat-landscape-aabc5d33bb
purpose: section 2 ai threat landscape
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-1-modern-framework-updates-what-changed-2024-2025-6e9007474a"]
links: ["skill-section-3-ai-security-frameworks-2024-2026-canon-d88b25468b"]
---

## SECTION 2 — AI Threat Landscape

### Adversarial ML Taxonomy (NIST AI 100-2)
- **Evasion attacks** — craft inputs to fool a deployed model
- **Poisoning attacks** — corrupt training data or model weights
- **Model inversion** — reconstruct training data from model outputs
- **Model extraction** — replicate proprietary model functionality through queries
- **Membership inference** — determine whether specific data was in the training set

### Prompt Injection (OWASP LLM01 — #1 for second consecutive edition)
**Root cause: LLMs process instructions and data in the same channel with no separation.**

Two forms:
- **Direct prompt injection** — user manipulates the prompt (e.g., DAN-style jailbreaks, system prompt override)
- **Indirect/XPIA (Cross-Prompt Injection Attack)** — malicious instructions hidden in documents, web pages, emails, or tool outputs that the model ingests

XPIA is especially dangerous because it requires no user interaction — the model fetches and executes attacker-controlled content autonomously.

### Training-Data Poisoning (OWASP LLM04)
- **Backdoored "sleeper agent" models** — behave normally until triggered by a specific input
- **Poisoned LoRA adapters** — the "PoisonGPT" technique: inject false factual claims via fine-tuning
- Treat Hugging Face downloads as untrusted supply chain — scan for unsafe deserialization (pickle) and backdoors; prefer **safetensors**

### RAG Poisoning / False RAG Entry Injection
- Poison vector databases used for retrieval-augmented generation
- False RAG entry injection: inject adversarial content that gets retrieved as "authoritative" context
- Added to MITRE ATLAS in Spring 2025

### Agent Hijacking and Tool Misuse
See Section 4 (OWASP Agentic Top 10) and Section 5 (real-world incidents).

---
