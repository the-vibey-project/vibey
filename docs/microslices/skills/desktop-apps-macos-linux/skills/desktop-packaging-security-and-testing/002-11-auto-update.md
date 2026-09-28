---
id: skill-11-auto-update-5e76479800
purpose: 11 auto update
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-packaging-security-and-testing/SKILL.md
requires: ["skill-10-packaging-and-distribution-85a52656fc"]
links: ["skill-12-security-sandboxing-and-privacy-fcb530a478"]
---

## §11. Auto-Update

**[UNIVERSAL] Requirements for any desktop updater**, identical in spirit to firmware OTA:
signed, atomic, resumable, rollback-capable, and staged. A half-applied update that leaves
an unlaunchable app is the worst possible outcome — worse than never updating.

| Platform / stack | Mechanism | Notes |
|---|---|---|
| macOS direct | **Sparkle 2** | The de facto standard. EdDSA-signed appcast (RSS/XML), delta updates, atomic installs, **works with sandboxed apps** (a Sparkle 2 feature), fully rebrandable, works with any toolkit (Cocoa, SwiftUI, Qt, .NET). |
| macOS MAS | App Store | You don't control timing. |
| Electron | `electron-updater` / Squirrel.Mac | Mature; test the update flow in CI, not just the app. |
| Tauri | Built-in updater plugin | Signed manifests. |
| Flatpak | `flatpak update` / GNOME Software | OSTree deltas; you just push to the remote. |
| Snap | Automatic, transactional | You get rollback for free; you also lose control of update timing. |
| Distro packages | Distro's updater | Slowest path to users. |
| Cross-platform .NET | WinSparkle/Sparkle wrappers (e.g. UpSparkle) | Thin wrappers over the native frameworks. |

**Ecosystem note (2026):** the third-party Mac update-tracking tool **MacUpdater was
discontinued on 1 January 2026** (final free build 3.5.0; its database is scheduled to go
dark at the end of 2026), pushing users toward Homebrew, `mas-cli`, and Sparkle-aware tools
like Latest and Updatest. **Practical implication:** shipping a working Sparkle appcast is
now more important, because the safety net of third-party trackers is gone.

**Rollout discipline [UNIVERSAL]:** canary → percentage → full, with a kill switch. Ship a
crash reporter *before* you ship auto-update, so you can tell whether a release is bad
within hours instead of learning it from reviews.

---
