---
id: skill-part-8-error-handling-design-and-patterns-8d895d7b4d
purpose: part 8 error handling design and patterns
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-7-slo-based-burn-rate-alerting-040b76deff"]
links: ["skill-part-9-distributed-debugging-f5a7245715"]
---

## Part 8 — Error Handling: Design and Patterns

### Philosophy

The fundamental question is propagate vs. handle locally. "Let it crash" (Erlang/Elixir — supervised processes restart cleanly) suits systems with strong supervision and isolation; defensive handling suits monoliths without it.

Distinguish **recoverable vs. unrecoverable** and **fail-fast vs. fail-safe.**

**Most dangerous anti-pattern:** catching an exception and doing nothing (swallowing). Preserve the original cause and stack trace — the "poisoned exception" problem is re-throwing without chaining.

### Result Types vs. Exceptions

Functional approaches make errors part of the type signature:
- Rust: `Result<T,E>`
- Go: `(value, error)`
- Haskell: `Either`
- Scala: `Try`

Exception-based languages (Java, Python, C#) separate the happy path but risk invisible control flow. **Railway-oriented programming** (Scott Wlaschin) chains fallible operations via Result types.

Libraries bringing result types to exception languages: Vavr (Java), **neverthrow** (TypeScript), OneOf/FluentResults (.NET).

### Error Type Design

Taxonomy: system, application, user, transient (retryable), permanent (not retryable). Structured errors carry both a human message and machine-readable fields (code, status, context).

**RFC 9457 (Problem Details for HTTP APIs, July 2023, obsoletes RFC 7807):** The standard for machine-readable HTTP errors, using media type `application/problem+json` with members `type` (URI identifying the problem type), `title`, `status`, `detail`, and `instance`, plus custom extension members.

Critically: "Problem details are not a debugging tool for the underlying implementation" — don't leak internals in API responses.

### Resilience Patterns (from Michael Nygard, *Release It!*, 2007/2018)

#### Retry with Exponential Backoff and Jitter

Formula: `delay = random(0, min(cap, base × 2^attempt))`

AWS's Marc Brooker showed **full jitter** dramatically reduces synchronized retry storms ("thundering herd") vs. no-jitter backoff: "In the case with 100 contending clients, we've reduced our call count by more than half." AWS SDKs use jittered exponential backoff with a 20-second cap and a token-bucket retry quota.

**Rules:**
- Only retry idempotent operations and transient errors (429, 503, network timeouts)
- Never retry 401/403
- Typical caps: 3–5 max attempts, 10–30s max delay

#### Circuit Breaker (Nygard)

State machine: **closed → open → half-open**. Trips on a failure threshold to stop hammering a failing dependency, preventing cascade and resource exhaustion.

**Reference implementations:**
- **Resilience4j** — JVM de facto standard (after Netflix Hystrix entered maintenance mode in 2018)
- **Polly** — .NET
- Istio/Envoy outlier detection (mesh-level, no code changes)
- sony/gobreaker (Go)
- pybreaker (Python)

Resilience4j nesting: `Retry(CircuitBreaker(RateLimiter(TimeLimiter(Bulkhead(fn)))))`.

#### Bulkhead

Isolate resource pools so one dependency's failure doesn't drain all threads/connections.

#### Additional Patterns

- **Timeout:** never wait forever; budget cascading timeouts in call chains
- **Fallback:** graceful degradation — cached/default/partial response
- **Idempotency keys:** for safe retries; distributed idempotency checks
- **Saga:** compensating transactions for distributed recovery
- **Health checks:** liveness vs. readiness vs. startup probes

### HTTP API Error Handling

Map status codes correctly: 2xx success, 3xx redirect, 4xx client error, 5xx server error.

Recurring decisions: 404 vs 200-with-error-body; 403 vs 404 for security (hide existence); 422 vs 400 for validation. Provide field-level validation error lists. Keep error response shapes consistent across microservices. Separate detailed *internal* errors (logged) from safe *external* messages (no stack traces, SQL, or connection strings in API responses).

---
