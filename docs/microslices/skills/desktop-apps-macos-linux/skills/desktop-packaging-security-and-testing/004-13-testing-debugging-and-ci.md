---
id: skill-13-testing-debugging-and-ci-9f8b60962a
purpose: 13 testing debugging and ci
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-packaging-security-and-testing/SKILL.md
requires: ["skill-12-security-sandboxing-and-privacy-fcb530a478"]
links: []
---

## §13. Testing, Debugging, and CI

### 13.1 The testing pyramid for desktop

```
        ▲  Crash + telemetry from real users     ← the ultimate integration test
       ╱ ╲ Manual exploratory on real hardware/DEs
      ╱   ╲ UI automation (XCUITest / dogtail / Squish / Playwright)
     ╱     ╲ Integration: real window, real event loop, fake I/O
    ╱       ╲ Unit tests of domain + view models (no UI)   ← the bulk
   ╱_________╲ Static analysis + compiler warnings
```
**[UNIVERSAL] UI tests are slow, flaky, and expensive — so keep the UI thin.** If your view
models are pure and testable (§8.1 → `desktop-cross-platform-and-architecture`), you need very few UI tests: enough to verify wiring
and the two or three critical user journeys, not to test logic.

### 13.2 Tools

| Need | macOS | Linux |
|---|---|---|
| Unit tests | **Swift Testing** (`@Test`/`#expect`), XCTest | GTest/Catch2, pytest, `cargo test`, QTest |
| UI automation | **XCUITest**, Accessibility Inspector | **dogtail** (AT-SPI), Squish, `wlheadless`/`weston --backend=headless` for CI |
| Web-shell UI tests | Playwright/WebdriverIO against Electron | same |
| Profiling (CPU/alloc/time) | **Instruments** (Time Profiler, Allocations, Leaks, Metal, Energy Log, SwiftUI template) | **sysprof**, `perf`, Hotspot, Valgrind/Massif, heaptrack |
| Graphics debugging | Metal debugger, Quartz Debug | RenderDoc, `GTK_DEBUG=interactive`, `apitrace` |
| Widget inspection | Xcode View Debugger | **GTK Inspector** (`GTK_DEBUG=interactive`), **Qt's `GammaRay`** |
| Memory errors | ASan/TSan/UBSan via Xcode schemes | ASan/TSan/UBSan, Valgrind |
| Leaks | `leaks`, Instruments Leaks, Xcode Memory Graph | heaptrack, `G_DEBUG=gc-friendly` + Valgrind |
| Logging | **`os.Logger`** (unified logging; `log stream --predicate`) | `journalctl`, `G_MESSAGES_DEBUG=all`, `QT_LOGGING_RULES` |
| Crash reports | `~/Library/Logs/DiagnosticReports`, Xcode Organizer, Sentry/Crashlytics | `coredumpctl`, ABRT, Sentry |
| D-Bus tracing | — | `busctl monitor`, `dbus-monitor`, `d-feet` |

**The two most underused tools**: on macOS, **Instruments' Time Profiler with "Record
Waiting Threads"** turns "the app hangs sometimes" into a stack; on Linux,
`GTK_DEBUG=interactive` gives you a live widget inspector with CSS editing in any GTK app,
including ones you didn't write.

### 13.3 CI for desktop apps

```
push
 ├─ lint + format (SwiftLint/SwiftFormat; clang-format; clippy; eslint)
 ├─ unit tests: domain + view models ................ fast, every commit
 ├─ build all targets (macOS universal; Linux x86_64 + aarch64)
 ├─ ASan/TSan run of the test suite (nightly)
 ├─ package: .app + notarize + staple + DMG | Flatpak build + lint
 ├─ SBOM + dependency CVE scan
 ├─ sign artifacts (HSM/hosted signing, never a laptop key)
 └─ nightly: UI smoke tests on real macOS + headless Wayland; update-flow test
```

**Platform-specific CI realities:**
- **macOS builds require macOS runners.** Notarization requires network access and an App
  Store Connect API key. GitHub-hosted macOS images change their default Xcode on a
  schedule — **pin your Xcode version** (`sudo xcode-select -s /Applications/Xcode_26.4.app`
  or the setup-xcode action), or a runner-image update will break your build without a
  commit from you.
- **Linux GUI tests need a display.** Use a headless Wayland compositor (`weston
  --backend=headless-backend.so`, `wlheadless-run`, or `cage`) or Xvfb for X11 paths.
- **Test the update path in CI**, not just the app. A broken updater is unrecoverable
  without asking users to reinstall manually.
- **Test on the oldest OS you claim to support.** "Deployment target macOS 13" that has
  only ever run on macOS 26 is a claim, not a fact.
