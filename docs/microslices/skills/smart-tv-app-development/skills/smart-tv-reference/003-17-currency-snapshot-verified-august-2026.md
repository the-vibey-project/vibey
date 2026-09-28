---
id: skill-17-currency-snapshot-verified-august-2026-ea6b93725b
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-reference/SKILL.md
requires: ["skill-16-contested-questions-655fd56384"]
links: ["skill-18-the-canon-0a92840fb3"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **US platform share** | Parks Associates (Apr 2026, most-used device for online video, US broadband households): **Roku OS 28%, Samsung Tizen 23%**; Fire TV, webOS, SmartCast mid-tier; tvOS, consoles, Android TV smaller. Other measures put Roku at ~38% of activated screens. **Global shipments rank differently** — Tizen and Android TV lead worldwide | Medium |
| **Scale anchors** | Android TV/Google TV **~300M monthly active devices**; Roku **~100M streaming households**; webOS ~12% overall but **~52% of premium OLED**; smart TV ownership heading past **1.1B households** | Medium |
| **Amazon Vega OS** | ⚠️ **Linux-based, not Android — APKs do not run.** React Native 0.72 or Vega WebView; **VPKG** packaging. Shipped on Fire TV Stick 4K Select (2025) and Fire TV Stick HD (Apr 2026); Amazon states **all future Fire TV Sticks run Vega**. Existing Fire OS devices **not upgraded**, supported through at least 2030. **No sideloading.** Selected apps cloud-streamed with ~9 months free hosting during transition | **High** |
| **Fox–Roku** | ⚠️ **April 2026: Fox announced an agreement to acquire Roku for ~$22B** (cash and stock). Expected to affect OS licensing and ad-supply terms | **High** |
| **Samsung Tizen web engine** | **2026: Tizen 10.0 / Chromium M130** · 2025: 9.0/M120 · 2024: 8.0/**M108** · 2023: 7.0/M94 · 2022: 6.5/M85 · 2021: 6.0/M76 · 2020: 5.5/M69 · 2019: 5.0/M63 · 2018: 4.0/**M56** · 2017: 3.0/M47 · 2016 and earlier: WebKit. **Never updated after ship** | Low (annual) |
| **Samsung native toolchain** | ⚠️ **GCC 9.2.0 through the 2025 model year; GCC 14.2.0 from 2026.** Native binaries must be rebuilt for 2026 sets | Low |
| **LG webOS** | **webOS 26** introduced Jan 2026 with AI assistant integrations (**Microsoft Copilot** and **Google Gemini**). Enact (React-based) remains the LG-blessed framework | Medium |
| **Roku certification** | ⚠️ **Spring 2026 update: Instant Resume required by 1 October 2026** for qualifying US Streaming Store apps. **`roAppMemoryMonitor`** usage required to pass certification testing. Static Analysis must pass to publish; App Behavior Analysis for free/ad-based apps. **Direct Publisher has been wound down** — no-code publishing now goes through third-party OTT platforms | Medium |
| **Roku OS** | 15.0 (Oct 2025). Linux-based; BrightScript + SceneGraph; ARM Cortex-A53/A55/A35 and some MIPS | Medium |
| **CTV ad specs** | **VAST 4.x required** for full CTV format and measurement support. **SSAI is the default.** Loudness **−23 LUFS (EBU R128)** streaming/SSAI, **−24 LKFS (ATSC A/85)** US broadcast. Creative typically ≤200 MB (≤150 MB preferred). **Universal Ad ID** and **OM SDK** are the IAB Tech Lab interop answers | Medium |
| **CTV market** | US digital video ad spend projected **>$80B in 2026**, passing **60% of total TV/video spend** for the first time. Streaming hit **~48.6% of US TV watch-time (Nielsen, May 2026)** | Annual |
| **Privacy/ACR regulation** | **US Cyber Trust Mark** programme and **Kentucky HB 692** (ACR data handling) named as shaping 2026 privacy-by-design roadmaps. **Caption discovery** is a 2026 US accessibility compliance milestone | **High** |

**Goes stale fastest:** the Vega transition; the Fox–Roku deal; Roku certification
requirements; ACR/privacy legislation; ad-market figures. **Essentially never stale:**
§2 → `smart-tv-platforms-and-10-foot-ui` (10-foot UI), §3 → `smart-tv-platforms-and-10-foot-ui` (focus and input), §4.3 → `smart-tv-playback-drm-and-performance` (playback metrics), §5.1 → `smart-tv-playback-drm-and-performance`'s `cenc`/`cbcs` trap,
§6.2 → `smart-tv-playback-drm-and-performance` (performance techniques), §15 (anti-patterns).

---
