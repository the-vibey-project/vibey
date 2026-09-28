---
id: skill-15-contested-questions-ffb1870ba0
purpose: 15 contested questions
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-reference/SKILL.md
requires: ["skill-14-anti-patterns-e70fb26bc4"]
links: ["skill-16-the-canon-authorities-and-references-b20202174b"]
---

## §15. Contested Questions

Present the strongest version of each side; the right answer is context-dependent.

**15.1 SwiftUI vs AppKit** — §2.1 → `desktop-macos-platform`. Dividing line: SwiftUI for structure and forms; AppKit
for dense data, text systems, and deep window/menu control. Nobody serious is 100% either.

**15.2 Native per-platform vs one cross-platform toolkit** — Native wins on feel,
accessibility, platform integration, and long-term maintainability *per platform*;
cross-platform wins on total cost and consistency. The synthesis that keeps winning is
architecture **B** from §0.2 → `desktop-macos-platform`: shared core, native UI.

**15.3 Electron vs Tauri** — §7.2 → `desktop-cross-platform-and-architecture`. Consistency and ecosystem maturity versus footprint and
permission model. Both camps are shipping real products.

**15.4 Flatpak vs Snap vs AppImage** — §10.2 → `desktop-packaging-security-and-testing`. Flatpak has the ecosystem centre of gravity
for GUI apps; Snap has the Ubuntu/server/daemon story and transactional updates but a
single centralized store; AppImage has portability and no update or sandbox story. Trying
to force one format everywhere is the actual mistake.

**15.5 GTK+libadwaita vs Qt on Linux** — libadwaita gives you a GNOME-perfect app and a
GNOME-shaped one. Qt gives you cross-desktop and cross-OS reach with a licensing decision
attached (LGPL relinking constraints; GPL-only modules; commercial for static linking and
LTS patches). Neither is wrong; the deciding factors are usually licensing and whether you
also target Windows.

**15.6 Sandboxed (App Store/Flatpak) vs unsandboxed distribution** — Sandboxing buys user
trust, store distribution, and genuine security; it costs capability (some apps simply
cannot be sandboxed), engineering time, and — on macOS — a revenue share. Many pro Mac
apps ship both builds with different feature sets, and say so plainly on their site.

**15.7 Wayland-first vs keeping X11 support** — GNOME has removed X11 code and KDE follows
in Plasma 6.8; new apps should be Wayland-native and use portals. The counterweight: LTS
distributions, XFCE/MATE/Cinnamon users, remote-desktop workflows, and accessibility tools
that still work better on X11 will exist for years. Support both if your users need it,
but *develop* on Wayland.

**15.8 Swift 6 strict concurrency: too much or just right** — §3.2 → `desktop-macos-platform`.

**15.9 SwiftData vs Core Data vs GRDB** — §3.3 → `desktop-macos-platform`.

**15.10 Menu bar vs header-bar/hamburger on Linux** — GNOME HIG says header bar; KDE and
traditional-desktop users expect menus; power users and accessibility tooling both benefit
from a discoverable menu structure. Pick per your target desktop and be internally
consistent.

---
