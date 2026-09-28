---
id: skill-17-case-studies-and-hard-won-lessons-dd96ff483b
purpose: 17 case studies and hard won lessons
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-reference/SKILL.md
requires: ["skill-16-the-canon-authorities-and-references-b20202174b"]
links: ["skill-18-currency-snapshot-verified-august-2026-d7566cf238"]
---

## §17. Case Studies and Hard-Won Lessons

| Case | What happened | Transferable lesson |
|---|---|---|
| **Ghostty's non-native fullscreen** | Mitchell Hashimoto's terminal (Zig core, SwiftUI on macOS, GTK4 on Linux) needed "non-native fullscreen." Online samples suggested a dozen lines; the real PR was +802/−239. | The last 10% of *native feel* is where AppKit knowledge is irreplaceable. Budget for it, and note the architecture: shared core, per-platform UI — §0.2 → `desktop-macos-platform` pattern B. |
| **Google Cloud IoT Core / Microsoft App Center retirements** | Platform services people built on were withdrawn with notice periods measured in months. | Anything vendor-hosted in your update or telemetry path is a dependency with an expiry date. Own your appcast; keep your update mechanism replaceable. |
| **MacUpdater shutdown (Jan 2026)** | An 8-year-old app-tracking service wound down; its database goes dark end of 2026, already producing false positives. | Third-party update discovery is not a distribution strategy. Ship a working in-app updater. |
| **Electron's `nodeIntegration` era** | Early Electron apps ran remote content with full Node access; XSS became RCE. Defaults were changed (contextIsolation on, nodeIntegration off) in later majors. | Framework *defaults* are a security control. Apps that pinned old versions to avoid migration inherited the vulnerable defaults. |
| **The GNOME/KDE X11 removal** | Years of "Wayland isn't ready" gave way to GNOME removing X11 code entirely and KDE scheduling the same. | Deprecation announcements on the Linux desktop are slow, then sudden. Treat "we'll port later" as accruing interest. |
| **libadwaita theming controversy** | A widely-read post about theming triggered a large, still-unresolved argument about GTK vs libadwaita and who owns an app's appearance. | On Linux, appearance is a *social* contract as much as a technical one. Whatever you choose, expect to defend it in your issue tracker. |
| **The Linux accessibility resourcing gap** | Credible assessments found single-digit numbers of people working significantly on Linux a11y over a decade, while Wayland and sandboxing broke AT-SPI's assumptions. | If you use custom-drawn UI on Linux, you are almost certainly shipping an inaccessible app, and no ecosystem safety net will catch it. Use standard widgets. |
| **Apple silicon transition (2020–2026)** | Universal binaries, Rosetta 2, and now the end of Intel support in macOS 26. | Multi-year architecture transitions are normal on macOS. Keep your build system capable of producing fat binaries and your dependencies capable of both architectures. |
| **Sandbox retrofits** | Countless Mac apps that added App Sandbox years in discovered their data directory moved, their file access vanished, and their helper tools stopped working. | Sandbox decisions are architectural, not packaging. Decide before v1. |
| **The `.desktop`/app-ID mismatch class of bug** | Apps ship with a generic icon in the dock and no notification attribution because the Wayland `app_id` doesn't match the desktop file name. | Invisible in development, universal in bug reports. Verify the whole chain (§4.1 → `desktop-linux-platform`). |

---
