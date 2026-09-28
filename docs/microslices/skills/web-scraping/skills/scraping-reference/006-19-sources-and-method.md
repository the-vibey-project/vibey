---
id: skill-19-sources-and-method-c19bee759f
purpose: 19 sources and method
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-reference/SKILL.md
requires: ["skill-18-quick-reference-7f5b4b8ee6"]
links: []
---

## §19. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §4 → `scraping-tooling-extraction-and-blocking` (how pages serve
data), §5–§6 → `scraping-tooling-extraction-and-blocking` (tooling and extraction), §8 → `scraping-scale-reliability-and-data-quality` (architecture), §9 → `scraping-scale-reliability-and-data-quality` (data quality), §10 → `scraping-scale-reliability-and-data-quality`, §11 → `scraping-ethics-ai-corpora-and-site-defense`
(ethics), §14 — rests on HTTP standards, long-stable engineering practice, and failure
modes reported consistently by practitioners. Every **time-sensitive** claim — and in this
domain the **legal layer is moving faster than the technical layer** — was verified against
a primary or near-primary source in **August 2026** and is flagged in §16 with a decay-risk
rating. §7 → `scraping-tooling-extraction-and-blocking` describes detection mechanisms at the conceptual level for the purpose of
diagnosing blocks and behaving better; **it deliberately does not provide evasion
techniques for specific commercial anti-bot products**, both because §1.4 → `scraping-legal-landscape-and-permissions` makes that
legally live and because the professional answer to a deliberate block is to seek
permission rather than escalate.

**Search log** (August 2026): web scraping case law (hiQ, Van Buren, Meta v. Bright Data,
Reddit v. Perplexity) · Cloudflare AI crawler controls, Pay Per Crawl, and the robots.txt
standards landscape · Playwright/Scrapy/tooling comparison and bot detection · GDPR
scraping enforcement, EDPB guidelines, and the EU AI Act.

**Primary and near-primary sources consulted (selected):**
- **Cloudflare's own blog and docs** — "Content Independence Day" (July 2025 and the
  July 2026 "Your site, your rules" post), AI Crawl Control documentation, and the
  Pay Per Crawl changelog; **Help Net Security** on the content-use levels and the
  mixed-use crawler rule
- **EDPB** Guidelines 03/2026 on web scraping for generative AI, via **Sidley's Data
  Matters** analysis and contemporaneous reporting; **EU AI Act** GPAI obligations and
  timelines
- **Gowling WLG** and **URM Consulting** on the UK Upper Tribunal's Clearview decision;
  **FPF** on the AI Act's targeted/untargeted facial-scraping distinction; Dutch DPA and
  other DPA enforcement reporting
- Case-law summaries of **Van Buren**, **hiQ v. LinkedIn** (including the December 2022
  settlement terms), and **Meta v. Bright Data** from multiple independent legal and
  industry analyses; contemporaneous reporting on **Reddit v. Perplexity**'s §1201 theory
- Tooling comparisons from **Browserless**, **ScrapingBee**, **ScrapFly**, **Oxylabs**,
  and independent practitioner write-ups

**Confidence statement.** **High confidence** in §4–§11 → `scraping-tooling-extraction-and-blocking`, `scraping-scale-reliability-and-data-quality`, `scraping-ethics-ai-corpora-and-site-defense` and §18 — HTTP semantics,
extraction practice, and pipeline engineering are stable and consistently described.
**High confidence** in the Cloudflare mechanics and dates, which come from Cloudflare's own
announcements and documentation. **Moderate confidence on the legal material in §1 → `scraping-legal-landscape-and-permissions`**, and
the caveats matter: **case summaries came largely from law-firm and industry analyses
rather than from the opinions themselves**; **US case law is circuit-specific and hiQ is a
Ninth Circuit holding**; **Reddit v. Perplexity was pending and its outcome is genuinely
unknown**; and **the EDPB guidelines were in draft with consultation open to 30 October
2026**, so the positions summarized in §1.6 → `scraping-legal-landscape-and-permissions` may change before adoption. **Lower confidence
on the crawl-to-referral ratio figures** in §16 — they come from a single analytics
provider's network view, methodology varies, and the numbers moved substantially within
2026. **This is not legal advice**; §1 → `scraping-legal-landscape-and-permissions` maps frameworks and identifies the questions to put
to counsel, and the answer for any specific operation depends on jurisdiction, data type,
data subject, and purpose in ways no general document can resolve.
