---
id: skill-5-the-tool-ladder-4f25f53280
purpose: 5 the tool ladder
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-tooling-extraction-and-blocking/SKILL.md
requires: ["skill-4-how-the-web-serves-data-84094e0020"]
links: ["skill-6-parsing-and-extraction-2d66e58407"]
---

## §5. The Tool Ladder

**[DURABLE] Climb only as far as you need. Each rung costs an order of magnitude more in
resources, complexity, and fragility.**

```
1. requests / httpx        static HTML. Fastest, simplest, cheapest
2. curl_cffi / httpmorph   same speed, but presents a realistic TLS fingerprint (§7.2)
3. Scrapy                  many URLs, one site — concurrency, retries, pipelines,
                           throttling, dedup, all built in
4. Playwright              JavaScript rendering genuinely required
5. Managed service         when the above is more work than it's worth
```

### 5.1 The tools

| Tool | Notes |
|---|---|
| **requests / httpx** | The baseline. `httpx` adds async and HTTP/2 |
| **curl_cffi** | HTTP client that impersonates real browser TLS fingerprints — **same speed as `requests`, far less trivially detectable** |
| **Beautiful Soup** | Forgiving HTML parser. Slow but pleasant |
| **lxml / selectolax** | **Much faster** parsing; use when volume matters |
| **Scrapy** | **The framework for crawling at scale.** Built-in concurrency, `AutoThrottle`, retries, middleware, item pipelines, dedup, and `robots.txt` obedience by default |
| **Playwright** | **[VERSIONED] The default browser-automation choice for new projects in 2026.** Chromium, Firefox, and WebKit; auto-waiting; multiple language bindings; parallel browser contexts |
| **Puppeteer** | Chrome-only. Fine to maintain, little reason to start new work with it |
| **Selenium** | Widely deployed, weakest on stealth (the WebDriver flag and navigator properties are trivially detectable) |
| **Managed / API services** | ScrapingBee, ScraperAPI, Bright Data, Apify, Browserless, Zyte, Scrapfly, Firecrawl — they handle browsers, proxies, and retries. **Usually cheaper than your engineering time** at moderate scale |

**Non-Python**: **Colly** (Go — very fast), **Crawlee** (Node/Python — batteries-included),
**Cheerio** (Node parsing), **Nokogiri** (Ruby), **jsoup** (Java).

### 5.2 Choosing

```
Does the page need JavaScript to render the data you want?
├─ NO  → 100+ URLs from one site? → Scrapy
│        Otherwise → requests/httpx (+ curl_cffi if blocked on fingerprint)
└─ YES → Did you check DevTools for a JSON endpoint first? (§4.2)  ← DO THIS
         ├─ Endpoint exists → go back to the NO branch. You just saved 10× the cost
         └─ Genuinely needs a browser → Playwright
                                        → too much operational burden? Managed service
```

**[DURABLE] Headless browsers cost roughly 10–100× more CPU, memory, and time per page
than an HTTP request.** At any real volume that's the dominant cost line, and it's also
the dominant load you're putting on the target. **Use one only when you've confirmed you
need it.**

---
