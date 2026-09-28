---
id: skill-0-routing-classify-before-answering-34aa1abfb9
purpose: 0 routing classify before answering
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-macos-platform/SKILL.md
requires: []
links: ["skill-1-macos-platform-architecture-720e7ce771"]
---

## §0. Routing — Classify Before Answering

### 0.1 The framework decision, up front

| If the answer to this is yes... | ...then |
|---|---|
| macOS-only, deep OS integration, sold on the Mac App Store | **SwiftUI + AppKit** |
| macOS + iOS from one codebase | **SwiftUI** (multiplatform target, not Catalyst) |
| Linux-first, GNOME-native feel, will ship on Flathub | **GTK4 + libadwaita** |
| Linux-first, KDE-native, or Linux+Windows+macOS with one native-ish toolkit | **Qt 6** |
| Team is web developers; you already have a web app; deadline dominates | **Electron** |
| Team can take on Rust; bundle size / memory matter; want a small attack surface | **Tauri 2** |
| Existing .NET/WPF codebase and skills; need Linux | **Avalonia** |
| Existing Kotlin/Android codebase; JVM shop | **Compose Multiplatform** |
| Pixel-identical custom UI on every OS, mobile too, don't care about native feel | **Flutter** |
| It's a developer tool / internal utility; native feel is irrelevant | Anything. Ship it. |

**[UNIVERSAL] The framework decision is downstream of two questions people skip:**
1. **Who maintains this in three years?** Framework choice is a hiring and staffing
   decision more than a technical one. A "better" framework nobody on the team knows is
   worse.
2. **Does this app need to feel native, or merely to work?** These have completely
   different cost curves. "Feels native" means platform menus, platform keyboard
   conventions, platform file dialogs, platform accessibility, platform theming,
   platform window behaviour — and it is 3–10× the work of "works."

### 0.2 The four architectures of a desktop app

```
A. Pure native, per platform     — two codebases, best feel, highest cost
B. Native UI + shared core       — Rust/C++/Go core, SwiftUI on Mac, GTK/Qt on Linux
                                   (the "right" answer for serious cross-platform apps)
C. Single cross-platform toolkit — Qt / Flutter / Avalonia / Compose. One UI, everywhere.
D. Web UI in a shell            — Electron / Tauri. One UI, everywhere, web tech.
```
**B is underrated.** Ghostty (Zig core + SwiftUI on macOS + GTK4 on Linux), 1Password
(Rust core), Signal, and many others use it. The core is testable, portable, and
performance-critical; the UI is thin and idiomatic per platform. The cost is that you
write the UI twice — but the UI is usually the *smaller* half of a serious application,
and it's the half where "twice" buys you the most.

### 0.3 The question-type router

| Asked about... | Go to |
|---|---|
| Bundles, launchd, run loops, Darwin, XPC | §1 |
| SwiftUI, AppKit, NSViewRepresentable, Liquid Glass, menus, windows | §2 |
| Swift concurrency, @MainActor, SwiftData/Core Data | §3 |
| D-Bus, systemd user units, XDG specs, PipeWire, desktop files | §4 → `desktop-linux-platform` |
| GTK4, libadwaita, Qt6, QML, toolkit choice on Linux | §5 → `desktop-linux-platform` |
| Wayland, X11, XWayland, compositors, protocols | §6 → `desktop-linux-platform` |
| Electron, Tauri, Flutter, Avalonia, Compose, Rust GUI | §7 → `desktop-cross-platform-and-architecture` |
| MVVM, state management, undo, documents, IPC, threading | §8 → `desktop-cross-platform-and-architecture` |
| Windows, keyboard, drag & drop, HiDPI, dark mode, i18n, a11y | §9 → `desktop-cross-platform-and-architecture` |
| Notarization, DMG, Flatpak, Snap, AppImage, .deb/.rpm, AppStream | §10 → `desktop-packaging-security-and-testing` |
| Sparkle, auto-update, delta updates, rollout | §11 → `desktop-packaging-security-and-testing` |
| TCC, entitlements, hardened runtime, portals, Electron security | §12 → `desktop-packaging-security-and-testing` |
| UI testing, profiling, Instruments, sysprof, CI | §13 → `desktop-packaging-security-and-testing` |
| "Don't do this" | §14 → `desktop-reference` |
| "Which is better, X or Y?" | §15 → `desktop-reference` (contested) |
| Books, docs, HIGs, authorities | §16 → `desktop-reference` |
| Famous failures and lessons | §17 → `desktop-reference` |
| "Is this still current?" | §18 → `desktop-reference` |

---
