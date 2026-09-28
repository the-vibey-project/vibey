---
id: skill-3-networking-326883cfb7
purpose: 3 networking
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-engine-architecture-and-networking/SKILL.md
requires: ["skill-2-process-model-ipc-and-sandboxing-d1fb104f6f"]
links: []
---

## §3. Networking

### 3.1 The stack

```
URL parse (WHATWG URL — the spec exists because everyone did this differently)
  → HSTS check → scheme handling
  → DNS (system, DoH, DoT) → Happy Eyeballs (race IPv4/IPv6, prefer fast path)
  → TCP + TLS 1.3, or QUIC (UDP) for HTTP/3
  → connection pool / coalescing
  → HTTP/1.1 · HTTP/2 (multiplex) · HTTP/3 (QUIC, no head-of-line blocking)
  → response: caching, decompression (gzip/br/zstd), MIME sniffing
  → hand to renderer as a stream
```

**Points that matter for implementers:**
- **HTTP/2** multiplexes over one TCP connection, eliminating per-request connections —
  but a lost packet stalls *all* streams (TCP head-of-line blocking).
- **HTTP/3 / QUIC** moves to UDP with per-stream loss recovery, fixing that, plus
  0-RTT resumption and connection migration across network changes. QUIC is implemented in
  userspace, which is why browsers ship their own.
- **Connection coalescing**: reusing one connection for multiple hosts that resolve to the
  same IP with a covering certificate. A real performance win and a subtle correctness trap.
- **HTTP caching is a specification, not a heuristic** — `Cache-Control`, `ETag`,
  `Last-Modified`, `Vary`, revalidation, and the freshness lifetime rules. ⚠️ **Cache
  partitioning by top-level site is now standard** (§9.2 → `browser-security-and-privacy`) and changed the performance
  calculus of shared CDN resources permanently.
- **MIME sniffing** exists because servers lie. It is also a security hazard —
  `X-Content-Type-Options: nosniff` exists to turn it off, and sniffing a response into an
  executable type is a classic XSS vector.
- **Preload/preconnect/prefetch/priority hints** — the browser's scheduling of what to
  fetch when is a large part of real-world page speed.

> **⚠️ GOTCHA — the network service parses hostile input from everyone, in C++, for all
> sites at once.** Chromium names this explicitly as a residual risk (§2.2). Whatever
> your architecture, that component deserves memory-safe implementation, aggressive
> fuzzing, and its own sandbox.
