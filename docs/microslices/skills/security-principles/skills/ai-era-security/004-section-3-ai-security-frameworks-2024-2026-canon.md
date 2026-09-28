---
id: skill-section-3-ai-security-frameworks-2024-2026-canon-d88b25468b
purpose: section 3 ai security frameworks 2024 2026 canon
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-2-ai-threat-landscape-aabc5d33bb"]
links: ["skill-section-4-owasp-agentic-top-10-december-2025-f698dac083"]
---

## SECTION 3 — AI Security Frameworks (2024–2026 Canon)

### NIST AI RMF 1.0 (NIST AI 100-1, Jan 2023)
The de facto US AI governance vocabulary. Four functions:
1. **Govern** — culture, policies, accountability
2. **Map** — categorize AI risks in context
3. **Measure** — assess and analyze risk
4. **Manage** — prioritize, respond, monitor

### NIST AI 600-1 (Generative AI Profile, July 26, 2024)
A cross-sectoral profile issued per Executive Order 14110. Defines **12 GAI risk categories** including:
- Confabulation/hallucination
- Dangerous/CBRN information
- Data privacy
- Harmful bias
- Intellectual property
- **Prompt injection and data poisoning (§2.9)** — explicitly named as information security risks
- **Supply-chain/value-chain integrity (§2.12)**

### MITRE ATLAS v5.1.0 (November 2025)
The adversarial AI ATT&CK analog.

Current scope:
- **16 tactics, 84 techniques, 56 sub-techniques, 32 mitigations, 42 case studies**
- Spring 2025: added GenAI techniques — RAG Poisoning, False RAG Entry Injection, LLM Prompt Crafting, AI Supply Chain Compromise
- October 2025: Zenity Labs collaboration added 14 agent-focused techniques

**Usage rule: OWASP for risk prioritization; ATLAS for technique mapping and red-teaming.**

### OWASP LLM Top 10 (2025 Edition)
Two new entries vs. 2023/24 (marked *new*):

| # | Risk |
|---|------|
| LLM01 | Prompt Injection |
| LLM02 | Sensitive Information Disclosure |
| LLM03 | Supply Chain |
| LLM04 | Data & Model Poisoning |
| LLM05 | Improper Output Handling |
| LLM06 | Excessive Agency |
| LLM07 | System Prompt Leakage *(new)* |
| LLM08 | Vector & Embedding Weaknesses *(new)* |
| LLM09 | Misinformation |
| LLM10 | Unbounded Consumption |

**Critical:** LLM07 means the system prompt is NOT a security control (see production security guidance below).

### OWASP Top 10 for Agentic Applications (December 2025)
See full Section 4 below.

### ISO/IEC 42001:2023
The world's first certifiable **AI Management System (AIMS)** standard. Plan-Do-Check-Act structure.

- 38 controls across 9 objectives
- Microsoft, Google Cloud (Vertex/Gemini), and others are now certified
- **This is the AI-governance analog of ISO 27001**
- Pair with ISO 27001 — they are complementary, not duplicative

### EU AI Act (Regulation 2024/1689)
Phased implementation timeline:
- **Aug 1, 2024** — entered into force
- **Feb 2, 2025** — prohibited practices + AI literacy requirements
- **Aug 2, 2025** — GPAI (General Purpose AI) obligations
- **Aug 2, 2026** — high-risk (Annex III) obligations and enforcement (plan for this date; a "Digital Omnibus" proposal may defer some, but assume original)

Fines: up to **€35M or 7% of global annual turnover**, whichever is higher.

**Action: classify all AI systems against Annex III before Aug 2, 2026. Any high-risk use case requires a full AI risk management system.**

---
