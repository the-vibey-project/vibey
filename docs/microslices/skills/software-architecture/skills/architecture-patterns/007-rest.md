---
id: skill-rest-101447aef9
purpose: rest
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-event-driven-architecture-eda-6a62bd0f75"]
links: ["skill-grpc-597c16112c"]
---

## REST
- Stateless, uniform interface, resource-based URLs
- **Richardson Maturity Model**: L0 (RPC-over-HTTP) → L3 (hypermedia)
- Verb idempotency: GET/PUT/DELETE idempotent; POST not
- Errors: **RFC 7807 Problem Details**
- Pagination: offset (simple, breaks under inserts) vs cursor/keyset (stable)
- **Azure:** APIM for full lifecycle; Functions HTTP triggers for lightweight endpoints; APIM imports OpenAPI directly
