---
id: skill-12-scraping-for-ai-and-rag-235af83a87
purpose: 12 scraping for ai and rag
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-ethics-ai-corpora-and-site-defense/SKILL.md
requires: ["skill-11-operational-ethics-c7d2a3b4d3"]
links: ["skill-13-if-you-run-a-site-1039b90528"]
---

## §12. Scraping for AI and RAG

**[VERSIONED — the highest-risk use case, and where §1.6 → `scraping-legal-landscape-and-permissions` concentrates.]**

**Technical differences from classic scraping**: you want **clean readable text** rather
than fields (boilerplate stripping, main-content extraction, markdown conversion),
**chunking** that respects document structure, **metadata and provenance per chunk** (so a
retrieval system can cite), and **freshness** management.

**⚠️ The legal picture is materially different from ordinary scraping**, and conflating
them is how teams get into trouble:
- **EDPB Guidelines 03/2026** apply to both direct scrapers and **organizations acquiring
  pre-scraped datasets from brokers** — buying the corpus does not transfer the problem
  away (§1.6 → `scraping-legal-landscape-and-permissions`).
- **Personal data cannot easily be removed from a trained model**, so the compliance
  decision has to be made **upstream, before training**.
- **EU AI Act GPAI obligations** require publishing a training-data summary and respecting
  machine-readable opt-outs, with enforcement from **2 August 2026**.
- **DMCA §1201 circumvention theories** are being tested specifically in the
  AI-training context (§1.4 → `scraping-legal-landscape-and-permissions`).
- **Copyright**: reproducing creative work for training is genuinely unsettled and heavily
  litigated; **the EU TDM exception is opt-out-dependent** (§3.2 → `scraping-legal-landscape-and-permissions`).

**[DURABLE] The practical governance minimum**: maintain a **source inventory with legal
basis per source**, **respect opt-out signals and log that you did**, exclude sensitive
categories at collection, keep provenance through to the training set, and get review
before training or reselling. **This is dull and it is the actual work.**

---
