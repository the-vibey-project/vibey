---
id: skill-1-the-legal-landscape-f177756e39
purpose: 1 the legal landscape
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-legal-landscape-and-permissions/SKILL.md
requires: ["skill-0-routing-97ee6e04c1"]
links: ["skill-2-should-you-scrape-at-all-f54a732a92"]
---

## §1. The Legal Landscape

### 1.1 The four questions

**[DURABLE] "Is web scraping legal?" is unanswerable as asked**, because at least four
independent frameworks apply and **an operation can be fine under one and unlawful under
another.**

| Question | Framework | Rough position |
|---|---|---|
| **How did you access it?** | Computer-access law (CFAA, UK CMA, etc.) | **Public, logged-out access is defensible** (§1.2) |
| **What did you agree to?** | Contract / Terms of Service | **This is where scrapers actually lose** (§1.3) |
| **What is the data?** | Copyright, database rights, personal data | Facts ≠ creative works; personal data is its own regime (§1.5) |
| **What will you do with it?** | Privacy law, AI regulation, resale | **The fastest-moving layer in 2026** (§1.5–1.6) |

### 1.2 Computer-access law: the settled part

**[VERSIONED, and this is the most favourable line for scrapers.]**

- **Van Buren v. United States (2021, US Supreme Court, 6–3)** narrowed the CFAA's
  "exceeds authorized access" clause to accessing **areas that are off-limits** — using
  permitted access for the wrong purpose is not a CFAA violation. **This set the ceiling
  on how far the CFAA reaches scraping.**
- **hiQ v. LinkedIn (9th Cir., reaffirmed April 2022)** held that **scraping publicly
  accessible data does not violate the CFAA.** The court's reasoning is worth knowing:
  a broad reading would give platforms "free rein to decide, on any basis, who can collect
  and use" public data, risking "possible creation of information monopolies that would
  disserve the public interest."
- **Meta v. Bright Data (N.D. Cal., January 2024)** extended it to social platforms —
  **Judge Chen dismissed Meta's CFAA claim** over scraping public Facebook and Instagram
  pages **in a logged-out state**.

**[DURABLE] The line that emerged and keeps holding: logged-out public scraping is
defensible; anything behind a login is not.** If the server hands you the page without
authentication, you had authorization to access it.

### 1.3 Contract: where scrapers actually lose

> **⚠️ GOTCHA — hiQ won the CFAA argument and lost the case.** In November 2022 the court
> found hiQ had **breached LinkedIn's User Agreement, which it had accepted by creating
> accounts.** The matter ended in a consent judgment: **$500,000, a permanent injunction,
> and destruction of the scraped corpus.** The favourable CFAA precedent survives; hiQ
> did not.
>
> **The CFAA protects you from hacking claims. It does not protect you from contracts you
> agreed to.**

**The distinction courts have drawn**: terms accepted by **creating an account** (clickwrap)
bind you. **Browsewrap terms** — the "by using this site you agree" link in the footer,
which a logged-out visitor never affirmatively accepts — are a **much weaker basis**.
In *Meta v. Bright Data* the contract claim **partially survived, but only for the period
when Bright Data had an active contractual relationship with Meta** as a former partner.

**[DURABLE] The practical rule: never scrape a service you hold an account with, using or
alongside that account, if its terms prohibit it.** That is the single highest-risk
configuration in this entire domain, and it is also the most common.

### 1.4 The §1201 shift — the live frontier

**[VERSIONED, and this is the most important development for scrapers since hiQ.]**

**Reddit sued Perplexity AI and several data-collection providers in late 2025**, and the
central claim is **not** CFAA — it's **DMCA §1201**, alleging **circumvention of
technological protection measures including rate limits and anti-bot systems** to scrape
content for AI training.

**Why this matters enormously**: §1201 **targets the circumvention, not the publicness of
the data.** The public-data cases predate the AI training boom, and the new wave reframes
the question from *"was it public?"* to **"did you defeat a protection to get it, and what
did you do with it?"** — a question the hiQ line does not answer in your favour.

**[CONTESTED and unresolved.]** The case was pending as of early 2026. **But the strategic
implication is already actionable: deliberately defeating anti-bot measures now carries a
legal theory it didn't clearly carry before**, independent of whether the underlying data
was public. Similar circumvention and IP theories appear in creator suits over alleged
YouTube scraping for model training.

### 1.5 Copyright, databases, and personal data

**Copyright**: **facts are not copyrightable; creative expression is.** Extracting prices,
specifications, or statistics sits differently from reproducing articles, images, or long
creative excerpts. **The EU's text-and-data-mining exception is the main carveout — and it
is subject to a machine-readable opt-out** (§3.2). The **EU sui generis database right**
has no close US equivalent and protects substantial extraction from a database as such.

**Personal data is a separate regime that public availability does not exempt.**
**[DURABLE] This is the point most technically-minded scrapers miss**: GDPR applies to
personal data regardless of whether it was publicly posted, and it applies
**extraterritorially** to anyone processing EU residents' data wherever they're based.

**[VERSIONED] The Clearview AI line is the object lesson.** Clearview scraped billions of
facial images from public sites to build a biometric database, drawing **€30.5M from the
Dutch DPA (2024)** plus actions from the Italian Garante and CNIL, and **$75M+ in
cumulative fines across the US, UK, and EU.** The UK's **Upper Tribunal held Clearview's
processing was within UK GDPR scope** despite the company being wholly outside the UK,
and rejected the law-enforcement exemption for a private company — reinforcing
extraterritorial reach.

**⚠️ Note precisely what those cases turned on.** As one analysis puts it: **none of them
turned on whether the data was technically public.** They turned on **the absence of a
documented legal basis, the absence of transparency toward the people whose data was
collected**, and — for biometrics — the absence of any Article 9 exemption.

### 1.6 The AI-training layer

**[VERSIONED — the fastest-moving material in this document.]**

**EDPB Guidelines 03/2026 on web scraping in the context of generative AI** were adopted
at the Board's **July 2026 plenary** — **the first pan-EU framework addressing AI training
data collection directly**, confirming that **GDPR applies in full to personal data scraped
to train AI models, with no carve-out for AI.** Reported headline positions:
- **Consent is unlikely to be a valid legal basis** for scraping at this scale.
- **Legitimate interest survives only a documented three-part test**, assessed
  **per deployment**.
- **Data minimisation applies before scraping**, not after.
- **Sensitive data carries a near-prohibition.**
- ⚠️ **Once a model is trained, personal data cannot easily be deleted from it** — which
  **turns AI data governance into an upstream engineering problem you must solve before
  training, not after launch.**
- Applies both to organizations scraping directly **and to those acquiring pre-scraped
  datasets from third parties**, including data brokers.

Companion **anonymisation guidelines** set a three-criterion test. **Both were open for
public consultation until 30 October 2026 — they are draft guidance, not settled law**,
but they signal where enforcement is heading.

**EU AI Act**: in force since 1 August 2024, GPAI obligations from **2 August 2025**, with
**enforcement teeth from 2 August 2026** (GPAI fines up to **€15M or 3% of turnover**).
Two obligations land directly on data collection: **GPAI providers must publish a summary
of training data sources**, and must **operate a copyright policy respecting
machine-readable opt-outs.** **[DURABLE-ish implication] Machine-readable "don't mine me"
signals — robots.txt, TDM reservations — now carry legal weight for anyone training models
for the EU market**, which is a change in kind from their previous purely-voluntary status
(§3). The Act also **bans untargeted scraping of facial images** for facial-recognition
databases, while distinguishing targeted from untargeted collection.

### 1.7 The risk gradient

**[DURABLE] A usable mental model, lowest to highest risk:**
```
LOW    public factual data · logged-out · no personal data · rate-limited ·
       own use · robots.txt respected
  │
  │    public data incl. some personal data · documented legal basis · GDPR-compliant
  │    aggregate/derived output · commercial use
  │
  │    ⚠️ defeating anti-bot measures  ← the §1201 theory (§1.4)
  │    ⚠️ republishing creative content
  │    ⚠️ training models on it, especially with personal data (§1.6)
  ▼
HIGH   behind a login, against accepted terms · biometric or sensitive data ·
       bypassing authentication · volume causing operational harm
```

---
