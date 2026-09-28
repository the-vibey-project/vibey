---
id: skill-part-3-structured-logging-deb8d5dabc
purpose: part 3 structured logging
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-2-correlation-trace-ids-the-distributed-debugging-primitive-3d8a572a13"]
links: ["skill-part-4-opentelemetry-cncf-graduated-may-11-2026-4ef5a9c8ef"]
---

## Part 3 — Structured Logging

### Philosophy and Design

Logs are the primary data source when production bugs can't be reproduced locally. Watch the **Heisenberg problem**: excessive logging changes the timing/behavior of the system being observed and can itself cause performance issues on hot paths.

**Structured over unstructured logging is the modern default.** JSON is the lingua franca. The rule: **the message field is a static, greppable string; variable data goes in structured fields.**

### Log Levels

| Level | Purpose |
|-------|---------|
| TRACE | Finest detail |
| DEBUG | Diagnostic |
| INFO | Business events |
| WARN | Recoverable/unusual |
| ERROR | Failures needing attention |
| FATAL/CRITICAL | Process death |

Run production at INFO or WARN. Support **dynamic level adjustment at runtime without restart.**

Common misuse: logging everything at INFO, or using ERROR for recoverable conditions (causing alert fatigue).

### What to Log / Not Log

**Log:**
- Entry/exit of critical operations
- The *why*, not just the *what*
- Request/response metadata (method, path, status, duration)
- Full exception stack traces with the original cause chain (don't swallow `initCause`)
- Third-party API calls (endpoint, status, latency, retries)
- Slow queries
- Security events (authn/authz outcomes — mandatory for compliance)

**Never log:**
- Passwords, tokens, API keys
- SSNs, credit-card/PCI data, HIPAA PHI
- Use field-level masking/scrubbing (`ReplaceAttr` in Go slog, redaction in Pino, Serilog enrichers)
- Avoid high-frequency hot-path logging

### Good Log Record Fields

A complete log record carries: timestamp (UTC), level, message, service/component, correlation/trace ID, user/tenant context, environment, host/pod, and additional structured fields. The emerging standard for field naming is **OpenTelemetry semantic conventions** (e.g., `http.method`, `http.status_code`, `exception.type`/`exception.message`/`exception.stacktrace`).

### Sampling at Volume

- **Head-based:** decide at ingestion
- **Tail-based:** decide after seeing the outcome — keeps all errors
- **Reservoir/structured downsampling:** configurable rates per category
- Always sample errors at 100% regardless of base rate

### Logging Frameworks by Language (2026)

**Java/JVM:**
- SLF4J (API) + Logback is the modern default
- Log4j 2 for high-performance async appenders
- Avoid `java.util.logging`
- Lombok `@Slf4j`, MDC for context

**Python:**
- stdlib `logging` (baseline)
- **structlog** — best-in-class for structured logging
- **loguru** — best developer experience
- `python-json-logger` for JSON output
- `contextvars` for propagation

**Node.js:**
- **Pino** — fastest (JSON-first, low overhead; benchmarks show roughly 7× faster than Winston using worker-thread transport)
- **Winston** — most popular
- Never `console.log` in production
- `AsyncLocalStorage` for context propagation

**Go:**
- **`log/slog`** (standard library since Go 1.21, largest stdlib addition since Go 1) — now the recommended default
- Frontend `Logger` + pluggable `Handler` (TextHandler/JSONHandler)
- Benchmarks slower than **zap** (Uber) and **zerolog** (zero-allocation) for hot-path work; the Go team optimized for the ≤5-attribute case (>95% of real usage)
- Use zap/zerolog only for hot-path allocation-sensitive logging; logrus is legacy

**.NET/C#:**
- `Microsoft.Extensions.Logging` abstraction with `ILogger<T>` + DI
- **Serilog** — the leading structured choice (rich sinks, enrichers)
- NLog — mature alternative

**Rust:**
- `log` (API) + env_logger for simple cases
- **tracing** (Tokio) — the async-aware ecosystem standard

**Ruby:** stdlib Logger, Ougai, semantic_logger, Rails logger

**PHP:** **Monolog** (PSR-3) is the standard

### Log Aggregation and Storage

**Shipping patterns:** sidecar (Fluentd/Fluent Bit), DaemonSet shippers, application-direct

**Fluent Bit** — lightweight, high-performance C-based shipper  
**Fluentd** — heavier, plugin-rich Ruby-based aggregator

**Backends:**
- **ELK/EFK stack** — Elasticsearch + Logstash/Beats/Fluentd + Kibana
- **OpenSearch** — AWS's Apache-2.0 fork of Elasticsearch
- **Grafana Loki** — label-indexed, no full-text index, LogQL; the cost-efficient choice
- **Splunk** — enterprise dominant, SPL
- **Datadog Logs**
- **Azure Monitor/Log Analytics** — KQL
- **AWS CloudWatch Logs** — Logs Insights, metric filters

Cost management: tiered hot/warm/cold retention and selective indexing.

---
