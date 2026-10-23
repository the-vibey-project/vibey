---
name: devex-editor-and-desktop-surfaces
description: "Use when building or reviewing a VS Code or IDE extension (Command Palette, sidebar views, welcome views, walkthroughs, status bar, quick pick, panels, notifications, webviews, activation events, disposables, language servers, Open VSX publishing) or a desktop app (Electron, Tauri, SwiftUI, GTK4, Qt, menu-bar extras and system tray, native-feel checklist, menu bar, undo, window-state restoration, Liquid Glass, signed and notarized installers). Triggers on VS Code extension UX, webview rules, notification rules, walkthrough, desktop app native feel, macOS menu-bar extra, Linux desktop conventions. Companion to the other developer-experience skills."
---

# Developer Experience: VS Code Extensions and Desktop Apps

> **Part 6 of 9** of the *Developer Experience Blueprint* (plugin `developer-experience`), covering: VS Code and IDE extensions; Desktop apps. Sibling skills: `devex-principles-and-feedback-loops`, `devex-cli-and-errors`, `devex-api-sdk-and-docs`, `devex-interfaces-onboarding-and-agents`, `devex-surface-placement`, `devex-mobile-and-web-surfaces`, `devex-non-developers-and-visual-design`, `devex-reference`. A reference into a sibling is written *Section name → `skill`*.
>
> **Currency:** the blueprint is dated Oct 23, 2026; its evidence base and the AI-tooling claims age fastest, so re-check those first.
>
> Evidence grades used throughout: **A** = peer-reviewed or large study, **B** = credible practitioner or single study, **C** = vendor or opinion. Thin evidence is flagged where it occurs, and collected under *Where the evidence is weak or conflicting* in `devex-reference`.

## VS Code and IDE extensions

Use native surfaces first, and treat a webview as the last resort. VS Code's own [UX guidelines](https://code.visualstudio.com/api/ux-guidelines/overview.md) list the surfaces below; the placement column is my recommendation built on them.

| Surface | What VS Code says it is for | Put this feature here |
| --- | --- | --- |
| Command Palette | Commands from one consistent place | Every action, so keyboard users and search find it |
| Activity Bar + Primary Sidebar | Core navigation; extension items open Views | Your main tree: projects, runs, environments |
| Welcome view (inside a view) | Shown when a view is empty | The single "Get started" button for the empty state |
| Walkthroughs | Multi-step onboarding checklists with rich content | First-run setup that ends in a working result |
| Status Bar | Left = workspace scope, right = active-file scope | Connection state, current environment, one-click actions |
| Quick Pick | One choice, several choices or free text | Template picker, environment picker |
| Editor / custom editor | Document-shaped content | Visual editors for files your product owns |
| Panel | Terminal-like, output-like views | Logs, run output |
| Context menus | Actions tied to a location | "Run this", "Deploy this" on a file or tree item |
| Notifications | Info, warning, error, progress | Rare, actionable events only |
| Webview | Custom UI beyond the native API | Dashboards and visual builders that nothing native can express |
| Settings | Extension configuration | Rarely changed options; keep defaults working |

**Webview rules** (from the [webview guidance](https://code.visualstudio.com/api/ux-guidelines/webviews.md)). Do: use them only when necessary, open them only in the active window, keep them related to the editor or workspace, make every element themeable, and meet contrast, ARIA-label and keyboard requirements. Do not: use them for promotions, wizards, or to duplicate the Welcome page or Settings, and do not open them on every update (use a notification).

**Notification rules** (from the [notification guidance](https://code.visualstudio.com/api/ux-guidelines/notifications.md)). Send only when necessary, one at a time, merge several into one, add "Do not show again", show progress in the relevant view rather than globally, give a cancel action and a link to logs, and never use notifications for promotion or first-install feedback requests.

**Engineering points that shape the experience** (from a VS Code extension reference I loaded; not re-verified against Microsoft's docs):

- Activate on the narrowest event; activating on `*` is the usual cause of "VS Code is slow to start".
- Push every disposable onto `context.subscriptions`, or duplicate handlers fire after reloads.
- Write the heavy analysis as a language server when it must run outside VS Code; use in-process providers for simple single-language features.
- Keep logic out of the `vscode` API surface so it can be unit-tested without launching the editor.
- Publish to both the VS Code Marketplace and Open VSX to reach forks.

**Making it usable by non-developers inside an editor.** Lead with a sidebar view whose empty state has one button ("Create from template"), follow it with a walkthrough that finishes with a running result, and hide anything advanced behind Settings or a second level. Use plain-language labels in the UI and keep the technical term in the tooltip.

**Not researched here:** JetBrains IDEs, Visual Studio, Xcode and Android Studio plugin models. They follow similar ideas (tool windows instead of sidebars, intentions instead of code actions), but I have not verified their guidelines.

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
