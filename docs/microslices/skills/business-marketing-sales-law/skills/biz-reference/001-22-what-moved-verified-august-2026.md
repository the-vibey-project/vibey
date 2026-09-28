---
id: skill-22-what-moved-verified-august-2026-de74086968
purpose: 22 what moved verified august 2026
source: src/vibey_tools/skills/plugins/business-marketing-sales-law/skills/biz-reference/SKILL.md
requires: []
links: ["skill-23-misconceptions-0ff23a684e"]
---

## §22. What Moved — verified August 2026

### 22.1 ⚠️ Marketing measurement — the cookie reversal
**⚠️ This is a genuine correction, and a great deal of advice written between 2020 and
2024 was written for a future that did not arrive.**

**What actually happened:**
- **⚠️ Google reversed course. It abandoned full third-party cookie deprecation in July
  2024, and in April 2025 confirmed it would not introduce the user-choice prompt
  either.** ⚠️ **Third-party cookies remain enabled by default in Chrome.**
- **⚠️ In October 2025 Google wound down ten Privacy Sandbox APIs — including the
  Attribution Reporting API — citing low adoption.** **The replacement was retired before
  the thing it was replacing.**

> **⚠️ GOTCHA — and this is the part that matters: the cookie survived, and the
> measurement did not.** ⚠️ **Safari and Firefox have blocked cross-site tracking by
> default for years, and iOS App Tracking Transparency did the rest.** **Reported figures
> vary by source, but the direction is consistent: attribution coverage fell from 90%+ to
> roughly 60–80%, and in some channels to 30–60%.** ⚠️ **So multi-touch attribution
> degraded regardless of Chrome's decision, and "Google reversed it, so nothing changed"
> is exactly the wrong conclusion.**

**⚠️ The practitioner consensus has converged on triangulation rather than a single source
of truth**, in three layers:
```
1. SERVER-SIDE TRACKING   ⚠️ first-party data plus conversion APIs. Recovers a
   meaningful share of lost signal (reported at 20–40% for Meta's CAPI paired with
   the pixel using event deduplication). Table stakes
2. INCREMENTALITY TESTING ⚠️ holdout and geo experiments. The only causal method,
   and in a January 2026 survey of 500 senior US decision-makers it earned the most
   trust of any measurement method — ahead of MMM and well ahead of the in-platform
   reporting most budgets are still steered by
3. MMM  ⚠️ aggregate regression, no personal data, cookie-proof. For budget allocation
```
**⚠️ MMM's revival is real and the reason is access, not method.** **The technique dates
from the 1960s and was gated behind six-figure consulting engagements.** ⚠️ **Google
open-sourced Meridian (January 2025), Meta maintains Robyn, and PyMC Labs ships
PyMC-Marketing** — **so any team with roughly two years of weekly spend and outcome data
can now run one in-house.**

**⚠️ The honest caveat**: **the IAB's State of Data 2026, surveying 400+ senior planning
and analytics decision-makers, found three in four marketers saying their existing
measurement — attribution, incrementality and MMM alike — is not delivering the speed,
accuracy or trust they need.** ⚠️ **The methods are understood; the data layer beneath
them eroded.** **Nobody has fully solved this, and claims otherwise are sales.**

### 22.2 ⚠️ The US state privacy patchwork
**⚠️ There is still no comprehensive US federal privacy law** — **the American Privacy
Rights Act expired without a vote** — **so states have filled the gap individually.**

> **⚠️ GOTCHA — sources disagree on the count, and I am not going to pretend otherwise.**
> ⚠️ **Most sources checking mid-2026 say **20 states** have comprehensive laws in
> effect** — with **Indiana, Kentucky and Rhode Island** the newest, all effective
> **1 January 2026** — **and citing the IAPP tracker.** **Some say 19; at least one
> reports the landscape expanded from 20 to 24 during 2026 following a further
> legislative wave.**
> ⚠️ **The discrepancy is partly definitional — enacted versus in effect, and whether
> Florida's narrower law counts — and partly that it is genuinely moving.**
> **⚠️ Check the IAPP US State Privacy Legislation Tracker for the current number; do not
> rely on any secondary source including this one for the count.**

**⚠️ What is consistent across sources, and more useful than the count:**
- **Most laws follow the Virginia template**: **opt-out for ordinary data, opt-in for
  sensitive data, AG-only enforcement.** ⚠️ **California is the outlier with a dedicated
  regulator (CPPA) and the only private right of action, for breaches.**
- **⚠️ Thresholds vary and are lower than small businesses assume**: **commonly 100,000
  consumers, but Rhode Island covers 35,000 (or 10,000 if >20% of revenue comes from
  selling data), and Texas has NO revenue threshold — it applies to any covered business
  not classified as a small business by the SBA.**
- **⚠️ Cure periods are disappearing** — **California and Colorado no longer provide them,
  and Rhode Island launched without one.** **The grace period era is ending.**
- **⚠️ Universal opt-out signals are now the leading enforcement theme, and the reason is
  testability**: **a reported twelve states require honouring Global Privacy Control**,
  and ⚠️ **an enforcer can simply load your site with the signal on and watch what
  happens.** **No subpoena required.**
- **⚠️ Enforcement is no longer light** — **a $2.75 million CCPA settlement was announced
  in February 2026, reported as the largest to date, over alleged opt-out failures.**

**⚠️ The practical read for a small business**: **you likely fall below most thresholds —
but "we're too small" is not a safe conclusion**, because ⚠️ **sectoral laws, marketing
laws (§20 → `biz-legal-contracts-ip-employment-and-privacy`), and your vendors' obligations reach you anyway**, and **the §19 → `biz-legal-contracts-ip-employment-and-privacy` baseline is
worth doing regardless of which statute technically applies.**

---
