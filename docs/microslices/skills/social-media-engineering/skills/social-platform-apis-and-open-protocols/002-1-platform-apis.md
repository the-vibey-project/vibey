---
id: skill-1-platform-apis-eb32247b43
purpose: 1 platform apis
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-platform-apis-and-open-protocols/SKILL.md
requires: ["skill-0-routing-f5fd29e1f5"]
links: ["skill-2-open-protocols-02e21e1f8c"]
---

## §1. Platform APIs

**[VERSIONED — and the single most important practical section here.]**

### 1.1 What happened

**[DURABLE lesson, VERSIONED specifics] The 2023–2026 period ended the era of open social
APIs, and the pattern was consistent: reprice or restrict with short notice, and let
downstream developers absorb the consequences.**

**Twitter/X**: the free tier that had supported a decade of bots, research, and
third-party clients closed. ⚠️ **Developers on the free v1.1 API were given nine days to
migrate.**
**Reddit (July 2023)**: **$0.24 per 1,000 API calls** for commercial use with roughly
30 days' notice. **Apollo — the most-loved third-party client, 1.5M active users — shut
down** rather than absorb it, its developer having been told the cost would be
**~$20M/year**. ⚠️ **Pushshift, the academic Reddit archive, was terminated.** Reddit also
ended self-service access; **new applications require approval under a "Responsible
Builder Policy."**

**⚠️ The $20M figure became the defining anecdote for how API repricing redistributes risk
from the platform onto the downstream developer** — and it is the right thing to remember
before you build.

### 1.2 ⚠️ The X API in 2026

**[VERSIONED — verify before budgeting; this has changed repeatedly.]**

**As of February 2026, X moved new developers to pay-per-use and closed Basic and Pro to
new signups.** Legacy subscribers are grandfathered. Reported rates as of mid-2026:

| Action | Reported rate |
|---|---|
| Read your own posts/followers/lists | ~$0.001 per resource (cut sharply April 2026) |
| **Read a third-party post** | **~$0.005** — ⚠️ **the rate that dominates data projects** |
| User / follower / trends read | ~$0.010 |
| Create a plain post | ~$0.015 |
| ⚠️ **Create a post containing a URL** | **~$0.20** — **~13× a plain post** |

> **⚠️ GOTCHA — three structural traps beyond the per-call rates:**
> - **The 2,000,000 post-read monthly cap.** ⚠️ **At $0.005/read, hitting it means you've
>   spent ~$10,000 — and then you stop until the cycle resets or you move to Enterprise
>   (reported entry ~$42,000/month, custom contract, multi-week sales process).** There is
>   **no middle tier any more** — the $5,000 Pro plan that included full-archive search is
>   closed to new signups, creating a cliff between self-serve and Enterprise.
> - **⚠️ The URL surcharge lands hardest on exactly the automation people build**:
>   auto-posting newsletter links, blog posts, release announcements.
> - **⚠️ As of 20 April 2026, following, liking, and quote-posting were removed from
>   self-serve writes entirely** — withdrawn rather than repriced, Enterprise-only.
>   **If your product does social actions on a user's behalf, check this before designing.**
>
> **Also: your stated use case is contractually binding**, and materially changing it
> requires notifying X and getting approval.

**⚠️ The third-party reseller market exists and the price gap is enormous** — resellers
advertise reads at a small fraction of the official rate, and one comparison put the
official pay-per-use rate at roughly **33× a third-party's**. **But**: ⚠️ **scraping X
directly is explicitly prohibited by its terms**, resellers occupy a legally contested
position (see a web-scraping reference for why), and **you inherit their compliance
posture and their continuity risk.** **The common architecture that results: official API
for posting and authenticated actions, third party for reads at volume** — with the
trade-off understood and documented, not assumed away.

### 1.3 The wider landscape
**Meta Graph** — weeks of app review before permissions are granted; **LinkedIn** —
partnership agreements for anything beyond surface data; **TikTok** — formal application
process; **YouTube** — a quota ceiling rather than per-call pricing. **⚠️ The common shape:
approval gates rather than open signup, and apps that fail review lose endpoints they were
using in development.**

**[DURABLE] How to build so this doesn't kill you:**
- **⚠️ Abstract the platform behind your own interface** from day one. When terms change,
  you change one adapter.
- **Cache aggressively and store what you're permitted to store** — re-fetching is the
  cost centre.
- **Model your costs at projected volume, not current volume**, and know where the cliff
  is (§1.2).
- **⚠️ Have a fallback path** — a second provider, a degraded mode, or a plan to exit.
- **Don't make a single platform load-bearing** for your product's core value.
- **Read the terms, including the use-case obligation**, and re-read them at renewal.
- **⚠️ Assume the free tier will end.** It has, everywhere, repeatedly.

---
