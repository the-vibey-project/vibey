---
id: skill-ai-coding-governance-in-agile-64833efdea
purpose: ai coding governance in agile
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-sprint-planning-checklist-with-security-gates-8a5ff01814"]
links: ["skill-dora-metrics-2024-benchmarks-816dddc4e1"]
---

## AI Coding Governance in Agile

The evidence (2024–2026) is sobering. The METR RCT (July 2025, 246 tasks) found AI tools made developers **19% slower** despite developers believing they were 20% faster. Apiiro found AI-assisted commits merged **4× faster** while introducing 322% more privilege escalation paths. Veracode found **45% of AI-generated code samples fail security tests**. Google DORA 2025 found a **9% increase in bug rates** correlated with 90% increase in AI adoption.

### Decision Framework: When to Use AI

| Use AI First | Use Human First | Human Only |
|---|---|---|
| Boilerplate/scaffolding (CRUD, DTOs) | Complex business logic | Authentication flows |
| Unit test generation | Domain-specific reasoning | Cryptography |
| Documentation | Familiar codebases | PII handling |
| Migration generation | Security-adjacent features | IaC for sensitive infra |

### Augmented DoD for AI-Assisted Code
- [ ] PR labeled `ai-assisted`
- [ ] At least one human reviewer confirms they *understand* the code (not just reviewed the diff)
- [ ] SAST and secrets scanning passed
- [ ] Parameterized queries verified (AI frequently generates string concatenation)
- [ ] License compliance checked (AI hallucinates package names — verify all AI-introduced dependencies exist)
- [ ] Test coverage maintained at parity with human-written code

### Team Norms
- **Approved tools** — enterprise-tier tools with audit logging only (no consumer AI tools with production code)
- **Prohibited** — pasting production secrets or PII into AI prompts; using AI output without human review
- **Track metrics** — AI-assisted vs. human-only defect rates per sprint; if security debt exceeds budget, reduce AI-assisted work next sprint

### Timeboxing AI Agent Sessions
- Time-box AI agent coding sessions to avoid runaway scope
- Review AI-generated changes as a complete unit before merging (not incrementally)
- Set a maximum PR size for AI-assisted work (e.g., 400 lines per review session)

---
