---
id: skill-13-if-you-run-a-site-1039b90528
purpose: 13 if you run a site
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-ethics-ai-corpora-and-site-defense/SKILL.md
requires: ["skill-12-scraping-for-ai-and-rag-235af83a87"]
links: []
---

## §13. If You Run a Site

**[DURABLE] Worth understanding from both sides, and increasingly a live product decision.**

**Publish your preferences clearly**: robots.txt with the AI-crawler tokens you care about
(**note that `Google-Extended` is a control token Googlebot reads, not a separate crawler —
disallowing it stops Gemini training use without touching search indexing**), a sitemap,
and consider Content Signals / TDM reservations if AI use matters to you (§3.2 → `scraping-legal-landscape-and-permissions`).

**⚠️ Understand the mixed-use trap before you toggle anything** — blocking Training can
block multi-purpose crawlers including Googlebot, Applebot and Bingbot (§3.2 → `scraping-legal-landscape-and-permissions`). **Check what
your configuration actually does rather than what you assumed it does.**

**Decide the strategic question**, because it's genuinely contested: **block AI crawlers
to protect content, allow them for AI-answer visibility, or charge via a pay-per-crawl
scheme.** These are real trade-offs with revenue implications either way, and the honest
position is that nobody knows yet how AI-referral traffic will develop.

**And the counterintuitive one**: **if you want to be cited by AI systems and found by
agents, clean machine-readable structured data is what makes you legible.** Schema.org
markup, a stable catalogue API, and accurate feeds serve search, marketplaces, agents, and
your own consumers simultaneously — **the same work pays off across all of them.**

**Technically**: rate-limit rather than hard-block where you can, offer an API so people
have a sanctioned path, serve conditional requests properly, and remember that **an
aggressive block is also blocking legitimate researchers, accessibility tools, and
archives.**
