---
id: skill-0-routing-f4a0cdc3de
purpose: 0 routing
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-engine-architecture-and-networking/SKILL.md
requires: []
links: ["skill-1-the-engine-landscape-9fffda8f79"]
---

## §0. Routing

### 0.1 The anatomy

```
┌────────────────────────────────────────────────────────────────────────┐
│ BROWSER PROCESS (privileged)                                           │
│   UI · tab/window management · profile & storage · permissions         │
│   navigation & session history · extension host · IPC broker           │
└───────┬─────────────────┬──────────────────┬───────────────────────────┘
        │ IPC             │ IPC              │ IPC
┌───────▼──────┐  ┌───────▼────────┐  ┌──────▼───────┐  ┌───────────────┐
│ RENDERER     │  │ NETWORK        │  │ GPU          │  │ UTILITY       │
│ (sandboxed,  │  │ SERVICE        │  │ PROCESS      │  │ (audio, media │
│  one per     │  │ HTTP/TLS/cache │  │ raster, draw │  │  codecs, data │
│  site)       │  │ cookies, DNS   │  │ compositing  │  │  decoders)    │
│              │  └────────────────┘  └──────────────┘  └───────────────┘
│  ┌─────────────────────────────────────────────┐
│  │ HTML parser → DOM                            │
│  │ CSS parser → CSSOM → style resolution        │
│  │ LAYOUT → PAINT (display lists) → COMMIT      │
│  │ JS engine (heap, JIT) · event loop            │
│  │ compositor thread (scroll, transform anims)   │
│  └─────────────────────────────────────────────┘
└──────────────┘
```

**[DURABLE] The single most important architectural fact: the renderer is assumed to be
compromised.** It is sandboxed, it has no filesystem or network access of its own, and
every privileged operation goes through an IPC message that the browser process must
independently validate. **Never trust a renderer's claim about its own origin** — that is
the whole ballgame (§8.4 → `browser-security-and-privacy`).

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| Engine landscape, who builds what, why it matters | §1 |
| Process model, IPC, sandboxing, site isolation | §2 |
| Networking, HTTP, TLS, caching, DNS | §3 |
| HTML parsing, DOM, error recovery | §4 → `browser-rendering-pipeline` |
| CSS: cascade, selectors, style resolution, invalidation | §5 → `browser-rendering-pipeline` |
| Layout algorithms and fragmentation | §6.1 → `browser-rendering-pipeline` |
| Paint, raster, compositing, GPU | §6.2 → `browser-rendering-pipeline`–6.4 |
| JS engine integration, bindings, GC interaction | §7 → `browser-rendering-pipeline` |
| Event loop, scheduling, rendering lifecycle | §7.3 → `browser-rendering-pipeline` |
| Security: SOP, CORS, CSP, XSS, Spectre, memory safety | §8 → `browser-security-and-privacy` |
| Privacy, tracking, cookies, fingerprinting | §9 → `browser-security-and-privacy` |
| Extensions | §10 → `browser-extensions-platform-and-standards` |
| Storage, media, devices, capability APIs | §11 → `browser-extensions-platform-and-standards` |
| Accessibility | §12 → `browser-extensions-platform-and-standards` |
| Standards, interop, compatibility | §13 → `browser-extensions-platform-and-standards` |
| Testing, telemetry, shipping | §14 → `browser-extensions-platform-and-standards` |
| "Don't do this" | §15 → `browser-development-reference` |
| "Which approach is better?" | §16 → `browser-development-reference` (contested) |
| "Is this still current?" | §17 → `browser-development-reference` |
| Books, docs, people | §18 → `browser-development-reference` |

---
