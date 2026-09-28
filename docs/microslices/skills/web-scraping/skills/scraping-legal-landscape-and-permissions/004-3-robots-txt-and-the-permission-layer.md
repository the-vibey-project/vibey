---
id: skill-3-robots-txt-and-the-permission-layer-f89de208c4
purpose: 3 robots txt and the permission layer
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-legal-landscape-and-permissions/SKILL.md
requires: ["skill-2-should-you-scrape-at-all-f54a732a92"]
links: []
---

## §3. robots.txt and the Permission Layer

### 3.1 robots.txt

**[DURABLE] The Robots Exclusion Protocol is a voluntary convention** (standardized as
**RFC 9309**), served at `/robots.txt`. It tells well-behaved crawlers what they may access.
Key directives: `User-agent`, `Disallow`, `Allow`, `Sitemap`, and `Crawl-delay` (widely
implemented, not in the RFC).

**⚠️ robots.txt is not an access control and never was.** It does not enforce anything;
it declares a preference. **But ignoring it is now materially riskier than it used to be**
for three separate reasons: it evidences bad faith in a contract or tort dispute, it
signals to the site's defensive layer that you're not a good-faith crawler, and under the
EU AI Act **machine-readable opt-outs now carry copyright significance for model training**
(§1.6).

**[DURABLE] Read it, respect it, and identify yourself.** A descriptive `User-Agent` with
a contact URL costs nothing and is the difference between a site owner emailing you and a
site owner blocking your whole ASN.

### 3.2 The emerging permission and payment layer

**[VERSIONED — a genuinely new stratum of the web, and it is consolidating fast.]**

**Cloudflare** has become the de facto enforcement layer:
- **"Content Independence Day" (July 2025)** introduced a one-click **Block AI Bots**
  toggle and the **Pay Per Crawl** private beta, which **revived HTTP 402 (Payment
  Required)** — blocked crawlers receive a 402 signalling that content is available for a
  price, with Cloudflare acting as **merchant of record**.
- **1 July 2026**: the binary toggle was replaced with **three separately controllable
  categories — Search, Agent, and Training** — each with states from allow through
  "block only on pages with ads" to "block everywhere." **Available to all customers
  including the free tier.**
- ⚠️ **15 September 2026**: **Training and Agent crawlers blocked by default on
  ad-serving pages** for new domains, new sites of existing customers, and **all existing
  free-tier customers.** Search remains allowed by default. Cloudflare's stated reasoning:
  "an ad is a signal that a website owner meant for a person to land there and see it."
- ⚠️ **The mixed-use trap**: if a zone blocks Training, **multi-purpose crawlers such as
  Googlebot, Applebot, and BingBot get blocked too**, even where Search is allowed. This
  only applies to zones that have actively enabled Training blocking — but **site owners
  who toggle "block AI" without understanding this can remove themselves from search.**
- **Content Signals** in robots.txt gained a **`use` parameter** expressing post-crawl
  usage preferences at three levels: **Immediate** (no storage or reuse), **Reference**
  (indexing, excerpts, links back), **Full** (summaries or reproduction). Not enforceable
  by robots.txt itself, but Cloudflare reports Verified Bot compliance via BotBase.

**The standards picture is fragmented**: **IETF AIPREF** (working toward a standards-track
spec, with a Content-Usage header and matching robots.txt rule), **RSL (Really Simple
Licensing)** handling the permission and compensation layer AIPREF omits, plus **ai.txt**
and **TDMRep**, each proposing its own file. **[CONTESTED] Nobody has won**, and a site
may express preferences in three incompatible places.

**⚠️ The economics driving this are stark.** Cloudflare-network analysis reported that
**89.4% of AI crawler traffic serves training or mixed purposes rather than search**, and
tracked crawl-to-referral ratios in the **hundreds-to-thousands of pages crawled per
referral sent back** — which is precisely why the historic crawler bargain (we take your
content, we send you traffic) has broken down and why the permission layer exists at all.
