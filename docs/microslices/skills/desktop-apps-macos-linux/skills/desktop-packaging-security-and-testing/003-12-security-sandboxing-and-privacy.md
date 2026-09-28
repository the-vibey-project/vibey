---
id: skill-12-security-sandboxing-and-privacy-fcb530a478
purpose: 12 security sandboxing and privacy
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-packaging-security-and-testing/SKILL.md
requires: ["skill-11-auto-update-5e76479800"]
links: ["skill-13-testing-debugging-and-ci-9f8b60962a"]
---

## §12. Security, Sandboxing, and Privacy

### 12.1 macOS: the three separate systems people conflate

They are independent, and you need all three straight:

1. **Code signing** — proves *who* built it. Developer ID or Apple Distribution certificate.
2. **Entitlements** — declare *what it may do*. Sandbox on/off plus each specific capability.
3. **Notarization** — proves *Apple scanned it* for malware. Required for anything
   distributed outside the App Store since macOS 10.15. **Requires Hardened Runtime.**

Plus, at runtime:
- **Hardened Runtime** — blocks code injection, DYLD hijacking, and unsigned executable
  memory. Mandatory for notarization. This is what breaks JIT-based runtimes unless you
  add the corresponding entitlement.
- **App Sandbox** — kernel-enforced confinement to your container. **Required for the Mac
  App Store; optional (and recommended) outside it.**
- **TCC (Transparency, Consent, Control)** — the per-resource consent database (camera,
  mic, screen recording, Documents/Desktop/Downloads, Contacts, Automation…). Independent
  of the sandbox: **a non-sandboxed app is still subject to TCC.**
- **Gatekeeper** — checks signature + notarization ticket at first launch, tracks
  provenance of files written by downloaded software, and randomizes launch paths when
  necessary.

> **⚠️ GOTCHA — enabling the sandbox late is a project, not a checkbox.** It relocates
> your data directory, revokes filesystem access outside the container, breaks hardcoded
> paths, breaks direct access to other apps' data, and may break your update mechanism.
> Decide sandbox/no-sandbox before v1 and develop with it on.

### 12.2 macOS secrets

Use the **Keychain** (`kSecClass...` / the Security framework) for credentials and tokens.
Not UserDefaults, not a file in Application Support, not obfuscated in the binary. For
higher-value secrets, `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` and the Secure
Enclave (via `SecKeyCreateRandomKey` with `kSecAttrTokenIDSecureEnclave`).

### 12.3 Linux: portals are the model

**XDG Desktop Portals** are the Linux answer to entitlements/TCC: a set of D-Bus
interfaces at `org.freedesktop.portal.Desktop` that mediate access to resources outside an
app's sandbox, with a user-controlled permission system and per-desktop backends
(`xdg-desktop-portal-gnome`, `-kde`, `-wlr`, and newer generic backends for COSMIC/niri).

**[UNIVERSAL for Linux] Use portals even if you are not sandboxed.** The portal docs say
this explicitly, and the reasons are practical:
- Free desktop integration: the FileChooser portal gives you *the user's own* file dialog.
- Some capabilities are **only** available via portals — screen capture and screenshots on
  Wayland go through the ScreenCast/Screenshot portals; some desktops expose no other path.
- Your app works identically packaged and unpackaged.

Key portals: FileChooser, OpenURI, ScreenCast (v6), Screenshot, RemoteDesktop, Camera,
Print, Notification, Settings (theme/accent/color-scheme), Inhibit (prevent sleep),
GlobalShortcuts, Background/Autostart, Secret, Account, Location, Clipboard, Trash.

GTK3/GTK4 and Qt5/Qt6 route through portals **transparently** for common operations —
which is why "use the toolkit's file dialog" is usually the whole answer.

```bash
# Debugging the portal stack — the checklist that resolves most "file picker won't
# open" and "OBS can't see my screen" reports:
echo $XDG_SESSION_TYPE $XDG_CURRENT_DESKTOP
systemctl --user status xdg-desktop-portal
systemctl --user status pipewire wireplumber
journalctl --user -u xdg-desktop-portal -f
# Most common cause: multiple portal backends installed, wrong one selected for
# an interface. The fix is installing the CORRECT backend, not more backends.
```

**Linux secrets**: the **Secret Service** API (`libsecret`) → GNOME Keyring or KWallet. In
Flatpak, request `--talk-name=org.freedesktop.secrets` or use the Secret portal.

### 12.4 Supply chain and dependency risk [UNIVERSAL]

Desktop apps ship a full dependency tree to end-user machines and often run with the
user's full privileges.
- **Pin and audit dependencies**; generate an **SBOM** (SPDX/CycloneDX) per release.
- **Sign everything** with keys held in an HSM or a hosted signing service — never a key
  file on a laptop or in a repo.
- **Keep the runtime current.** An Electron app two majors behind ships known Chromium
  RCEs to your users. A Flatpak on an EOL runtime is the same problem.
- **Reproducible builds** where you can; at minimum, build in a pinned container so
  "it built on my machine" isn't part of your release process.
- The **EU Cyber Resilience Act** applies to desktop software sold into the EU: vulnerability
  and incident **reporting obligations begin 11 September 2026**, full application
  11 December 2027. If you sell a desktop app in Europe, you need an SBOM, a monitored
  vulnerability intake, and a reporting runbook — this is not a firmware-only concern.

---
