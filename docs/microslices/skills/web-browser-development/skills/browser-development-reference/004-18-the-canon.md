---
id: skill-18-the-canon-8ee59aa692
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-development-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-b66e4fe7f9"]
links: ["skill-19-quick-reference-184e7caa88"]
---

## §18. The Canon

### 18.1 Primary sources — overwhelmingly the best material

- **The specifications themselves**, and they are unusually readable:
  **html.spec.whatwg.org** (the parsing algorithm in §4.1 → `browser-rendering-pipeline` is worth reading in full),
  **dom.spec.whatwg.org**, **fetch.spec.whatwg.org**, **url.spec.whatwg.org**, the
  **CSS specs** at `drafts.csswg.org`, and **HTML Standard §"event loops."**
- **Chromium documentation** — `chromium.org` and `chromium.googlesource.com/chromium/src/+/main/docs/`.
  Specifically: the **Site Isolation design doc**, `process_model_and_site_isolation.md`,
  the **memory safety** page (unusually honest about limits), and the **Chrome Security
  quarterly updates**, which are the single best running account of browser security
  engineering anywhere.
- **RenderingNG series** on `developer.chrome.com/docs/chromium/` — overview, architecture,
  **key data structures**, **BlinkNG**, **LayoutNG**, VideoNG. Chris Harrelson et al. This
  is the best public description of a modern rendering engine's architecture, full stop.
- **Mozilla**: `firefox-source-docs.mozilla.org`, **Mozilla Hacks** (Stylo, WebRender,
  Quantum, and Fission write-ups), the **Mozilla standards-positions** repo.
- **WebKit blog** (`webkit.org/blog`) — especially the Interop and ITP posts.
- **web.dev** and **MDN** — MDN is the de facto platform reference; web.dev carries
  Baseline and the Chrome rendering/performance material.
- **Web Platform Tests** (`web-platform-tests.org`, `wpt.fyi`) and the
  **Interop dashboard**.
- **Ladybird** (`ladybird.org`, and the GitHub repo) and **Servo** (`servo.org`) —
  both are readable codebases in a way the big three are not, which makes them excellent
  learning material even if you never ship them.

### 18.2 Books and long-form

| Work | Why |
|---|---|
| **Tali Garsiel & Paul Irish, "How Browsers Work"** | The classic single-article overview. Dated in specifics, correct in shape |
| **"Web Browser Engineering" (Panchekha & Harrelson)** | **Free online.** Build a browser in Python, chapter by chapter. **The best hands-on introduction that exists** |
| **Alan Grosskurth & Michael Godfrey**, "A Reference Architecture for Web Browsers" | The academic framing of the component decomposition |
| **Michal Zalewski, *The Tangled Web*** | The best book on web security's actual model and its historical accidents |
| **Ryan Barnett / OWASP materials**; **Google's Web Fundamentals security docs** | Practical |
| **Ilya Grigorik, *High Performance Browser Networking*** | **Free online.** The networking reference (§3 → `browser-engine-architecture-and-networking`) |
| **Lin Clark's cartoon deep-dives** (Mozilla) | Stylo, WebRender, and Wasm explained better than anywhere else |
| **"Inside look at modern web browser"** (Mariko Kosaka, Chrome) | A clear four-part architecture series |

### 18.3 People and channels
Chris Harrelson (Blink rendering), Charlie Reis and Adrienne Porter Felt (Chrome security
and Site Isolation), Andreas Kling (Ladybird — his development streams are unusually good
teaching material), Lin Clark (Mozilla), Ilya Grigorik (networking), Alex Russell
(platform, opinionated and worth reading precisely for that), Jen Simmons and Rachel
Andrew (CSS layout), Anne van Kesteren (WHATWG specs), Michal Zalewski (web security).
Follow the **blink-dev** and **mozilla.dev.platform** intent-to-ship threads if you want
to see the platform being decided in public.

---
