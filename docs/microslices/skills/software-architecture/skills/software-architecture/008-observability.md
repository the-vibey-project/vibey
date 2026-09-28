---
id: skill-observability-54fe73659e
purpose: observability
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-cqrs-and-event-sourcing-34cdbf3349"]
links: ["skill-zero-downtime-database-migrations-expand-contract-0fdb3b3664"]
---

## Observability

### OpenTelemetry (Standard)
- **Python/FastAPI**: `FastAPIInstrumentor.instrument_app(app)`; `azure-monitor-opentelemetry` distro gives one-line `configure_azure_monitor(connection_string=...)` export to Application Insights
- **Critical gotcha**: import the framework module (`import fastapi`) and call `configure_azure_monitor()` **before** instantiating `fastapi.FastAPI()`, or the Requests table won't populate
- Exclude health/readiness endpoints: `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS="health,ping"`
- Use **structlog** for structured logging in Python
- Propagate W3C trace context across Python ↔ Next.js ↔ Azure for end-to-end correlation
- Query Application Insights with KQL: `requests | summarize avg(duration) by name`
- Run only one exporter/processor per signal to avoid duplicate telemetry

### Security
- Zero-trust: verify every request, least privilege, managed identities, Private Endpoints
- Secrets in Key Vault — never in code
- WAF on Front Door/App Gateway; GraphQL query-complexity limits; parameterized queries via ORM; input validation with Pydantic/Zod at boundaries

---
