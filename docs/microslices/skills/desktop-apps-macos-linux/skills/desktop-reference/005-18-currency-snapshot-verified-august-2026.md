---
id: skill-18-currency-snapshot-verified-august-2026-d7566cf238
purpose: 18 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-reference/SKILL.md
requires: ["skill-17-case-studies-and-hard-won-lessons-dd96ff483b"]
links: ["skill-19-quick-reference-f9462082eb"]
---

## §18. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **macOS** | **macOS 26 "Tahoe"** shipped 15 Sept 2025; latest **26.6.2** (17 Aug 2026). **Last macOS to support Intel Macs.** macOS 27 "Golden Gate" in public beta, September release expected | **High** |
| **Xcode / Swift** | Xcode **26.6** current (26.4 pairs with Swift compiler **6.3**; language modes 4/4.2/5/6). Xcode 26.4 requires macOS Tahoe 26.2+ | High |
| **Swift concurrency** | Swift 6 strict concurrency is the default in Swift 6 mode; **Swift 6.2's "approachable concurrency"** (`SWIFT_APPROACHABLE_CONCURRENCY`, main-actor-by-default, `nonisolated(nonsending)` per SE-0461, `@concurrent` escape hatch) is on by default for new Xcode 26 projects | Medium |
| **Liquid Glass** | Introduced macOS 26; free for framework chrome on recompile; custom components need work; Icon Composer required for icons | Medium |
| **SwiftData** | Production-viable for new apps on macOS 14+/iOS 17+; stable across three OS releases; gained migration tooling in iOS 18; model inheritance added in the 2025 cycle. Still weaker than Core Data for complex graphs, heavyweight migrations, and some CloudKit sync modes | Medium |
| **GTK** | **GTK 4.22.x** (4.22.4, Apr 2026) current. GTK5 not imminent. libadwaita tracks GNOME releases | Medium |
| **GNOME** | GNOME 49 disabled the X11 session; **X11 backend code removed from Mutter; GNOME 50 (Mar 2026) ships with zero X11 code**. GNOME 51 due Sept 2026 | High |
| **KDE Plasma** | **Plasma 6.8 will be Wayland-only**, expected ~**14 Oct 2026**; Plasma X11 session supported into **early 2027** | High |
| **Distros** | Fedora 43 and Ubuntu 25.10 already ship no GNOME X11 session; Ubuntu 26.04 makes Wayland exclusive for major DEs | High |
| **Xorg / XLibre** | Xorg still maintained for security, **feature development halted**. XLibre is an actively-developed fork of contested provenance, adopted by a few distros (e.g. Artix default) | Medium |
| **Qt** | **Qt 6.11.x** current (6.11.1, May 2026); ~6-month minor cadence. LTS = 5 years since 6.8.0; **LTS patches are commercial-only** | Medium |
| **Wayland ancillary** | PipeWire **1.6.x** is the default audio/video server nearly everywhere; screen capture requires ScreenCast portal + PipeWire | Medium |
| **Linux a11y** | AT-SPI2 is current; **Newton** (AccessKit-based, Wayland-native, sandbox-compatible) is the experimental successor. KDE added AT-SPI2 in Plasma 6.0; keyboard-event API landed in Mutter 48/GNOME 48 and KWin/KDE 6.4 | Medium |
| **Flatpak/Flathub** | Flathub ~3,200–3,500 apps, 433M downloads reported for 2025; default on Fedora, Mint, elementary, Steam Deck; Canonical ships a Flatpak plugin for GNOME Software | Low |
| **Electron** | Still the most-used desktop framework; powers VS Code, Slack, Discord, Notion, Postman, 1Password, Obsidian, Linear, Figma desktop | Low |
| **Tauri** | **Tauri 2 stable**, mobile (iOS/Android) supported; the default recommendation for new size/memory-sensitive projects in most 2026 comparisons | Medium |
| **Deno desktop** | `deno desktop` shipped in **Deno 2.9 (25 June 2026)**; explicitly experimental | High |
| **Avalonia** | **Avalonia 12** released ~Apr 2026 (large rendering-performance work; Impeller renderer in partnership with Google's Flutter team). **Avalonia.MAUI** backend brings MAUI to Linux/browser — preview | Medium |
| **.NET MAUI** | Mobile-first; **no first-party Linux support**; desktop via WinUI + Mac Catalyst | Medium |
| **Sparkle** | Still the macOS standard; Sparkle 2 supports sandboxed apps, custom UI, EdDSA signing, delta updates | Low |
| **MacUpdater** | **Discontinued 1 Jan 2026**; database scheduled dark end of 2026 | Settled |
| **EU CRA** | Reporting obligations **11 Sept 2026**; full application **11 Dec 2027** — applies to desktop software sold in the EU | **Imminent** |

**What goes stale fastest**: macOS/Xcode versions; GNOME and Plasma release status; Swift
concurrency defaults; cross-platform framework version claims and benchmarks.
**What essentially never goes stale**: §8 → `desktop-cross-platform-and-architecture` (architecture), §9 → `desktop-cross-platform-and-architecture` (desktop idioms), §14
(anti-patterns), §17 (lessons).

---
