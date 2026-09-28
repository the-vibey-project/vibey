---
id: skill-output-sanitization-llm05-2025-improper-output-handling-dbb59d9f40
purpose: output sanitization llm05 2025 improper output handling
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-prompt-injection-llm01-2025-the-unfixable-risk-0bac2abfd2"]
links: ["skill-guardrail-architectures-ddc15ef222"]
---

## Output Sanitization (LLM05:2025 Improper Output Handling)

**Threat:** treating model output as trusted → XSS, SQLi, SSRF, or RCE when output flows into downstream interpreters.

**Pattern:** validate/encode output by context:
- Schema validation: Pydantic (Python) / Zod (TypeScript)
- Context-aware output encoding
- Parameterized queries (never string-concatenate LLM output into SQL)
- PII redaction: Presidio-based (built into NeMo Guardrails and Guardrails AI Hub)

---
