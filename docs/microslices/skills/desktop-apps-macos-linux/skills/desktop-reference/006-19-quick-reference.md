---
id: skill-19-quick-reference-f9462082eb
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-reference/SKILL.md
requires: ["skill-18-currency-snapshot-verified-august-2026-d7566cf238"]
links: ["skill-20-sources-and-method-1392fc1eb8"]
---

## §19. Quick Reference

### 19.1 "Why doesn't my app feel native?" — the checklist
1. Menu bar / header bar follows the platform HIG, with every command present
2. Keyboard shortcuts match platform conventions; full keyboard navigation works
3. Platform file dialogs (not a custom browser)
4. Semantic colors; dark mode and high contrast work; respects Reduce Transparency/Motion
5. Window size/position/state restored across launches
6. Drag & drop in *and* out; clipboard with multiple representations
7. Undo/redo, unlimited and coalescing; autosave; crash recovery
8. Correct app ID everywhere → icon, notifications, and window matching work (Linux)
9. Screen-reader accessible (VoiceOver / Orca) — actually tested
10. Idles at ~0% CPU

### 19.2 "The app won't launch on a user's Mac"
Signature broken (`codesign --verify --deep --strict`) → not notarized or ticket not
stapled (`stapler validate`) → quarantine + translocation breaking a relative path →
missing `NS*UsageDescription` for an API it calls at launch → an embedded binary unsigned
or lacking Hardened Runtime → architecture mismatch (arm64-only on Intel, or a
mixed-arch plugin) → `LSMinimumSystemVersion` above their OS.

### 19.3 "The app misbehaves on Linux"
Wrong/missing `.desktop` file or app-ID mismatch → Wayland vs X11 assumption → missing or
wrong portal backend → no D-Bus session bus → Flatpak sandbox denying something (check
`flatpak run --command=sh` and the portal logs) → missing runtime dependency the distro
didn't pull in → fractional scaling → theme assumptions.

### 19.4 Numbers worth knowing
- Frame budget: **16.7 ms** @60 Hz, **8.3 ms** @120 Hz.
- "Instantaneous" to a user: **< 100 ms**. Needs a spinner: **> 1 s**. Needs
  cancel + progress: **> 10 s**.
- Cold launch target: **< 1 s** to interactive.
- WCAG AA contrast: **4.5:1** body text, **3:1** large text and UI components.
- Electron: ~80–200 MB bundle, ~150–300 MB idle RAM. Tauri: ~2–10 MB, ~30–50 MB.
- macOS deployment: notarization requires **Hardened Runtime**; Mac App Store requires
  **App Sandbox**; both require **code signing**.
- Flatpak runtime download on first install: **500 MB+** (GNOME/KDE platform) — mention
  it in your install docs so users don't think your 8 MB app is 500 MB.

### 19.5 Reviewing someone else's desktop app
- [ ] Is there a UI-framework-free domain layer with tests? (§8.1 → `desktop-cross-platform-and-architecture`)
- [ ] Any file/network I/O on the main thread? (§8.4 → `desktop-cross-platform-and-architecture`)
- [ ] Are long operations cancellable, with progress?
- [ ] Undo, autosave, atomic writes for user data? (§8.3 → `desktop-cross-platform-and-architecture`)
- [ ] Window state restoration? Multi-window safe?
- [ ] Semantic colors, dark mode, HiDPI, Reduce Transparency? (§9.4 → `desktop-cross-platform-and-architecture`)
- [ ] Every command reachable by keyboard and present in a menu? (§9.2 → `desktop-cross-platform-and-architecture`)
- [ ] Screen-reader tested (VoiceOver/Orca)? (§9.6 → `desktop-cross-platform-and-architecture`)
- [ ] Strings externalized; plurals and RTL handled? (§9.5 → `desktop-cross-platform-and-architecture`)
- [ ] Secrets in Keychain / Secret Service, not files? (§12 → `desktop-packaging-security-and-testing`)
- [ ] macOS: signed + hardened + notarized + stapled; entitlements minimal? (§10.1 → `desktop-packaging-security-and-testing`)
- [ ] Linux: app ID consistent; portals used; no `--filesystem=home`? (§4.1 → `desktop-linux-platform`, §12.3 → `desktop-packaging-security-and-testing`)
- [ ] Electron: contextIsolation on, nodeIntegration off, CSP, current version? (§7.3 → `desktop-cross-platform-and-architecture`)
- [ ] Update path atomic, signed, rollback-capable, and tested in CI? (§11 → `desktop-packaging-security-and-testing`, §13.3 → `desktop-packaging-security-and-testing`)
- [ ] Idle CPU ≈ 0?

---
