---
id: skill-part-12-advanced-debugging-tools-55f1401baf
purpose: part 12 advanced debugging tools
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-11-language-specific-debugging-patterns-c92bdf3bc2"]
links: ["skill-part-13-testing-for-debuggability-66932570f0"]
---

## Part 12 — Advanced Debugging Tools

### Interactive Debuggers

Power moves underused by most engineers:
- **Conditional breakpoints** — break only when a condition holds; invaluable for intermittent bugs
- **Data breakpoints/watchpoints** — break when a memory location changes; for tracking mutations
- **Remote debugging** — attach to a running process on a server/container (mind security and JIT-deoptimization overhead in production)

### Time-Travel / Deterministic-Replay Debugging

- **rr** (Mozilla, Linux) — record execution once, replay deterministically
- **WinDbg TTD** (Windows Time Travel Debugging)
- **UDB** (Undo)
- **Replay.io** (JavaScript/web) — records a deterministic browser session; CI Agent posts root-cause analysis and suggested fix as PR comment; documented case: traced a React race condition to root cause in 7 minutes

### Snapshot Debugging

**Lightrun / Rookout** — inject logpoints/breakpoints into running production code without restart or source changes.

### Memory Debugging

Leak detection via heap profiling and memory-growth monitoring. Common causes: lingering references, JS event-listener leaks, unintended statics.

**Tools:** Eclipse MAT (JVM), dotMemory (.NET), AddressSanitizer/MemorySanitizer/Valgrind (C/C++), `gc`/objgraph (Python reference cycles), Chrome DevTools heap snapshots (V8).

### Concurrency Debugging

- **ThreadSanitizer** — C/C++/Go/Rust race detection; `go test -race`
- Helgrind (Valgrind tool)
- SpotBugs (Java static analysis)
- jstack thread dumps (JVM deadlock)
- Go's runtime deadlock detector
- **goleak** — goroutine leak detection

Async pitfalls: Promise swallowing, `await` in loops, event-loop blocking. Connection-pool exhaustion is a frequent concurrency-induced production failure.

### Network and Database Debugging

**Network:** curl/httpie, Postman/Insomnia, Wireshark/tcpdump, `openssl s_client` for TLS chains, dig/nslookup for DNS, grpcurl for gRPC.

**Database/query debugging:**
- `EXPLAIN`/`EXPLAIN ANALYZE` for query plans (missing indexes, table scans, join strategy)
- **N+1 detection:** Bullet (Rails), Django Debug Toolbar, Hibernate SQL logging
- Deadlock logs (MySQL) and `pg_locks`+`pg_stat_activity` (Postgres)
- Enable SQL logging in ORMs (Hibernate, EF, SQLAlchemy, ActiveRecord) to defeat the ORM transparency problem

---
