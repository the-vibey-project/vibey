---
id: skill-vs-code-and-ide-extensions-2d327eb8f9
purpose: vs code and ide extensions
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-editor-and-desktop-surfaces/SKILL.md
requires: []
links: ["skill-desktop-apps-e2ccf3b1e8"]
---

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
