---
id: skill-15-contested-questions-36f8abf8ad
purpose: 15 contested questions
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-reference/SKILL.md
requires: ["skill-14-anti-patterns-a4eb5fb740"]
links: ["skill-16-currency-snapshot-verified-august-2026-ec21d4c5bf"]
---

## §15. Contested Questions

**15.1 Is scraping public data ethical?** *For*: information wants to be accessible, public
data supports research, journalism, price transparency, and competition, and the hiQ court
warned specifically about **"information monopolies that would disserve the public
interest."** *Against*: users posted to a platform, not to the world's data brokers; scale
changes the character of the act; and site operators bear real infrastructure cost. **Both
positions are seriously held and the answer plainly depends on the data and the use.**

**15.2 Does robots.txt bind you?** Technically voluntary and legally not an access control
— **but ignoring it evidences bad faith, and machine-readable opt-outs now carry copyright
weight under the EU AI Act.** The "it's just a suggestion" position has weakened
considerably.

**15.3 Should sites block AI crawlers?** §13 → `scraping-ethics-ai-corpora-and-site-defense`. The historic bargain (content for traffic)
has demonstrably broken — crawl-to-referral ratios in the hundreds-to-thousands support
that — but blocking forfeits AI-answer visibility, and nobody yet knows what that's worth.

**15.4 Is pay-per-crawl the right model?** *For*: it prices an externality and compensates
creators. *Against*: it concentrates enormous gatekeeping power in one CDN, disadvantages
smaller AI developers and researchers, and **the "web as open commons" framing is genuinely
lost if crawling requires payment rails.**

**15.5 Should the CFAA/§1201 line move?** *For scrapers*: hiQ's monopoly reasoning, and
§1201 was written for DRM, not rate limiters. *For platforms*: they bear the cost, and
users didn't consent to bulk collection. **Reddit v. Perplexity may substantially determine
this.**

**15.6 LLM extraction vs. deterministic selectors.** §6 → `scraping-tooling-extraction-and-blocking`. Robustness and speed of
development against cost, non-determinism, and **hallucinated fields that pass validation**.

**15.7 Managed service vs. build it yourself.** *Service*: faster, handles the operational
layer, often cheaper than engineering time. *Against*: cost at scale, vendor lock-in, less
control, and **you inherit their collection practices and their legal posture** — which,
given §1 → `scraping-legal-landscape-and-permissions`, is not a minor consideration.

---
