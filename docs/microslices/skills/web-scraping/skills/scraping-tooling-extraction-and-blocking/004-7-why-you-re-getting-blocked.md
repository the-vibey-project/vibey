---
id: skill-7-why-you-re-getting-blocked-6d0991cc97
purpose: 7 why you re getting blocked
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-tooling-extraction-and-blocking/SKILL.md
requires: ["skill-6-parsing-and-extraction-2d66e58407"]
links: []
---

## §7. Why You're Getting Blocked

**[DURABLE] Understand detection so you can be a better-behaved client — and so you can
recognize when a site is clearly telling you to stop.** That second reading matters
legally now (§1.4 → `scraping-legal-landscape-and-permissions`).

### 7.1 What sites look at

| Signal | What it means |
|---|---|
| **Rate and volume** | The most common trigger, and **the one that's your fault** |
| **IP reputation** | Datacenter ranges are trivially identifiable; residential and mobile less so |
| **TLS/JA3/JA4 fingerprint** | ⚠️ Your HTTP library's TLS handshake **does not look like a browser's**, regardless of what User-Agent you set — this is why `curl_cffi` exists |
| **HTTP/2 fingerprint** | Frame ordering and settings differ between clients |
| **Headers** | Missing, inconsistent, or implausible header sets — especially **`Sec-CH-UA` and friends that headless browsers omit by default** |
| **Browser fingerprint** | Canvas, WebGL, fonts, screen, timezone, and automation-framework artifacts |
| **Behaviour** | Perfectly-timed requests, no mouse movement, impossible navigation speed, no asset loading |
| **Honeypots** | Links invisible to humans that only a crawler would follow |

**Commercial systems** (Cloudflare, DataDome, Akamai, PerimeterX/HUMAN, Imperva) combine
these with machine learning at network scale. **[VERSIONED] Cloudflare's "AI Labyrinth"**
and similar tarpit approaches now actively feed crawlers generated content rather than
simply blocking — **which means "my scraper is working" is no longer proof that your data
is real** (§9 → `scraping-scale-reliability-and-data-quality`).

### 7.2 The honest guidance

**[DURABLE] Most blocking is a rate problem, and the fix is to slow down.** Before anything
else: reduce concurrency, add delays, cache aggressively, use conditional requests, and
crawl off-peak (§11 → `scraping-ethics-ai-corpora-and-site-defense`). This resolves a large share of blocks and is what you should have
been doing anyway.

**Legitimate technical fixes**: send a **complete, coherent, honest header set** (a
descriptive User-Agent with contact info — **not** a spoofed Chrome string); use
`curl_cffi` so your TLS fingerprint matches the client you claim to be; handle cookies and
sessions properly; respect `Retry-After` and back off exponentially on 429/503.

> **⚠️ GOTCHA — the line you need to think about before crossing.** There is a meaningful
> difference between **"my client is being misidentified as malicious, so I'll make it
> present itself accurately and slow down"** and **"this site has deployed measures to stop
> automated collection, so I'll defeat them."**
>
> **The second is what DMCA §1201 claims target** (§1.4 → `scraping-legal-landscape-and-permissions`). Reddit's theory against
> Perplexity is precisely that rate limits and anti-bot systems are technological
> protection measures and defeating them is circumvention. **Solving CAPTCHAs at scale,
> rotating residential proxies specifically to evade IP-based blocking, and reverse-
> engineering anti-bot challenges sit on the wrong side of that line** — regardless of
> whether the underlying data is public.
>
> **A hard block, delivered consistently after you've slowed down and identified yourself,
> is the site's answer.** The professional response is to seek permission, license the
> data, use an official API, or walk away — not to escalate.
