---
id: skill-1-the-platform-landscape-775d8a4035
purpose: 1 the platform landscape
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-platforms-and-10-foot-ui/SKILL.md
requires: ["skill-0-routing-56841de476"]
links: ["skill-2-the-10-foot-ui-ba1b6789fc"]
---

## §1. The Platform Landscape

### 1.1 Who actually owns the living room

**[VERSIONED — and note that the numbers disagree wildly depending on what's being
measured.]** Three different, all-defensible framings:

- **US usage share** (Parks Associates, Streaming Video Tracker, April 2026, "device used
  most frequently to watch online video" in US broadband households): **Roku OS 28%,
  Samsung Tizen 23%**, with Amazon Fire TV, LG webOS, and VIZIO SmartCast mid-tier, and
  tvOS, consoles, and Android TV smaller.
- **US activated screens**: Roku OS around **38%**, with Google TV growing ~2.6%/year.
- **Global units shipped**: an entirely different ranking, where **Tizen and Android TV
  lead** because Samsung and the Android licensees ship the most TVs worldwide, and Roku
  barely registers outside North America.

**[DURABLE] Reconcile those before you plan.** *Installed base* ≠ *units shipped* ≠
*hours watched* ≠ *ad revenue*. Roku's US strength and near-absence in Europe is the
canonical trap for teams that read one number and built one app.

Rough scale anchors for 2026: **Android TV/Google TV crossed ~300M monthly active
devices** globally; **Roku passed ~100M streaming households**; **LG webOS is ~12%
overall but ~52% of the premium OLED tier**; and **smart-TV ownership is heading past
1.1 billion households**.

Parks Associates' framing is the one worth internalizing: *"Control of the platform layer
is central to competition in the connected TV market. Operating systems determine what
content consumers see, how services are positioned, and how advertising is delivered."*
A small number of OSes account for the majority of usage, **limiting visibility for
services without strong distribution partnerships** — which is a polite way of saying
discovery placement is negotiated, not earned.

### 1.2 The two structural shifts in progress

**[VERSIONED — both are live as of 2026 and both change build plans.]**

**Amazon is replacing Fire OS with Vega OS.** Vega is **Linux-based, built from the ground
up, and not Android** — it cannot natively run APKs. Apps are built with **React Native
0.72** ("React Native for Vega") or web via **Vega WebView**, packaged as **VPKG** rather
than APK. Timeline: first shipped on the **Fire TV Stick 4K Select (late 2025)**, then the
**Fire TV Stick HD (April 2026)**; Amazon's developer site states that **starting with the
4K Select, all future Fire TV Sticks run Vega**. Existing Fire OS devices are **not being
upgraded** and are supported with security updates through at least 2030 (or four years
from purchase).

What this means practically:
- **Porting is re-engineering, not recompiling** — new APIs, new packaging, and rewritten
  UI, focus management, and entitlement flows. React Native apps reuse the most.
- Amazon is **cloud-streaming selected apps** during the transition, with roughly nine
  months of free hosting, to buy publishers time to build native Vega versions.
- **Sideloading is gone** on Vega devices — Amazon Appstore only.
- **⚠️ You now support two Amazon platforms simultaneously**, indefinitely. That is a real
  and unwelcome addition to an already-fragmented matrix.

**Fox agreed to acquire Roku (announced April 2026, ~$22B cash-and-stock).** If it
completes, it shifts the strategic value of a TV OS further toward distribution and
advertising, and it will affect OS licensing and ad-supply negotiations. **Treat any
Roku commercial term as subject to change.**

### 1.3 The frozen-browser problem

**[PLATFORM — this is the single most under-anticipated constraint in TV development, and
it deserves its own section.]**

On Tizen and webOS your app is a web app running in the browser engine the TV shipped
with — **and that engine is never updated**. Samsung publishes the mapping, and it is
sobering:

| TV model year | Tizen | Web engine |
|---|---|---|
| **2026** | 10.0 | **Chromium M130** |
| 2025 | 9.0 | Chromium M120 |
| 2024 | 8.0 | Chromium M108 |
| 2023 | 7.0 | Chromium M94 |
| 2022 | 6.5 | Chromium M85 |
| 2021 | 6.0 | Chromium M76 |
| 2020 | 5.5 | Chromium M69 |
| 2019 | 5.0 | Chromium M63 |
| 2018 | 4.0 | Chromium M56 |
| 2017 | 3.0 | Chromium M47 |
| 2016 / 2015 | 2.4 / 2.3 | **WebKit** |

Read that table again: **a 2024 TV shipped with Chromium 108 while desktop Chrome was on
130.** A 2018 TV is on Chromium 56 — an engine from 2016. webOS has the same structure.

Consequences you must design around:
- **Your baseline is whatever the oldest model year you support shipped**, not "modern
  evergreen browsers." A team targeting 2019+ Samsungs is writing for **Chromium 63**.
- **Feature-detect, never version-sniff.** An API introduced in Chrome 110 works on 2025+
  sets and **fails silently** on everything older.
- **Transpile and polyfill aggressively**, and *test what your bundler actually emits* —
  a modern framework's default output targets browsers your fleet doesn't have.
- **⚠️ Teams routinely start with Next.js or a modern SPA framework and hit a wall**,
  because both platforms run considerably outdated Chromium. Budget for this in week one,
  not month four.
- **No webview embedding on Tizen** — the only way to embed external content is an
  `iframe`, which sites can refuse via frame-ancestors/X-Frame-Options.
- Old engines also mean **no security updates**: Chromium 56 and below are unsafe to run
  web content on at all.
- **[VERSIONED] Native binaries have their own cliff**: Samsung used **GCC 9.2.0 through
  the 2025 model year and moved to GCC 14.2.0 for 2026**, so any native library must be
  rebuilt for 2026 sets.

---
