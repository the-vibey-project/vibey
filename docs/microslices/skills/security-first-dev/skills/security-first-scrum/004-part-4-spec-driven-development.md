---
id: skill-part-4-spec-driven-development-7e7a48e97d
purpose: part 4 spec driven development
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-3-eight-inviolable-security-principles-saltzer-schroeder-zero-trust-dae7dda65c"]
links: ["skill-part-5-project-anatomy-c6ec05eefa"]
---

## PART 4: SPEC-DRIVEN DEVELOPMENT

Every feature begins with a written specification before any code. The spec is the source of truth.

### Spec Hierarchy (most authoritative first)

1. Formal contracts/schemas — OpenAPI/Swagger, JSON Schema, C# record types, TypeScript interfaces
2. Interface definitions — C# interfaces / abstract classes / ports
3. Acceptance tests — BDD / integration / contract tests
4. Unit tests — narrow behavior verification
5. Implementation — always last

### Security Must Be Explicit in Specs

Every spec must include a **Security Considerations** section covering:

- Authentication requirement (which flow, which scopes)
- Authorization requirement (which roles/policies, BOLA protection if applicable)
- Input validation rules (types, ranges, allowed values)
- Data classification (PII, credentials, sensitive business data?)
- Rate limiting requirement (if public-facing or abuse-prone)

If a spec has no Security Considerations section: write it and confirm it before proceeding.

### Agentic Workflow Per Feature

```
SPEC (with security section) → INTERFACE → TEST (red) → IMPL (green) → REFACTOR → SECURITY SCAN
```

---
