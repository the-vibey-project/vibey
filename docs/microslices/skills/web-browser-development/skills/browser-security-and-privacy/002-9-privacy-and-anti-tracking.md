---
id: skill-9-privacy-and-anti-tracking-5d20a30fa6
purpose: 9 privacy and anti tracking
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-security-and-privacy/SKILL.md
requires: ["skill-8-the-security-model-77b0564f7a"]
links: []
---

## §9. Privacy and Anti-Tracking

### 9.1 The third-party cookie saga — what actually happened

**[VERSIONED, and the folklore is badly out of date. This is worth getting exactly right.]**

Timeline:
- **January 2020** — Google announces intent to phase out third-party cookies in Chrome
  "within two years," alongside the **Privacy Sandbox** initiative. Deadlines slip from
  2022 → 2023 → 2024 → 2025.
- **22 July 2024** — Google announces it will **not** phase out third-party cookies,
  proposing a user-choice prompt instead. UK **CMA** competition concerns and **ICO**
  disappointment are both part of the record; the CMA had been formally engaged since 2022.
- **22 April 2025** — Google confirms it is **maintaining the current approach** and will
  **not roll out a standalone opt-out prompt**. Default behaviour — third-party cookies
  allowed — unchanged.
- **17 October 2025** — Google **retires most Privacy Sandbox APIs**, citing low adoption:
  Topics, Protected Audience, Attribution Reporting, Private Aggregation, IP Protection,
  Related Website Sets and others. Deprecation lands in **Chrome 144 (January 2026)** with
  full removal targeted for **Chrome 150 (July 2026)**. Google's stated continuing focus is
  privacy-preserving measurement plus **FedCM** and **CHIPS**.

**[DURABLE] The lesson for an engine implementer is not about advertising.** It's that
**a browser vendor whose revenue depends on advertising faces a structural conflict when
changing tracking defaults**, and that regulators now treat browser defaults as competition
policy. Note also the asymmetry that remains: **Safari, Firefox, and Brave still block
third-party cookies by default**, so roughly 17–20% of global traffic is "cookieless"
regardless of Chrome — the fragmentation didn't go away, it just stopped being Chrome-led.

### 9.2 What browsers actually do now

- **Third-party cookie blocking** (Safari ITP since 2020, Firefox ETP, Brave) vs.
  Chrome's user-choice model.
- **State partitioning / "total cookie protection"** — partitioning *all* storage
  (cookies, localStorage, IndexedDB, cache, service workers) by top-level site, so a
  third party gets a separate jar per embedding site. **This is the most important
  anti-tracking mechanism actually deployed**, because it defeats cross-site state without
  breaking same-site embedding. **CHIPS** (`Partitioned` cookies) is the opt-in
  standardized form.
- **Cache partitioning** — closing the shared-cache timing side channel.
- **Referrer trimming**, **`Referrer-Policy`** defaults.
- **Fingerprinting defences** — the hard problem (§9.3).
- **Bounce-tracking mitigation**, link decoration stripping, **Global Privacy Control**.

### 9.3 Fingerprinting

**[CONTESTED, and genuinely unresolved.]** Canvas, WebGL, fonts, audio, screen metrics,
timing, hardware concurrency, and the sheer combination of exposed APIs form an identifier
without any storage at all.

Two philosophies:
- **Randomization** (Brave): add per-session, per-site noise so the fingerprint is unstable.
- **Uniformity** (Tor Browser): make every user look identical, at real functionality cost.
- Chrome's position historically leaned on "privacy budget"-style ideas that have not
  broadly shipped.

**The honest assessment: nobody has solved this.** Every new capability API adds entropy,
which is why capability APIs (§11 → `browser-extensions-platform-and-standards`) are permanently in tension with privacy, and why "just
ship the feature" is never the whole answer.
