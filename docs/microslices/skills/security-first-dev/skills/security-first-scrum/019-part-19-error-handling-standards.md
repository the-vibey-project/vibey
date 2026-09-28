---
id: skill-part-19-error-handling-standards-c0af1ae3f8
purpose: part 19 error handling standards
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-18-structured-logging-standards-6f25a47833"]
links: ["skill-part-20-git-and-commit-standards-495c54cdb6"]
---

## PART 19: ERROR HANDLING STANDARDS

### Exception Hierarchy

```
AppException (base)
+-- ValidationException        <- malformed input, FluentValidation failure
+-- NotFoundException          <- resource does not exist
+-- AuthException              <- authentication / authorization failure (NEVER retry)
+-- ResourceOwnershipException <- BOLA (NEVER retry)
+-- ExternalServiceException   <- downstream failure
|   +-- TransientException     <- retriable subset (timeout, 429, 503)
+-- ConfigException            <- missing / invalid App Configuration or Key Vault
```

### Retry Policy

- Retry on: network timeouts, Cosmos DB 429, 503, Azure Service Bus transient errors
- DO NOT retry on: 400, 401, 403, 404, 409, AuthException, ResourceOwnershipException
- Exponential backoff with jitter: 1s, 2s, 4s, 8s, 16s. Max retries: 3-5.
- Use Polly (.NET) or tenacity (Python).

### Controller Error Mapping (RFC 7807 ProblemDetails)

```
ValidationException          -> 400
NotFoundException            -> 404
AuthException                -> 401 (generic message, no detail)
ResourceOwnershipException   -> 403 (generic message)
TransientException           -> 503 with Retry-After header
All others                   -> 500 with correlation ID, no internal details
```

---
