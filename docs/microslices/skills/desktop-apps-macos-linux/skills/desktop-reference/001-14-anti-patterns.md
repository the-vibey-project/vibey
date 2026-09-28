---
id: skill-14-anti-patterns-e70fb26bc4
purpose: 14 anti patterns
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-reference/SKILL.md
requires: []
links: ["skill-15-contested-questions-ffb1870ba0"]
---

## §14. Anti-Patterns

| Anti-pattern | Why it's bad | Do instead |
|---|---|---|
| Blocking I/O on the main thread | Beachball / frozen window; the #1 perceived-quality bug | Async everything; §8.4 → `desktop-cross-platform-and-architecture` |
| A custom file browser inside your app | Ignores bookmarks, recents, cloud providers, sandbox, portals | Platform file dialog / FileChooser portal |
| Hardcoded colors instead of semantic ones | Breaks dark mode, high contrast, accent colors | Semantic colors and system materials |
| Hardcoded paths (`~/Library/...`, `~/.config/...` literal) | Breaks under sandbox and Flatpak | Platform APIs / XDG env vars |
| No keyboard access to a feature | Fails accessibility; power users bounce | Menu item + shortcut for every command |
| Removing focus rings for aesthetics | Accessibility regression | Restyle them |
| Custom-drawn controls without accessibility | Invisible to screen readers | Native widgets, or implement the a11y tree |
| Ignoring window state restoration | Feels broken every launch | Persist and restore |
| A splash screen to hide slow startup | Hides the problem; users still wait | Fix startup; show real UI progressively |
| Auto-update that isn't atomic | Bricked installs, unrecoverable | Sparkle/OSTree/transactional |
| `--filesystem=home` in a Flatpak | Defeats the sandbox; reviewers reject | Portals |
| `nodeIntegration: true` / `contextIsolation: false` in Electron | Remote content gets Node — full RCE | Preload + contextBridge (§7.3 → `desktop-cross-platform-and-architecture`) |
| Shipping an ancient Electron/Chromium | You ship known RCEs | Track upstream releases |
| Polling timers at idle | Battery drain, fan noise, uninstall | Event-driven; pause when occluded |
| One giant "AppDelegate"/"MainWindow" class | Untestable, unmergeable | Layered architecture (§8.1 → `desktop-cross-platform-and-architecture`) |
| Assuming X11 | Broken on GNOME 50+, Fedora 43+, Ubuntu 25.10+ | Test on Wayland first |
| Assuming integer display scale | Blurry/misaligned at 125%/150% | Handle fractional scaling |
| String concatenation for translated text | Untranslatable; wrong word order | Positional format strings |
| Storing secrets in prefs/plain files | Trivially harvested | Keychain / Secret Service |
| Truncate-then-write the user's document | Crash mid-write destroys data | temp + fsync + atomic rename |
| No undo | Users will not trust the app with real work | §8.3 → `desktop-cross-platform-and-architecture` |
| Changing `CFBundleIdentifier` / app ID after ship | Orphans data, keychain, licenses, store record | Choose carefully once |
| Testing only on your own machine/DE | Ships bugs on every other configuration | Matrix: macOS n and n-1; GNOME + KDE; Wayland + X11 |

---
