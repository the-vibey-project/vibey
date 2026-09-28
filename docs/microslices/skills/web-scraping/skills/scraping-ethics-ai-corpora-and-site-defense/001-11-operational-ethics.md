---
id: skill-11-operational-ethics-c7d2a3b4d3
purpose: 11 operational ethics
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-ethics-ai-corpora-and-site-defense/SKILL.md
requires: []
links: ["skill-12-scraping-for-ai-and-rag-235af83a87"]
---

## §11. Operational Ethics

**[DURABLE] Almost every rule here also happens to keep you unblocked, which is a useful
alignment.**

- **Identify yourself.** A descriptive User-Agent with a contact URL. **The cost of being
  contactable is zero; the benefit is that a site owner emails you instead of banning your
  infrastructure.**
- **Respect robots.txt** (§3.1 → `scraping-legal-landscape-and-permissions`).
- **Rate-limit conservatively.** Start slow, watch response times, back off if the site
  slows. **⚠️ Nights and weekends are not free** — that's when their batch jobs run.
- **Cache aggressively and use conditional requests.** A 304 costs them almost nothing.
- **Don't scrape what you don't need.** Every field you don't use is load you shouldn't
  have generated.
- **Honour `Retry-After` and 429s.** They are literally telling you the answer.
- **Respect a hard block** (§7.2 → `scraping-tooling-extraction-and-blocking`).
- **Consider the target's size.** The same request rate is trivial to a major platform and
  a genuine cost to a hobbyist's blog or a small nonprofit. **Scale your courtesy to their
  infrastructure, not to your appetite.**
- **Attribute where appropriate**, and **don't republish wholesale** — derive, aggregate,
  analyze.
- **Don't build a competing product from a scrape of someone's entire catalogue** and
  expect goodwill.

**[DURABLE] The test worth applying: would you be comfortable if the site owner read your
crawl logs, and could you explain your rate, your purpose, and your data handling without
wincing?** If not, that's information.

---
