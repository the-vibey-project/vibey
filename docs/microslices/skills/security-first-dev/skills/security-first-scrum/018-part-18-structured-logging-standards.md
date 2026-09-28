---
id: skill-part-18-structured-logging-standards-6f25a47833
purpose: part 18 structured logging standards
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-17-anti-patterns-never-do-these-3768dcb030"]
links: ["skill-part-19-error-handling-standards-c0af1ae3f8"]
---

## PART 18: STRUCTURED LOGGING STANDARDS

Use Microsoft.Extensions.Logging with Application Insights or OpenTelemetry sink.

### Required Log Events

| Event | Level | Layer |
|---|---|---|
| Request received | Information | Controller |
| Authentication failure | Warning + userId attempt | Controller |
| Authorization denial | Warning + userId + resource | Controller |
| Validation failure | Warning | Controller |
| Suspicious input detected | Warning + sanitized input | Controller |
| Business operation started | Information | Service |
| Resource ownership check failed | Warning + userId + resourceId | Service |
| External call (DB, API, queue) | Debug | Repository |
| External call failed (retry) | Warning | Repository |
| Business operation completed | Information | Service |
| Unhandled error | Error + exception | Any |

### Security Logging Rules — Strict

- NEVER log: passwords, JWTs, API keys, connection strings, credit card numbers, SSNs, PII
- NEVER log: Azure Service Bus / Event Hub message payloads
- ALWAYS log: authentication failures with the user identifier (not the password)
- ALWAYS log: authorization denials with userId + resourceId + required policy
- ALWAYS log: rate limit violations with the partition key
- Use structured message templates with named placeholders, never string interpolation

---
