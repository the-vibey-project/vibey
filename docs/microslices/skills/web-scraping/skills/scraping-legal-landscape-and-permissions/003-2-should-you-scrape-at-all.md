---
id: skill-2-should-you-scrape-at-all-f54a732a92
purpose: 2 should you scrape at all
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-legal-landscape-and-permissions/SKILL.md
requires: ["skill-1-the-legal-landscape-f177756e39"]
links: ["skill-3-robots-txt-and-the-permission-layer-f89de208c4"]
---

## §2. Should You Scrape At All?

**[DURABLE] Scraping is the option of last resort, and teams reach for it first.** Check,
in order:

1. **Is there an API?** Documented, stable, rate-limited, and it won't break when they
   redesign. **Even a paid API is usually cheaper than maintaining a scraper** once you
   price the engineering time.
2. **Is there a bulk dataset or data dump?** Wikipedia, government open data, Common Crawl,
   academic corpora, and many companies publish more than people realise.
3. **Is there an RSS/Atom feed, sitemap, or structured-data markup?** (§4.3 → `scraping-tooling-extraction-and-blocking` — sites often
   hand you clean JSON-LD for free.)
4. **Can you license it?** A commercial data agreement removes the entire legal layer of
   §1 and often costs less than the litigation risk.
5. **Can you just ask?** ⚠️ **Genuinely underused.** Small sites and researchers frequently
   say yes, and an email creates a written record of permission.
6. **Does a data provider already have it?** Often cheaper than building it.

**[DURABLE] Then scrape** — and note that the maintenance cost is the real cost. A scraper
is not a project; it is an ongoing obligation to someone else's front-end decisions.

---
