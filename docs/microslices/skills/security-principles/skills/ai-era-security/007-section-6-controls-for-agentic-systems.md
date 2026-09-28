---
id: skill-section-6-controls-for-agentic-systems-4eacbc54c6
purpose: section 6 controls for agentic systems
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-5-documented-real-world-agentic-incidents-2025-2026-aecc3404b8"]
links: ["skill-section-7-post-quantum-cryptography-pqc-401de13328"]
---

## SECTION 6 — Controls for Agentic Systems

### Agent Identity and Authorization
**Microsoft Entra Agent ID** (GA April 2026) is the current gold standard for enterprise agent identity:
- Issues agent identities as credential-less service principals
- OAuth for authorization, OIDC for authentication
- Scoped short-lived tokens (no standing broad permissions)
- Required human "sponsor" for every agent
- Conditional Access policies apply to agents
- Soft-delete cascade cleanup prevents orphaned agents

**Important caveat:** There is no single ratified cross-vendor OAuth-for-agents standard as of mid-2026. OWASP is working on Agentic Identity / an Agentic Naming Service. Flag agent identity as an emerging, fragmented area.

### Inter-Agent Trust
- Require message signing between agents
- Enforce mutual authentication across agent boundaries
- Establish explicit trust boundaries — don't implicitly trust upstream agents
- Both A2A and MCP protocols currently **lack enforced token expiration and central verification** — compensating controls are required

### Tool-Use Security
- **Allowlist tools and egress domains** (not blocklist — assume hostile)
- Validate and sanitize all URLs and parameters before execution
- Require re-approval on tool definition changes — defend against "rug pulls" where tool behavior changes after initial approval
- Validate tool outputs before feeding back into the agent (XPIA defense)

### Guardrails Architecture
Layer all available guardrail types — no single guardrail is sufficient:
- **Azure AI Content Safety** — Prompt Shields for direct + indirect injection, Groundedness detection, protected-material detection
- **AWS Bedrock Guardrails** — content filters, denied topics, PII redaction
- **NVIDIA NeMo Guardrails** — programmable rails via Colang across input/dialog/retrieval/execution/output
- **Guardrails AI** — Python validator library for output validation

Layer cloud-native input filters + specialized output/hallucination checks + library-level controls, ideally enforced at a gateway, not in the model.

### System Prompt Security
**The system prompt is NOT a security control.** OWASP LLM07 (System Prompt Leakage) makes this explicit. Enforce all security constraints deterministically outside the model in code.

### CSA MAESTRO Threat Modeling Framework
MAESTRO (Multi-Agent Environment, Security, Threat, Risk, and Outcome) is a seven-layer agentic threat modeling framework developed by Ken Huang/CSA (February 2025). Used by OWASP's Multi-Agentic System Threat Modeling Guide. Use it for structured threat modeling of agentic architectures, layered with MITRE ATLAS technique mapping.

### Secure Orchestration Frameworks
LangChain, LlamaIndex, and AutoGen all require explicit hardening:
- Explicit permission scoping for each agent
- Sandboxing for all tool execution
- Output validation before downstream consumption
- Audit logging of all agent decisions and tool calls

---
