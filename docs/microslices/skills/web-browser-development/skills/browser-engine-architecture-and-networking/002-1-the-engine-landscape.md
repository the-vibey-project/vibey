---
id: skill-1-the-engine-landscape-9fffda8f79
purpose: 1 the engine landscape
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-engine-architecture-and-networking/SKILL.md
requires: ["skill-0-routing-f4a0cdc3de"]
links: ["skill-2-process-model-ipc-and-sandboxing-d1fb104f6f"]
---

## §1. The Engine Landscape

### 1.1 Who actually renders the web

**[VERSIONED — as of 2026, three engines carry essentially all of it:]**

| Engine | Share (desktop+mobile+tablet, ~May 2026) | Ships in |
|---|---|---|
| **Blink** (Chromium) | **~81%** | Chrome, Edge, Brave, Arc, Opera, Vivaldi, Samsung Internet, and nearly every Electron app |
| **WebKit** (Apple) | **~14%** | Safari — and, **outside the EU**, *every* iOS browser, because the App Store mandated WebKit (Chrome/Firefox/Edge on iOS are WebKit wrappers) |
| **Gecko** (Mozilla) | **~3%** | Firefox and derivatives. The last major engine that is neither Chromium nor Apple |

That's ~99%. The remaining ~1% is Pale Moon's Goanna, Ekioh's commercial GPU-accelerated
Flow, and the two ground-up rewrites below.

**The two new engines, and their honest status [VERSIONED]:**
- **Servo** — originated at Mozilla as a Rust, parallel, embeddable engine co-developed
  with Rust itself (2012–2020); donated to the Linux Foundation, now under **Linux
  Foundation Europe**. Modular; several components (Stylo, WebRender) were upstreamed into
  Firefox and are in production there. Positioned as an **embeddable webview**, not a
  browser.
- **Ladybird** — Andreas Kling's independent C++ engine (**LibWeb** + **LibJS**), spun out
  of SerenityOS, backed by the non-profit Ladybird Browser Initiative (incorporated 2024),
  funded by private sponsorship including GitHub and Shopify founders and Cloudflare, with
  roughly 7–10 full-time engineers. **No code from Blink, WebKit, or Gecko.** Explicit
  policy of never taking search-default money. **First Alpha targeted 2026 for Linux and
  macOS**, aimed at developers and early adopters; **beta expected 2027, general stable
  2028.** Roadmap items include moving style and layout to Rust, sandboxing, GPU isolation,
  and WebAssembly GC — note that those are *roadmap*, not shipped.

**[DURABLE] Why the count matters more than the market share.** With one engine at 81%,
"works in Chrome" becomes the de facto standard regardless of what the spec says, and a
single vendor's product decisions become web-wide policy. Every argument in §9 → `browser-security-and-privacy`, §10 → `browser-extensions-platform-and-standards`, and
§13 → `browser-extensions-platform-and-standards` is downstream of this.

### 1.2 What it costs to build one

**[DURABLE] A browser engine is one of the largest artifacts in commercial software** —
tens of millions of lines, decades of accumulated compatibility behaviour, and a security
surface that attracts state-level attackers. The realistic assessment:
- **Nobody has built a competitive from-scratch engine in twenty years** and shipped it to
  general users. Ladybird's 2026-alpha/2028-stable timeline with ~10 full-time engineers is
  the current experiment in whether that's still possible.
- The hard part is **not** the parts that are fun (parser, layout algorithms). It's the
  long tail: compatibility with two decades of quirks, media codecs and DRM, accessibility,
  the security architecture, and the sheer surface area of the platform.
- **Forking is the rational choice and is why the landscape looks like it does.** Every
  "new browser" of the last decade is a Chromium shell with different UI and policy.

### 1.3 What a browser is besides an engine

Product surface that is genuinely half the work: profiles and sync, password and payment
management, downloads, bookmarks and history, autofill, the update mechanism (a
**security-critical** always-on channel), enterprise policy, crash reporting and telemetry,
DevTools, and the extension platform.

---
