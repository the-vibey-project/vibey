---
id: skill-7-cross-platform-frameworks-137f615b20
purpose: 7 cross platform frameworks
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-cross-platform-and-architecture/SKILL.md
requires: []
links: ["skill-8-application-architecture-and-patterns-1b88ff0dc8"]
---

## §7. Cross-Platform Frameworks

### 7.1 The comparison table

| Framework | Language | Rendering | Bundle (typical) | Idle RAM (typical) | Native feel | Maturity |
|---|---|---|---|---|---|---|
| **Electron** | JS/TS + Node | Bundled Chromium | 80–200 MB | 150–300 MB | Low (unless heavily worked) | Very high (13 yrs) |
| **Tauri 2** | JS/TS + Rust | **OS WebView** | 2–10 MB | 30–50 MB | Medium | High, younger |
| **Wails 3** | JS/TS + Go | OS WebView | small | low | Medium | Medium |
| **Neutralino** | JS/TS + thin C++ | OS WebView | 1–5 MB | very low | Low | Low |
| **Qt 6** | C++ / Python / QML | Own (raster/RHI) | 20–60 MB | 40–80 MB | High (Widgets) | Very high (31 yrs) |
| **Flutter** | Dart | Own (Impeller/Skia) | 20–50 MB | 60–120 MB | Low (identical everywhere by design) | High on mobile, medium on desktop |
| **Avalonia** | C#/XAML | Own (Skia → Impeller in progress) | ~40 MB + runtime | medium | Medium (drawn, WPF-like) | High for desktop |
| **.NET MAUI** | C#/XAML | Native controls per platform | — | — | Medium | Mobile-first; **no first-party Linux** |
| **Compose Multiplatform** | Kotlin | Own (Skia) | JVM-sized | higher | Low-Medium | Growing fast |
| **Slint** | Rust/C++/JS + DSL | Own | small | low | Medium | Medium; embedded-focused |
| **egui / iced / Xilem / GPUI** | Rust | Own | small | low | Low | Varies; see §7.4 |

*(Figures are representative ranges from published 2026 comparisons, not measurements of
your app. **Benchmark your own workload** — this is the one place vendor numbers are least
trustworthy.)*

### 7.2 Electron vs Tauri — the argument everyone is having

**[CONTESTED], and the numbers are real but not the whole story.**

**Case for Electron:**
- **Rendering consistency.** It ships its own Chromium, so CSS, WebGL, WebRTC, service
  workers, and codecs behave identically on every OS. For a visually complex or
  media-heavy app this eliminates an entire cross-platform testing burden.
- **Thirteen years of ecosystem**: `electron-builder`, `electron-updater`, code-signing
  recipes, crash reporting, native modules, Stack Overflow answers for every failure mode.
- **Proven at the top end**: VS Code, Slack, Discord, Notion, Postman, 1Password, Obsidian,
  Figma desktop. These are not accidents; they're evidence the trade-offs are survivable
  at billion-user scale.
- Bundle size rarely blocks a *desktop* install the way it would on mobile.

**Case for Tauri 2:**
- **Order-of-magnitude smaller bundles and ~4–5× lower idle memory**, because it uses the
  OS WebView (WKWebView on macOS, WebKitGTK on Linux, WebView2 on Windows) plus a Rust
  backend with no bundled runtime.
- **Capability-based permission model** — you declare exactly which commands the frontend
  may invoke. This is materially easier to defend in a SOC 2 / HIPAA audit than "Node is
  available in the renderer, we promise we turned it off."
- Smaller attack surface; memory-safe backend.
- **Tauri 2 (stable) added iOS and Android**, making one codebase span desktop and mobile.

**Case against Tauri (the honest knocks):**
- **WebView heterogeneity is the cost you pay for the small bundle.** WebKitGTK on Linux
  is meaningfully behind Chromium; you will hit "works in Chrome, broken in the Linux
  build" bugs. Your testing matrix expands even as your bundle shrinks.
- Native integrations require Rust. If nobody on the team writes Rust, "we'll just add a
  small native command" is not small.
- Fewer battle scars at very large scale.

**Migration reality**: porting a mid-size Electron app is commonly reported at ~2–3 months
— you must reimplement every Node native integration in Rust, rework IPC, and chase
WebView rendering differences. Do it when bundle size or memory is causing *actual user
pain*, not on principle.

**Also in this space**: **Wails 3** (Go backend, clean DX, performance claims still mostly
vendor-reported), and **`deno desktop`** (shipped in Deno 2.9, June 2026) — best ergonomics
for porting an existing web app, but explicitly experimental, and Deno's own docs concede
Tauri produces far smaller apps.

### 7.3 If you go the web-shell route: the security baseline

```js
// main.js — the settings that separate a safe Electron app from a browser
// with filesystem access. These are non-negotiable.
const win = new BrowserWindow({
  webPreferences: {
    contextIsolation: true,       // MUST be true (default since Electron 12)
    nodeIntegration: false,       // MUST be false
    sandbox: true,                // renderer in an OS sandbox
    webSecurity: true,            // never disable to "fix" CORS
    preload: path.join(__dirname, 'preload.js'),
  }
});

// preload.js — expose a MINIMAL, typed, validated surface. Never expose ipcRenderer.
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('api', {
  // Good: one narrow, named operation
  readConfig: () => ipcRenderer.invoke('config:read'),
  // BAD (do not do this): send: (ch, ...a) => ipcRenderer.send(ch, ...a)
});

// main process — validate EVERY argument. The renderer is untrusted.
ipcMain.handle('config:read', async (event) => {
  if (!isTrustedSender(event.senderFrame)) throw new Error('untrusted');
  return await loadConfigFromKnownPath();   // never a caller-supplied path
});
```
Plus: a strict **Content-Security-Policy**; block `will-navigate` and
`setWindowOpenHandler` to external origins; never `shell.openExternal()` a URL that came
from remote content; **keep Electron current** (you inherit every Chromium CVE, and old
Electron versions are a standing supply-chain liability).

Tauri's equivalent discipline: keep the capability/permission JSON tight, validate command
arguments in Rust, and don't enable `withGlobalTauri` in production.

### 7.4 Rust GUI — the honest 2026 assessment

The ecosystem is real but **fragmented, and every option is a compromise.**

| Library | Model | Best for | Weakness |
|---|---|---|---|
| **egui** (eframe) | Immediate mode | Tools, debug UIs, fastest zero→window | Non-native look; no retained accessibility model; re-renders continuously |
| **iced** | Elm/functional | Structured apps; more native feel than egui | Documentation gaps; ecosystem thinner |
| **Slint** | Declarative DSL | Polished product UI, embedded + desktop; commercial licensing available | DSL is another language; smaller community |
| **Dioxus** | React-like | Web devs; can render via WebView or natively | WebView path inherits WebView trade-offs |
| **Xilem** | Data-first, from the Druid team | Aligned with Rust's architecture; the "future" bet | Still maturing |
| **GPUI** | GPU-first, from Zed | Extreme performance, custom rendering | Effectively Zed's framework; limited outside it |
| **gtk4-rs / cxx-qt** | Bindings | You want a *real* mature toolkit with Rust | You're using GTK/Qt, with binding friction |
| **wxDragon / fltk-rs** | Bindings to native | **Genuinely native controls → free screen-reader accessibility** | Older toolkits, dated aesthetics |

**[CONTESTED] Is Rust GUI production-ready?** Advocates point to shipping apps and rapid
improvement. Skeptics point to a widely-circulated 2026 write-up in which a developer
benchmarked egui, iced, Slint, and GTK for a data-heavy table application (search, filter,
sort, inline edit), hit walls in each, and shipped Electron for the UI with Rust for the
core. Both accounts are honest. **The reliable synthesis:** Rust GUI is ready for tools,
utilities, and apps where you control the design; it is not yet a low-risk choice for
dense, data-grid-heavy business applications, and **accessibility is the weakest link**
across every self-drawn Rust toolkit.

---
