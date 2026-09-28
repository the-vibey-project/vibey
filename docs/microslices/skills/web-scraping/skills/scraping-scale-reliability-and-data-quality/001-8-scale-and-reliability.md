---
id: skill-8-scale-and-reliability-6387646ed1
purpose: 8 scale and reliability
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-scale-reliability-and-data-quality/SKILL.md
requires: []
links: ["skill-9-data-quality-aacb2108bb"]
---

## §8. Scale and Reliability

**[DURABLE] The architecture that survives contact with reality:**

```
URL frontier (queue, deduplicated, prioritized)
   → fetcher pool (rate-limited PER DOMAIN, retries with backoff)
     → response cache (raw HTML stored — see below)
       → parser (pure function: HTML → structured record)
         → validator (§9)
           → storage + change detection
```

**[DURABLE] Store the raw response, not just the parsed output.** This is the single most
valuable architectural decision in a scraping system: when your parser turns out to have
been wrong for three weeks, **you can re-parse history instead of re-crawling** — which is
cheaper for you and, more importantly, costs the target site nothing.

**Rate limiting is per-domain, not global.** A token bucket per host, with concurrency
caps. Scrapy's `AutoThrottle` adapts to observed latency, which is both polite and
effective.

**Retries**: exponential backoff **with jitter**, only on transient failures (429, 5xx,
timeouts), with a cap. **⚠️ Retrying a 404 or a 403 is just extra load** — classify errors
before retrying.

**Also**: **conditional requests** (`If-Modified-Since`, `If-None-Match` → 304 responses
cost the server almost nothing), **incremental crawling** (only fetch what changed —
sitemaps with `lastmod` help), **checkpointing** so a crash doesn't restart from zero,
**idempotent writes** so a re-run doesn't duplicate, and **distributed queues** (Redis,
SQS) when one machine isn't enough.

**Proxies**: legitimate uses exist — geographic content variation, avoiding
single-IP saturation, and reliability. **⚠️ But note that "rotating residential proxies to
evade blocking" is the use case §7.2 → `scraping-tooling-extraction-and-blocking` flags**, and separately, **residential proxy networks
have documented supply-chain ethics problems** around how consumer bandwidth is sourced and
whether those users understood what they consented to. That's worth knowing before you buy.

---
