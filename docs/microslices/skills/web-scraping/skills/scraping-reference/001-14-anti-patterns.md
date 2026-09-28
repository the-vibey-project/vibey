---
id: skill-14-anti-patterns-a4eb5fb740
purpose: 14 anti patterns
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-reference/SKILL.md
requires: []
links: ["skill-15-contested-questions-36f8abf8ad"]
---

## §14. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Asking "is scraping legal" as one question | It's four questions with different answers (§1.1 → `scraping-legal-landscape-and-permissions`) |
| Scraping a service you hold an account with, against its terms | **The single highest-risk configuration** — hiQ won on CFAA and lost on contract for $500K (§1.3 → `scraping-legal-landscape-and-permissions`) |
| Treating hiQ as blanket permission | It covers **logged-out public access under the CFAA**. Nothing else |
| Assuming public = free to use for any purpose | Copyright, database rights, and GDPR all say otherwise (§1.5 → `scraping-legal-landscape-and-permissions`) |
| Assuming public personal data is outside GDPR | **The Clearview cases turned on legal basis and transparency, not publicness** (§1.5 → `scraping-legal-landscape-and-permissions`) |
| Buying a pre-scraped dataset to avoid the compliance problem | EDPB guidelines cover acquirers too (§1.6 → `scraping-legal-landscape-and-permissions`) |
| Defeating anti-bot measures | **DMCA §1201 theories now target exactly this** (§1.4 → `scraping-legal-landscape-and-permissions`, §7.2 → `scraping-tooling-extraction-and-blocking`) |
| Ignoring a consistent hard block | It's the site's answer. Escalating is the risk (§7.2 → `scraping-tooling-extraction-and-blocking`) |
| Scraping before checking for an API, dataset, feed, or licence | Cheaper, more stable, no legal layer (§2 → `scraping-legal-landscape-and-permissions`) |
| Not opening DevTools to look for a JSON endpoint | **The single highest-leverage 60 seconds in this domain** (§4.2 → `scraping-tooling-extraction-and-blocking`) |
| Reaching for a headless browser by default | 10–100× the cost per page, for you and for them (§5.2 → `scraping-tooling-extraction-and-blocking`) |
| Ignoring sitemaps and crawling links instead | They enumerated the URLs for you (§4.3 → `scraping-tooling-extraction-and-blocking`) |
| Selectors bound to generated class names or `nth-child` | Breaks on the next deploy (§6 → `scraping-tooling-extraction-and-blocking`) |
| Spoofing a Chrome User-Agent while sending a Python TLS fingerprint | Inconsistent, and detected on the mismatch (§7.1 → `scraping-tooling-extraction-and-blocking`) |
| Blaming the site when the real problem is your request rate | Most blocking is a rate problem (§7.2 → `scraping-tooling-extraction-and-blocking`) |
| Not storing raw responses | You'll re-crawl history you already have (§8 → `scraping-scale-reliability-and-data-quality`) |
| Global rate limit instead of per-domain | Hammers one host while idling on others |
| Retrying 404s and 403s | Extra load, zero chance of success |
| A scraper that returns `None` instead of failing | **Silent wrong data is worse than a crash** (§9 → `scraping-scale-reliability-and-data-quality`) |
| No null-rate baseline per field | The most effective breakage detector, and it's cheap (§9 → `scraping-scale-reliability-and-data-quality`) |
| Never manually spot-checking records | Ten minutes catches what nothing else will |
| Assuming everything you collected is real content | Tarpits now serve generated filler (§7.1 → `scraping-tooling-extraction-and-blocking`, §9 → `scraping-scale-reliability-and-data-quality`) |
| No contact information in the User-Agent | You get banned instead of emailed (§11 → `scraping-ethics-ai-corpora-and-site-defense`) |
| Same crawl rate for a major platform and a hobbyist blog | Scale courtesy to their infrastructure (§11 → `scraping-ethics-ai-corpora-and-site-defense`) |
| Treating AI-training scraping like ordinary scraping | Materially different legal regime (§12 → `scraping-ethics-ai-corpora-and-site-defense`) |
| Toggling "block AI bots" without reading the mixed-use rule | **You may have blocked Googlebot** (§3.2 → `scraping-legal-landscape-and-permissions`, §13 → `scraping-ethics-ai-corpora-and-site-defense`) |
| No documented legal basis or provenance per source | Exactly what a regulator asks for, and unreconstructable later (§10 → `scraping-scale-reliability-and-data-quality`) |
| No deletion capability for personal data | Rights are not optional, and models can't easily forget (§1.6 → `scraping-legal-landscape-and-permissions`, §10 → `scraping-scale-reliability-and-data-quality`) |

---
