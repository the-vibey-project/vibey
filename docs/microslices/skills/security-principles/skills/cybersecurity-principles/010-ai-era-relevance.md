---
id: skill-ai-era-relevance-bb9f736e95
purpose: ai era relevance
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-building-the-mental-model-the-threat-landscape-b0d2fc1d3e"]
links: ["skill-the-three-structural-realities-of-all-security-work-872f6a0961"]
---

## AI-Era Relevance

**The single highest-leverage traditional principle for the AI era is Least Privilege applied to non-human identities.** Most agentic breaches are privilege-and-blast-radius failures, not novel ML attacks. Non-human identities (agents, service accounts, API tokens) already outnumber human identities 80:1 — and agentic AI is adding to that count rapidly.

**Saltzer-Schroeder mapped to AI-era problems**:

| Principle | Traditional application | AI-era application |
|-----------|------------------------|-------------------|
| Complete Mediation | Check authorization on every request | Validate every tool call against policy in a deterministic layer outside the LLM |
| Psychological Acceptability | Don't force developers to hard-code tokens to avoid MFA friction | Human-in-the-loop UX that isn't defeated by alert fatigue; don't require re-approval on every low-risk agent action |
| Least Privilege | Service accounts shouldn't have admin access | Each AI agent is a non-human identity with scoped, just-in-time credentials and a required human sponsor |
| Fail-Safe Defaults | Default-deny firewall rules | Treat system prompts as NOT a security control; enforce security deterministically outside the model |
| Complete Mediation | Re-check auth on every sensitive request | Allowlist tools and egress domains; require re-approval on tool definition changes |
| Economy of Mechanism | Don't roll your own crypto | Prefer small, focused agents over monolithic agents with broad access |

**Why traditional controls remain necessary but insufficient**: prompt injection (OWASP LLM01) exploits a fundamentally new problem — the data/instruction boundary collapses when an LLM processes both in the same channel. No amount of least-privilege configuration prevents a model from following malicious instructions embedded in a document it was told to summarize. This requires new controls (input validation, output filtering, guardrails) layered on top of traditional ones.
