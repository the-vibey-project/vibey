---
id: skill-20-sources-and-method-1392fc1eb8
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-reference/SKILL.md
requires: ["skill-19-quick-reference-f9462082eb"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. Durable material — §8 → `desktop-cross-platform-and-architecture` (architecture),
§9 → `desktop-cross-platform-and-architecture` (desktop idioms), §14 (anti-patterns), §16–17 — is synthesized from established
practice and the canonical literature in §16. Every **time-sensitive** claim (versions,
dates, deprecation schedules, product status) was verified against a primary or
near-primary source in **August 2026** and is flagged in §18 with a decay-risk rating.
Where practitioners disagree, §15 gives both cases rather than adjudicating, and disputed
claims are marked in place.

**Search log** (August 2026): macOS current version and Xcode/Swift pairing · SwiftUI vs
AppKit state of play · GTK4/libadwaita versions and GNOME releases · Qt 6 releases and
licensing · Wayland/X11 transition status across GNOME, KDE, and distros · Flatpak vs Snap
vs AppImage · Tauri 2 vs Electron · macOS notarization, Hardened Runtime, entitlements,
Gatekeeper · XDG Desktop Portals · Swift 6 strict concurrency and 6.2 approachable
concurrency · Rust GUI ecosystem maturity · PipeWire, D-Bus, systemd user services ·
Sparkle and desktop auto-update · Linux accessibility (AT-SPI, Orca, Newton) · macOS 26
Liquid Glass adoption · .NET MAUI / Avalonia / Compose Multiplatform desktop status ·
SwiftData vs Core Data.

**Primary and near-primary sources consulted (selected):**
- Apple Developer documentation and WWDC sessions — Xcode system requirements page,
  macOS 26 release notes, "Use SwiftUI with AppKit and UIKit" (WWDC26), "Build a SwiftUI
  app with the new design" (WWDC25), "Adopting Liquid Glass", "Adopting strict concurrency
  in Swift 6", "Notarizing macOS software before distribution"
- Apple Support — Gatekeeper and runtime protection; macOS Tahoe 26 update notes
- Bluetooth-unrelated: Qt Company — `doc.qt.io` releases and licensing pages; Qt release blogs
- GNOME — `blogs.gnome.org` (X11 Session Removal FAQ; Newton accessibility updates);
  GTK releases; libadwaita
- KDE — `blogs.kde.org` "Going all-in on a Wayland future"; Plasma/Wayland community wiki
- freedesktop.org — D-Bus specification; XDG Desktop Portal documentation and API reference
- Flatpak — sandbox permissions documentation; Flathub
- Snapcraft — XDG Desktop Portals documentation
- ArchWiki — PipeWire, XDG Desktop Portal
- LWN.net — "Modernizing accessibility for desktop Linux"; "Enhancing screen-reader
  functionality in modern GNOME"
- Sparkle Project — `sparkle-project.org` and GitHub
- Electron — `electron.build` notarization docs; `electron/notarize`
- Avalonia UI — Avalonia 12 release blog; MAUI backend announcement
- Espressif-unrelated: Deno release notes (via secondary coverage) for `deno desktop`
- European Commission — Cyber Resilience Act reporting obligations

**Confidence statement.** High confidence in §1–§2 → `desktop-macos-platform`, §4–§6 → `desktop-linux-platform`, §8–§14 → `desktop-cross-platform-and-architecture`, §16–§17, §19 (durable
architecture, well-documented platform mechanics, and verifiable history). High confidence
in §18's verified items as of the stated date. **Moderate confidence** in the framework
comparison figures in §7.1 → `desktop-cross-platform-and-architecture` and the adoption characterizations in §7.2 → `desktop-cross-platform-and-architecture`, §7.4 → `desktop-cross-platform-and-architecture`, and §10.2 → `desktop-packaging-security-and-testing` —
these rest substantially on practitioner blogs and vendor material where incentives differ
and methodology is rarely published. They are stated as representative ranges and
tendencies, **not measurements**; benchmark your own workload before making a decision
that depends on them.
