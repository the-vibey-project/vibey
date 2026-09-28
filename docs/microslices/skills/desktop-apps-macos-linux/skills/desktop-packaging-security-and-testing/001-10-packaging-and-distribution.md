---
id: skill-10-packaging-and-distribution-85a52656fc
purpose: 10 packaging and distribution
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-packaging-security-and-testing/SKILL.md
requires: []
links: ["skill-11-auto-update-5e76479800"]
---

## §10. Packaging and Distribution

### 10.1 macOS: the four distribution channels

| Channel | Signing | Sandbox | Notarization | Update mechanism | Trade-off |
|---|---|---|---|---|---|
| **Mac App Store** | Apple Distribution cert | **Required** | N/A (review instead) | App Store | Discovery + trust; 15–30% cut; review latency; sandbox limits |
| **Developer ID (direct)** | Developer ID Application | Optional | **Required** | Sparkle or your own | Full capability, your prices, you own support |
| **Both** | Two builds | Differs | — | — | Common for pro apps; maintain two entitlement sets |
| **Homebrew Cask** | Developer ID | Optional | Required | `brew upgrade` | Great for developer tools; not a discovery channel for consumers |

**The Developer ID pipeline, precisely:**

```bash
# 1. Sign everything inside-out: frameworks, helpers, XPC services, then the app.
#    --options=runtime enables the Hardened Runtime — REQUIRED for notarization.
codesign --force --timestamp --options=runtime \
  --sign "Developer ID Application: Example Inc (TEAMID)" \
  MyApp.app/Contents/Frameworks/*.framework

codesign --force --timestamp --options=runtime \
  --entitlements MyApp.entitlements \
  --sign "Developer ID Application: Example Inc (TEAMID)" \
  MyApp.app

# 2. Verify BEFORE you ship, not after a user's bug report.
codesign --verify --deep --strict --verbose=2 MyApp.app
spctl --assess --type exec --verbose=4 MyApp.app

# 3. Notarize. Use an App Store Connect API key in CI — it doesn't expire
#    and doesn't trip 2FA, unlike an app-specific password.
ditto -c -k --keepParent MyApp.app MyApp.zip
xcrun notarytool submit MyApp.zip \
  --key AuthKey_XXXX.p8 --key-id XXXX --issuer <issuer-uuid> --wait

# 4. Staple the ticket so Gatekeeper works OFFLINE.
xcrun stapler staple MyApp.app
xcrun stapler validate MyApp.app

# 5. Ship a DMG or PKG — and notarize + staple THAT too, not just the .app.
```

> **⚠️ GOTCHA — notarization failures are almost always one of five things:**
> (1) Hardened Runtime not enabled on *every* executable, including helpers and embedded
> binaries in `Contents/MacOS/` subdirectories; (2) a nested binary that wasn't signed;
> (3) a missing `--timestamp` (signatures without a secure timestamp expire with the
> certificate); (4) a JIT or unsigned-memory requirement without
> `com.apple.security.cs.allow-jit` / `allow-unsigned-executable-memory` (this hits every
> Electron, JVM, Python, and .NET app); (5) an entitlement you're not authorized for.
> The notarization log URL Apple emails you names the exact file — read it rather than
> guessing.

> **⚠️ GOTCHA — app translocation.** Gatekeeper runs quarantined apps from a randomized,
> read-only path on first launch. Anything that assumes it can write next to itself, or
> that reads its own path to find resources outside the bundle, breaks in a way that never
> reproduces in development. Fix: ship in a DMG that instructs dragging to /Applications,
> and never write beside the bundle.

**Entitlements** (`MyApp.entitlements`), the ones that matter:
```xml
<key>com.apple.security.app-sandbox</key><true/>              <!-- required for MAS -->
<key>com.apple.security.files.user-selected.read-write</key><true/>
<key>com.apple.security.files.bookmarks.app-scope</key><true/> <!-- persist file access -->
<key>com.apple.security.network.client</key><true/>
<key>com.apple.security.device.camera</key><true/>
<key>com.apple.security.cs.allow-jit</key><true/>              <!-- Electron/JVM/JIT -->
<key>com.apple.security.temporary-exception.files.home-relative-path.read-write</key>
```
**Security bookmarks are the key sandbox concept**: when the user picks a file, you get
access to *that file* for *this launch*. To keep access across launches, create a
**security-scoped bookmark**, persist it, and resolve it later with
`startAccessingSecurityScopedResource()` / `stopAccessing…` (balanced — leaking these
exhausts a limited resource).

### 10.2 Linux: the packaging matrix

| Format | Sandbox | Updates | Store | Distro reach | Best for |
|---|---|---|---|---|---|
| **Flatpak** | Bubblewrap + namespaces + portals | Delta via OSTree | **Flathub** (community-governed, self-hostable remotes) | Universal; default on Fedora, Mint, elementary, Steam Deck | **The default recommendation for GUI apps** |
| **Snap** | AppArmor + seccomp | Automatic, transactional, rollback | Snap Store (**Canonical-only, no alternate remotes**) | Ubuntu-centric | Ubuntu targeting; CLI tools; servers/IoT; daemons |
| **AppImage** | **None** | **None built in** | AppImageHub (community directory) | Anywhere with FUSE | Portable single-file distribution, no-root environments, testing a version |
| **.deb / .rpm** | None | Distro repo | Distro archives | Per-distro | System-level software; when a distro packages you |
| **AUR / Homebrew / nix** | Varies | Varies | — | Per-ecosystem | Developer tools |

**[CONTESTED] but with a clear centre of gravity:** the 2026 consensus in most practitioner
comparisons is **Flatpak+Flathub as the primary universal format for desktop GUI apps**
(largest catalogue — Flathub passed ~3,200 apps and 433M downloads in 2025 and continues
growing; strongest sandboxing story; shared runtimes save disk; OSTree deltas save
bandwidth), **Snap where you're Ubuntu-aligned or shipping daemons/CLI**, and **AppImage
for portability**. The recurring criticisms are also real: universal packages start slower
than native ones (Snap notably), theming integration is imperfect, runtimes are large on
first install, and **neither Flathub nor the Snap Store vets aggressively** — both have
hosted fake crypto wallets and other malware. Verified-publisher badges exist for a reason;
tell your users to check them.

```yaml
# com.example.MyApp.yaml — a Flatpak manifest
app-id: com.example.MyApp
runtime: org.gnome.Platform
runtime-version: '48'
sdk: org.gnome.Sdk
command: myapp
finish-args:
  - --socket=wayland
  - --socket=fallback-x11          # NOT --socket=x11; fallback prefers Wayland
  - --device=dri                   # GPU
  - --share=network
  # NOTE: no --filesystem=home. Use the FileChooser portal instead — that is
  # the entire point, and Flathub will flag broad filesystem access.
  - --talk-name=org.freedesktop.secrets   # keyring, if you need it
modules:
  - name: myapp
    buildsystem: meson
    sources:
      - type: archive
        url: https://example.com/myapp-1.2.0.tar.xz
        sha256: <hash>
```

> **⚠️ GOTCHA — `--filesystem=home` is a sandbox escape hatch, not a solution.** It's the
> first thing developers reach for and the first thing reviewers push back on. If your app
> needs "access to files," the answer is the FileChooser portal, which grants access to
> exactly what the user picked, transparently, through the toolkit's normal file dialog.

**Reduce your distro-support burden**: ship one Flatpak, tell everyone else to use it, and
let volunteers maintain AUR/nixpkgs. Trying to build and test `.deb` and `.rpm` across six
distro versions is a full-time job that adds no user value in 2026.

---
