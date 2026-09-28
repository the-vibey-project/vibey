---
id: skill-18-the-canon-0a92840fb3
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-ea6b93725b"]
links: ["skill-19-quick-reference-4a63153f92"]
---

## §18. The Canon

### 18.1 Primary sources — and here, they're nearly all you have

**[DURABLE] Unlike web or mobile, TV development has almost no independent literature.
The vendor docs are the field.** Read them directly and read them annually.

- **Roku**: `developer.roku.com` — the SceneGraph course, **certification docs**, the
  BrightScript reference, and the **`rokudev` GitHub org**, especially
  **`scenegraph-master-sample`** (a certification-compliant reference channel you can use
  as a template) and `samples`. The **Roku developer blog's Certification category** is
  where requirement changes are announced — subscribe to it.
- **Samsung**: `developer.samsung.com/smarttv` — and specifically the **Web Engine
  Specifications** page, which carries the model-year/Chromium/feature-support matrix in
  §1.3 → `smart-tv-platforms-and-10-foot-ui` and §17. This single page will save you more time than anything else in this list.
  Also **General Specifications** for HLS/DASH tag support and the toolchain notes.
- **LG**: `webostv.developer.lge.com` — webOS TV docs, the **Enact** framework, and the
  Simulator/CLI tooling.
- **Google**: `developer.android.com/tv` — Leanback, **Compose for TV**, **Media3/
  ExoPlayer**, Watch Next and channel APIs, and the Android TV quality guidelines.
- **Amazon**: `developer.amazon.com` — Fire TV docs and, critically, the **Vega Developer
  Tools** getting-started guides, VS Code extension, and CLI.
- **Apple**: the **tvOS Human Interface Guidelines** (the best-written TV design doc from
  any vendor, and worth reading even if you never ship tvOS) plus TVMLKit and SwiftUI docs.
- **IAB Tech Lab**: the **CTV Programmatic Guide**, VAST 4.x, **Universal Ad ID**, and
  **OM SDK** specs — the standards layer under §9 → `smart-tv-monetization-certification-and-operations`.
- **Standards bodies**: HbbTV (Europe), ATSC 3.0 (US broadcast), DASH-IF, and CTA
  specifications, depending on your market.

### 18.2 Practitioner sources

Vendor-neutral analysis lives with the OTT integrators and the measurement firms rather
than in books: **Conviva** (State of Streaming — the QoE benchmark data),
**Parks Associates** and **Nielsen** (share and viewing), **Bitmovin's annual Video
Developer Report**, **Accedo**, **Float Left**, **Fora Soft**, and **Lightcast** (platform
notes and build-cost writeups — commercially motivated, but the technical detail is real
and hard to find elsewhere). **AFTVnews** is the best source on Fire TV/Vega specifics.
**Dolby OptiView**, **Bitmovin**, **JW Player**, **THEO**, and **Shaka Player** docs are
the practical references for the player and DRM layers.

**⚠️ Almost every source in this domain is a vendor or an integrator selling something.**
Cross-read, and treat platform-share numbers especially carefully (§1.1 → `smart-tv-platforms-and-10-foot-ui`).

---
