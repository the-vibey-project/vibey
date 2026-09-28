---
id: skill-13-standards-and-interop-0cb5fe5d58
purpose: 13 standards and interop
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-extensions-platform-and-standards/SKILL.md
requires: ["skill-12-accessibility-5487f3b0ac"]
links: ["skill-14-testing-telemetry-and-shipping-9a178cbf61"]
---

## §13. Standards and Interop

### 13.1 How the web is specified

**WHATWG** maintains **living standards** (HTML, DOM, Fetch, URL, Streams) — continuously
updated, no versions. **W3C** handles CSS (per-module levels), WebRTC, WebAuthn, and
accessibility. **TC39** owns JavaScript, with a staged proposal process. **IETF** owns HTTP,
TLS, QUIC.

**[DURABLE] The web's specs are unusual in being written to describe what implementations
must do down to error cases** (§4.1 → `browser-rendering-pipeline`). That's a response to a specific historical failure —
under-specified standards produced incompatible engines, and the compatibility debt is
permanent.

**Web Platform Tests (WPT)** is the shared, cross-vendor conformance suite and the
mechanism that makes "interoperable" measurable rather than aspirational.

### 13.2 Interop and Baseline

**[VERSIONED]** The **Interop** project — Apple, Google, Igalia, Microsoft, and Mozilla —
picks a shared set of focus areas each year, measured by WPT pass rate, and works them
together. **2026 is the fifth year.**

The 2025 results are the strongest argument for the process: **the overall Interop score
across all four browsers went from 25 to 95, and Firefox's own score went from 46 to 99.**
Features that reached cross-browser availability through it include Same-Document View
Transitions, CSS Anchor Positioning, the Navigation API, `@scope`, and URLPattern.

**Interop 2026** focus areas include cross-document view transitions, `blocking="render"`,
`<link rel="expect">`, `:active-view-transition-type()`, the CSS `attr()` function,
`contrast-color()`, custom highlights, scroll-driven animations, scroll snap, `shape()`,
the Navigation API's `precommitHandler`, scoped `CustomElementRegistry`, fetch streaming
request bodies, plus a continuing **mobile testing** investigation.

**Baseline** is the companion developer-facing signal: *Newly available* (works in the
current version of all major engines) vs. *Widely available* (30 months later). Recent
Baseline arrivals include **Trusted Types**, the CSS `shape()` function, **zstd** content
encoding, and the Navigation API.

**[DURABLE] For an engine implementer, WPT + Interop + Baseline is the closest thing to an
objective definition of "done."** Ship a feature, pass the tests, watch the dashboard.

---
