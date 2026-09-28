---
id: skill-9-data-quality-aacb2108bb
purpose: 9 data quality
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-scale-reliability-and-data-quality/SKILL.md
requires: ["skill-8-scale-and-reliability-6387646ed1"]
links: ["skill-10-storage-and-operations-e9d31110c5"]
---

## §9. Data Quality

**[DURABLE] This is the section that separates a scraper from a data pipeline, and it is
the one people skip.**

> **⚠️ GOTCHA — silent breakage is the characteristic failure of this field.** A site
> redesigns. Your selector no longer matches. Your extractor returns empty strings.
> **Your pipeline runs green, your dashboard shows data, and every number is wrong.**
> Nobody notices for weeks because nothing crashed.
>
> **A scraper that crashes is a good scraper. A scraper that silently returns `None` for
> the price field is a liability.**

**Validate every record**: required fields present; types correct; **values within
plausible ranges** (a price of 0 or 10,000,000 is a parser bug, not a bargain); enums in
their expected set; dates sane.

**Validate every batch — this is where breakage actually surfaces**: record count within
expected bounds, **null rate per field compared against the historical baseline** (the
single most effective breakage detector), value distributions not suddenly shifted,
duplicate rate stable. **Alert on the delta, not on absolute failure.**

**Cross-check** against a second source, an official API, or a manual spot-check on a
sample. **[DURABLE] Manually verify a handful of records at the start and after every
change** — it takes ten minutes and catches the class of error nothing else will.

**Also track provenance**: source URL, fetch timestamp, parser version, and raw-response
reference on every record. When you find a problem you need to know exactly which records
are affected.

**⚠️ And in 2026, add one more check**: with tarpit and content-poisoning defences now
deployed (§7.1 → `scraping-tooling-extraction-and-blocking`), **verify that what you're collecting is real content**, not generated
filler served to something the site classified as a bot.

---
