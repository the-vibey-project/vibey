---
id: skill-17-currency-snapshot-verified-august-2026-b66e4fe7f9
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-development-reference/SKILL.md
requires: ["skill-16-contested-questions-498f11528f"]
links: ["skill-18-the-canon-8ee59aa692"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Engine share** | Blink **~81%**, WebKit **~14%**, Gecko **~3%** (desktop+mobile+tablet, ~May 2026). Remaining ~1%: Goanna, Flow, Servo, Ladybird | Low |
| **Ladybird** | Independent C++ engine (LibWeb/LibJS), non-profit-backed, ~7–10 FT engineers, no code from other engines, no search-deal funding. **Alpha targeted 2026 (Linux/macOS), beta 2027, stable 2028.** Roadmap (not shipped): Rust style/layout, sandboxing, GPU isolation, Wasm GC | **High** |
| **Servo** | Rust, embeddable, parallel; under **Linux Foundation Europe**; components (Stylo, WebRender) shipped in Firefox. Positioned as a webview, not a browser | Medium |
| **Third-party cookies** | ⚠️ **Not being deprecated in Chrome.** 22 Jul 2024 first reversal; **22 Apr 2025** confirmed current approach with **no standalone prompt**. Safari/Firefox/Brave still block by default (~17–20% of traffic) | Medium |
| **Privacy Sandbox** | ⚠️ **Mostly shut down.** On **17 Oct 2025** Google retired most APIs (Topics, Protected Audience, Attribution Reporting, Private Aggregation, IP Protection, Related Website Sets) citing low adoption. Deprecated in **Chrome 144 (Jan 2026)**, full removal targeted **Chrome 150 (Jul 2026)**. Continuing focus: privacy-preserving measurement, FedCM, CHIPS | Medium |
| **Manifest V2** | ⚠️ **Essentially dead in Chrome.** By **June 2026** Chromium removed `kExtensionManifestV2Disabled`; Chrome 150/151 remove the last overrides. Edge and Opera follow. **Full uBlock Origin unavailable on Chrome** (uBO Lite only); available on **Firefox and Brave**. Firefox retains **both MV2 and MV3 with blocking `webRequest`** | Medium |
| **Interop** | **Interop 2026** is the fifth year (Apple, Google, Igalia, Microsoft, Mozilla). **Interop 2025 finished with an overall score of 95 (from 25); Firefox went 46 → 99.** 2026 areas: cross-document view transitions, `attr()`, `contrast-color()`, custom highlights, scroll-driven animations, scroll snap, `shape()`, Navigation API `precommitHandler`, scoped `CustomElementRegistry`, fetch streaming bodies, mobile testing | Medium |
| **Baseline** | **Trusted Types** reached Baseline **February 2026**; also `shape()`, **zstd**, Navigation API. *Newly available* = all major engines; *Widely available* = +30 months | Medium |
| **Chrome memory safety** | MiraclePtr expanding to **Skia, ANGLE, Dawn, C++ iterators, `std::` containers**; **MiracleObject on the GPU main thread targeting ~90% of UAFs there**; "spanification" against OOB; UBSan `-fsanitize=return` default in release; **PartitionAlloc in Skia**; **`ChildProcessSecurityPolicy` being migrated to Rust** (Canary experiment) plus an initial **Rust Mojo client**; exploring an **HTML/CSS/TypeScript top-level UI** | **High** |
| **AI in browser security** | Google's early-2026 Gemini-based agent harness found a **sandbox escape that had survived >13 years** in Chrome's codebase | **High** |
| **Site Isolation ceiling** | Chromium docs state plainly that sandboxing and site isolation are reaching their limits — processes are not cheap, especially on Android where extra processes cause background activities to be killed more often | Low |

**Goes stale fastest:** Chrome's memory-safety program and AI-assisted vuln finding;
Ladybird's alpha timeline; MV2 removal specifics; Privacy Sandbox removal milestones.
**Essentially never stale:** §2.1 → `browser-engine-architecture-and-networking`–2.4 (process model and IPC discipline), §4.1 → `browser-rendering-pipeline` (HTML
parsing), §5.1 → `browser-rendering-pipeline`–5.2 (cascade and selector matching), §6.1 → `browser-rendering-pipeline`–6.2 (pipeline and immutability),
§7.3 → `browser-rendering-pipeline` (event loop), §8.1 → `browser-security-and-privacy`–8.4 (security model), §15 (anti-patterns).

---
