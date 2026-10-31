---
id: skill-desktop-apps-e2ccf3b1e8
purpose: desktop apps
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-editor-and-desktop-surfaces/SKILL.md
requires: ["skill-vs-code-and-ide-extensions-2d327eb8f9"]
links: []
---

## Desktop apps

Choose the architecture by who maintains it in three years and whether it must feel native; most of the rest follows. This section draws on a desktop-development reference I loaded and on Microsoft's [Windows design overview](https://learn.microsoft.com/en-us/windows/apps/design/guidelines-overview) (an index page, so it gave little detail).

| If you need | Likely choice |
| --- | --- |
| Mac-only with deep OS integration | SwiftUI plus AppKit where needed |
| Web team, existing web app, tight deadline | Electron |
| Small footprint and a Rust-capable team | Tauri |
| Linux-native feel | GTK4 with libadwaita, or Qt |
| One custom look on every OS | Flutter or Compose Multiplatform |
| Serious cross-platform product | Shared core in Rust or C++, thin native UI per platform |

**Native-feel checklist** (the reference estimates that real native feel costs several times the effort of "it works"):

- **Complete menu bar.** Every command appears in a menu, even when it also has a toolbar button; this is how Help search, shortcut discovery and accessibility find it.
- **Unlimited, coalescing undo.** Typing 30 characters is one undo step.
- **Window-state restoration and multiple windows.**
- **Keyboard first**, with shortcuts shown in menus.
- **Dark mode, HiDPI and system accessibility settings** respected.
- **Linux is a family of conventions**, not one platform: GNOME favors header bars, KDE keeps menu bars. Use libadwaita or KDE components and inherit the right answer.

**Where features belong on desktop**

| Feature | Place |
| --- | --- |
| Quick status and one-click actions | Menu-bar extra (macOS) or system tray (Windows, Linux) |
| Main workflow | Main window with a sidebar, list and detail layout |
| Rare configuration | Settings window opened by the standard shortcut |
| Long-running work | A progress area in the window plus a system notification on completion |
| Opening your files | File association and drag-and-drop onto the window or Dock icon |
| Updates | Automatic, with a visible "what changed" and a way to roll back |
| Background helpers | The platform's own login-item mechanism, listed where users manage startup items |

**macOS 26 Liquid Glass.** Recompiling against the new SDK gives standard chrome the new material free; your custom components do not get it and may clash. Respect Reduce Transparency and Increase Contrast, and apply glass effects to your own content conservatively. The reference notes this adoption question is contested.

**Pitfalls the reference flags:** a missing privacy usage string crashes the app on first use of that API; hardcoded data paths break when the sandbox is enabled; and an unauthenticated privileged helper is a local privilege-escalation risk.

**For non-developers.** Ship a signed, notarized installer that opens straight into a sample project, offer drag-a-folder-here as the first action, and keep a visible "Show me the code" toggle rather than starting in code view.
