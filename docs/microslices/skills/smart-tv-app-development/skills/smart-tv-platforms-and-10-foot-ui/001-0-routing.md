---
id: skill-0-routing-56841de476
purpose: 0 routing
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-platforms-and-10-foot-ui/SKILL.md
requires: []
links: ["skill-1-the-platform-landscape-775d8a4035"]
---

## §0. Routing

### 0.1 The platform matrix

**[PLATFORM/VERSIONED — the single most important table in this document.]**

| Platform | Language / model | UI framework | Notes |
|---|---|---|---|
| **Roku OS** | **BrightScript** (proprietary, BASIC-like, dynamically typed, single-threaded interpreter) | **SceneGraph** (XML scene graph) | **No browser engine. No HTML/CSS/JS.** A wholly separate discipline |
| **Samsung Tizen** | **HTML/CSS/JS web app** | Your own / any web framework | Runs in a **model-year-frozen Chromium**. See §1.3 — this is the defining constraint |
| **LG webOS** | **HTML/CSS/JS web app** | Your own / **Enact** (React-based) | Same frozen-engine problem as Tizen |
| **Android TV / Google TV** | **Kotlin/Java** (or Compose for TV) | Leanback / **Jetpack Compose for TV** | Real native media stack (**Media3/ExoPlayer**), Widevine L1 |
| **Amazon Fire OS** | Android (AOSP fork) — Kotlin/Java | Leanback/Compose | ⚠️ Being **replaced** — see below |
| **Amazon Vega OS** | **React Native 0.72** or web (**Vega WebView**) | React Native for Vega | ⚠️ **Linux-based, NOT Android. APKs do not run.** New packaging (VPKG) |
| **Apple tvOS** | **Swift** (SwiftUI/UIKit) or **TVML/TVMLKit** | SwiftUI for TV | The most consistent hardware; smallest US share |
| **VIDAA** (Hisense), **whaleOS**, **webOS Hub**, **VIZIO SmartCast**, **Xumo**, **Titan OS** | Mostly web apps | varies | The long tail. Each is its own certification and QA burden |

**[DURABLE] There are three programming models, not eight**: **web apps** (Tizen, webOS,
VIDAA, most of the long tail, Vega WebView), **Android/Kotlin** (Android TV, Google TV,
Fire OS), and **proprietary** (Roku BrightScript, tvOS Swift, Vega React Native). Your
cross-platform strategy (§13 → `smart-tv-monetization-certification-and-operations`) is really a decision about how many of those three you're
willing to staff.

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| Which platforms to target, market reality | §1 |
| The 10-foot UI, safe areas, typography, layout | §2 |
| Focus, spatial navigation, remote input | §3 |
| Video playback, HLS/DASH, ABR, players | §4 → `smart-tv-playback-drm-and-performance` |
| DRM and content protection | §5 → `smart-tv-playback-drm-and-performance` |
| Performance and memory on TV silicon | §6 → `smart-tv-playback-drm-and-performance` |
| App lifecycle, resume, deep linking, discovery feeds | §7 → `smart-tv-playback-drm-and-performance` |
| Monetization: subs, IAP, AVOD/FAST | §8 → `smart-tv-monetization-certification-and-operations` |
| CTV advertising: VAST, SSAI, ad pods, measurement | §9 → `smart-tv-monetization-certification-and-operations` |
| Certification and store submission | §10 → `smart-tv-monetization-certification-and-operations` |
| Testing on real devices | §11 → `smart-tv-monetization-certification-and-operations` |
| Analytics and QoE | §12 → `smart-tv-monetization-certification-and-operations` |
| Cross-platform strategy and frameworks | §13 → `smart-tv-monetization-certification-and-operations` |
| Accessibility, privacy, ACR, regulation | §14 → `smart-tv-monetization-certification-and-operations` |
| "Don't do this" | §15 → `smart-tv-reference` |
| "Which approach is better?" | §16 → `smart-tv-reference` (contested) |
| "Is this still current?" | §17 → `smart-tv-reference` |
| Docs, tools, people | §18 → `smart-tv-reference` |

---
