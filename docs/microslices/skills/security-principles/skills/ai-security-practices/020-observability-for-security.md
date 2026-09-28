---
id: skill-observability-for-security-90d8f12867
purpose: observability for security
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-container-and-kubernetes-security-c9f74b3f20"]
links: ["skill-staged-implementation-roadmap-19c96234f0"]
---

## Observability for Security

- Structured logging to a SIEM
- Log security events (authn failures, authz denials) at a distinct level
- Anomaly detection on LLM usage/cost (unusual spend = potential credential compromise or DoS)
- For LLMs: trace each guardrail step (e.g., Langfuse `@observe`) and monitor risk scores
- OpenTelemetry tracing
- Data privacy: Presidio-based PII detection/redaction; data minimization; never log request bodies/tokens

---
