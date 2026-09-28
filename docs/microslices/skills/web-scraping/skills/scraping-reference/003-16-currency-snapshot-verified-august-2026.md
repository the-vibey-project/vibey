---
id: skill-16-currency-snapshot-verified-august-2026-ec21d4c5bf
purpose: 16 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-reference/SKILL.md
requires: ["skill-15-contested-questions-36f8abf8ad"]
links: ["skill-17-the-canon-49201cac0f"]
---

## §16. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **CFAA line** | **Van Buren (2021)** narrowed "exceeds authorized access." **hiQ v. LinkedIn (9th Cir., April 2022)**: scraping publicly accessible data doesn't violate the CFAA. **Meta v. Bright Data (N.D. Cal., Jan 2024)**: Judge Chen dismissed Meta's CFAA claim over **logged-out** public Facebook/Instagram scraping. **Logged-out public scraping is defensible** | Low |
| **The contract counterweight** | ⚠️ **hiQ lost on breach of LinkedIn's User Agreement (accepted by creating accounts)** — **$500,000, permanent injunction, destruction of the scraped corpus.** In *Meta v. Bright Data* the contract claim **partially survived only for the period of an active contractual relationship**; general browsewrap ToS was treated as a **weaker basis** | Low |
| **⚠️ The §1201 shift** | **Reddit sued Perplexity AI and data-collection providers in late 2025**, claiming **DMCA §1201 circumvention of rate limits and anti-bot systems** for AI training. **Reframes the question from "was it public?" to "did you defeat a protection?"** Pending as of early 2026. Similar theories in creator suits over YouTube scraping | **High** |
| **EDPB Guidelines 03/2026** | ⚠️ **Adopted at the July 2026 plenary** (published 7 July, adopted 8 July) — **first pan-EU framework on web scraping for generative AI**, confirming **GDPR applies in full with no AI carve-out.** Reported positions: **consent unlikely to be a valid basis**; **legitimate interest requires a documented three-part test per deployment**; **data minimisation before scraping**; **near-prohibition on sensitive data**; **personal data can't easily be deleted from a trained model.** Covers **acquirers of pre-scraped datasets**, not just scrapers. Companion anonymisation guidelines set a three-criterion test. **Draft — consultation open to 30 October 2026** | **High** |
| **EU AI Act** | In force 1 Aug 2024; GPAI obligations from **2 Aug 2025**; ⚠️ **enforcement teeth from 2 August 2026** — GPAI fines up to **€15M or 3% of turnover**. GPAI providers must **publish a training-data summary** and **respect machine-readable copyright opt-outs**, giving robots.txt and TDM reservations legal weight. **Bans untargeted scraping of facial images** for FR databases (targeted collection distinguished) | Medium |
| **Clearview line** | **€30.5M (Dutch DPA, 2024)**, actions from the Italian Garante and CNIL, **$75M+ cumulative across US/UK/EU**. **UK Upper Tribunal held Clearview within UK GDPR scope** despite being wholly outside the UK, rejecting the law-enforcement exemption for a private company — a potential **£7.5M ICO fine**. ⚠️ **These cases turned on legal basis and transparency, not on whether the data was public** | Low |
| **Cloudflare: the enforcement layer** | **July 2025 "Content Independence Day"**: one-click Block AI Bots + **Pay Per Crawl** private beta reviving **HTTP 402**, Cloudflare as merchant of record. **1 July 2026**: replaced by **three categories — Search, Agent, Training** — each with allow / block-on-ad-pages / block-everywhere, **free tier included**. ⚠️ **15 September 2026: Training and Agent blocked by default on ad-serving pages** for new domains, new sites of existing customers, and **all existing free-tier customers**; Search allowed by default. **Pay Per Crawl evolving toward "Pay Per Use"** | **High** |
| **⚠️ The mixed-use trap** | **If a zone blocks Training, multi-purpose crawlers including Googlebot, Applebot and BingBot are blocked too**, even where Search is allowed — applying only to zones that actively enabled Training blocking. **Opt out via Security settings before 15 September 2026** to preserve current behaviour | **High** |
| **Content Signals / standards** | Cloudflare's **Content Signals** gained a **`use` parameter**: **Immediate** (no storage/reuse), **Reference** (index, excerpt, link back), **Full** (summarize/reproduce). Not enforceable by robots.txt; compliance reported via BotBase. Competing efforts: **IETF AIPREF** (Content-Usage header, standards-track milestone targeted Aug 2026), **RSL**, **ai.txt**, **TDMRep**. **No winner** | **High** |
| **Crawler economics** | Cloudflare-network analysis (Q1 2026): **89.4% of AI crawler traffic serves training or mixed purposes rather than search**; GPTBot the most-blocked AI crawler. Crawl-to-referral ratios tracked in the hundreds-to-thousands per referral, **improving through 2026** (one series reported Anthropic's falling 3,386:1 → 1,917:1 June→July; OpenAI 647:1 → 251:1) | **High** |
| **Tooling** | **Playwright is the default browser-automation choice for new 2026 projects** (Chromium/Firefox/WebKit, auto-waiting, multi-language). Puppeteer maintenance-mode-ish for new work; **Selenium weakest on stealth** (WebDriver flag trivially detected). **`curl_cffi` / `httpmorph`** for realistic TLS fingerprints at HTTP-client speed. **Scrapy** remains the scale framework. ⚠️ **Cloudflare's "AI Labyrinth"** and similar tarpits serve generated content rather than blocking | Medium |

**Goes stale fastest:** the Cloudflare defaults and the standards contest; the EDPB
guidelines as they move from draft to final; Reddit v. Perplexity. **Essentially never
stale:** §4 → `scraping-tooling-extraction-and-blocking` (how pages serve data), §6 → `scraping-tooling-extraction-and-blocking` (selector stability), §8 → `scraping-scale-reliability-and-data-quality` (architecture), §9 → `scraping-scale-reliability-and-data-quality` (data
quality), §11 → `scraping-ethics-ai-corpora-and-site-defense` (ethics), §14.

---
