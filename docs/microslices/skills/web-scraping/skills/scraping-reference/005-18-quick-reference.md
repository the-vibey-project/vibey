---
id: skill-18-quick-reference-7f5b4b8ee6
purpose: 18 quick reference
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-reference/SKILL.md
requires: ["skill-17-the-canon-49201cac0f"]
links: ["skill-19-sources-and-method-c19bee759f"]
---

## §18. Quick Reference

### 18.1 Before you write any code
- [ ] Is there an API, dataset, feed, or licence? (§2 → `scraping-legal-landscape-and-permissions`)
- [ ] **Have you opened DevTools → Network → XHR to look for a JSON endpoint?** (§4.2 → `scraping-tooling-extraction-and-blocking`)
- [ ] Is there a sitemap or schema.org markup? (§4.3 → `scraping-tooling-extraction-and-blocking`)
- [ ] Read `robots.txt`
- [ ] Read the Terms of Service — **and do you hold an account there?** (§1.3 → `scraping-legal-landscape-and-permissions`)
- [ ] Does the data include personal data? If so, what's your legal basis? (§1.5 → `scraping-legal-landscape-and-permissions`)
- [ ] Is this for AI training? Different regime (§12 → `scraping-ethics-ai-corpora-and-site-defense`)
- [ ] Documented: source, purpose, legal basis, retention (§10 → `scraping-scale-reliability-and-data-quality`)

### 18.2 Operating rules
- [ ] Descriptive User-Agent **with contact info**
- [ ] Per-domain rate limiting, conservative to start
- [ ] Conditional requests and caching
- [ ] Exponential backoff with jitter; honour `Retry-After`
- [ ] **Raw responses stored** so you can re-parse without re-crawling
- [ ] Per-field null-rate baseline with alerting
- [ ] Batch-level validation on count, distribution, and duplicates
- [ ] Provenance on every record
- [ ] Manual spot-check after every change
- [ ] A consistent hard block is respected, not escalated (§7.2 → `scraping-tooling-extraction-and-blocking`)

### 18.3 Triage
| Symptom | First look |
|---|---|
| 403 / CAPTCHA immediately | TLS fingerprint (try `curl_cffi`), header set, IP reputation (§7.1 → `scraping-tooling-extraction-and-blocking`) |
| Worked, then started failing | Rate — slow down first, before anything else (§7.2 → `scraping-tooling-extraction-and-blocking`) |
| Empty results, no error | **Selector broke.** Check null rates; this is the dangerous one (§9 → `scraping-scale-reliability-and-data-quality`) |
| Page loads in browser, empty from script | JavaScript rendering — **look for the JSON endpoint before reaching for a browser** (§4.2 → `scraping-tooling-extraction-and-blocking`) |
| Data looks plausible but is subtly wrong | Tarpit/generated content, or a partially-broken parser (§7.1 → `scraping-tooling-extraction-and-blocking`, §9 → `scraping-scale-reliability-and-data-quality`) |
| Works locally, blocked in production | Datacenter IP reputation |
| Slow and expensive | You're using a browser where an HTTP request would do (§5.2 → `scraping-tooling-extraction-and-blocking`) |
| Duplicates across runs | Non-idempotent writes; offset pagination with a shifting window (§4.4 → `scraping-tooling-extraction-and-blocking`, §8 → `scraping-scale-reliability-and-data-quality`) |
| Site owner sends an angry email | **Good — you were contactable.** Respond, slow down, negotiate (§11 → `scraping-ethics-ai-corpora-and-site-defense`) |

---
