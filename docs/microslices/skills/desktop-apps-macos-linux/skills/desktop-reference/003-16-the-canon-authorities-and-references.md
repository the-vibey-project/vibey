---
id: skill-16-the-canon-authorities-and-references-b20202174b
purpose: 16 the canon authorities and references
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-reference/SKILL.md
requires: ["skill-15-contested-questions-ffb1870ba0"]
links: ["skill-17-case-studies-and-hard-won-lessons-dd96ff483b"]
---

## §16. The Canon — authorities and references

### 16.1 Primary documentation (always prefer these)

**Apple**
- **Human Interface Guidelines** — the macOS sections specifically; the Mac patterns
  differ from iOS in ways tutorials elide.
- **Apple Developer Documentation**: AppKit, SwiftUI, Foundation, Security, `notarytool`,
  "Notarizing macOS software before distribution", "Adopting Liquid Glass",
  "Adopting strict concurrency in Swift 6".
- **WWDC session videos** — genuinely the best source for new API rationale. For this
  domain: "Use SwiftUI with AppKit and UIKit" (WWDC26), "Build a SwiftUI app with the new
  design" (WWDC25), the privacy/Gatekeeper "What's new in privacy" series (2022–2024
  cover app-bundle, container, and app-group protection changes).
- **Apple Platform Security guide** — Gatekeeper, notarization, runtime protection.
- **Swift Evolution proposals** (SE-####) for concurrency semantics; the **Swift Forums**
  are where the real migration discussions happen.

**Linux / freedesktop**
- **freedesktop.org specifications** — Base Directory, Desktop Entry, Icon Theme,
  AppStream, MIME, Notifications, Autostart, Trash, Secret Service.
- **XDG Desktop Portal documentation** (`flatpak.github.io/xdg-desktop-portal`) — the
  API reference *and* the "Reasons to Use Portals" / "For App Developers" pages.
- **GNOME Human Interface Guidelines** and the **libadwaita** docs; **GTK4 API reference**;
  **gtk4-rs book**.
- **KDE Human Interface Guidelines**; **Qt documentation** (`doc.qt.io`) — especially the
  licensing and release pages, which are the authoritative word on LGPL/GPL/commercial.
- **Flatpak documentation** (sandbox permissions, manifests) and **Flathub's** submission
  requirements.
- **ArchWiki** — despite being distro-specific, it is the best practical reference for
  PipeWire, portals, Wayland, systemd/user, and D-Bus. Use it as documentation, not as
  Arch advocacy.
- **LWN.net** — the highest-signal reporting on Linux desktop architecture changes
  (the accessibility/Newton coverage is the reference on that topic).

### 16.2 Books and long-form

| Author / source | Work | Why |
|---|---|---|
| **Aaron Hillegass** | *Cocoa Programming for OS X* | The classic AppKit text; still the best explanation of the Cocoa object model and delegation |
| **Matt Neuburg** | *Programming iOS/macOS* series | Rigorous, precise, updated frequently |
| **Paul Hudson** | *Hacking with Swift / Hacking with macOS* | The best free practical Swift/SwiftUI reference; his Swift 6 concurrency writeups are widely cited |
| **Chris Eidhof, Florian Kugler, Wouter Swierstra (objc.io)** | *Advanced Swift*, *Thinking in SwiftUI* | The deepest treatment of how SwiftUI actually evaluates |
| **Fatbobman (Xu Yang)** | Core Data / SwiftData blog series | The most thorough independent analysis of Apple's persistence stack |
| **Michael Tsai** | Blog | The community's institutional memory for Apple platform changes and their consequences |
| **Jasper St. Pierre** | *Xplain* | The clearest existing explanation of how X11 actually works — read before arguing about Wayland |
| **Daniel Stone** | "The Real Story Behind Wayland and X" (talk) | The canonical account of why Wayland exists |
| **Havoc Pennington** | D-Bus design writing | Origin rationale for the desktop's IPC model |
| **Blanchette & Summerfield** | *C++ GUI Programming with Qt* | Dated but still the best structured Qt introduction |
| **Andrew Krause** | *Foundations of GTK+ Development* | GTK's conceptual model (GTK3-era; concepts transfer) |
| **Jeff Johnson** | *Designing with the Mind in Mind*; *GUI Bloopers* | The cognitive-psychology basis for UI decisions |
| **Alan Cooper** | *About Face* | The interaction-design canon |
| **Bruce Tognazzini** | *Tog on Interface* / First Principles | Where much of the Mac's interaction philosophy originates |

### 16.3 Ongoing sources
**Apple side**: Michael Tsai's blog, The Eclectic Light Company (Howard Oakley — deep,
accurate macOS internals), Hacking with Swift, objc.io, SwiftLee, Swift Forums,
`developer.apple.com/forums` (the Gatekeeper/code-signing tags are staffed by Apple's
DTS and are the definitive answer source for signing problems).
**Linux side**: LWN.net, Phoronix (news, treat benchmarks carefully), GNOME and KDE
developer blogs (`blogs.gnome.org`, `blogs.kde.org` — KDE's "This Week in Plasma" is
excellent), 9to5Linux/OMG!Ubuntu for release tracking, the Flatpak and freedesktop
GitLab issue trackers.
**Cross-platform**: the Electron and Tauri blogs and release notes; `areweguiyet.com` and
boringcactus's periodic Rust GUI survey.

---
