---
id: skill-4-linux-desktop-architecture-ece1614b4a
purpose: 4 linux desktop architecture
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-linux-platform/SKILL.md
requires: []
links: ["skill-5-linux-ui-toolkits-28f8c97fc2"]
---

## §4. Linux Desktop Architecture

### 4.1 The stack — and why "Linux" isn't one platform

```
┌─────────────────────────────────────────────────────────┐
│ Your app: GTK4 / Qt6 / Electron / Tauri / SDL / raw      │
├─────────────────────────────────────────────────────────┤
│ Toolkit + desktop integration: libadwaita / KDE Frameworks│
│ XDG Desktop Portals (D-Bus) ── the sandbox-safe API       │
├─────────────────────────────────────────────────────────┤
│ Session services: D-Bus, systemd --user, PipeWire,        │
│ PolicyKit, UPower, NetworkManager, AT-SPI/Newton (a11y)   │
├─────────────────────────────────────────────────────────┤
│ Display: Wayland compositor (Mutter/KWin/wlroots/COSMIC)  │
│          + XWayland for legacy X11 clients                │
├─────────────────────────────────────────────────────────┤
│ Graphics: Mesa, DRM/KMS, GBM, Vulkan/OpenGL               │
├─────────────────────────────────────────────────────────┤
│ Kernel: Linux, evdev/libinput, udev                       │
└─────────────────────────────────────────────────────────┘
```

**[UNIVERSAL for Linux] The single most useful mental model: there is no vendor, only
specs.** freedesktop.org publishes the conventions; GNOME, KDE, and everyone else
implement them with varying completeness. Your app's job is to speak the specs, not to
target a desktop environment. Apps that hardcode "if GNOME then X" age badly.

**The specs you must actually know:**

| Spec | What it governs | Practical impact |
|---|---|---|
| **XDG Base Directory** | Where files go | `$XDG_CONFIG_HOME` (`~/.config`), `$XDG_DATA_HOME` (`~/.local/share`), `$XDG_CACHE_HOME` (`~/.cache`), `$XDG_STATE_HOME` (`~/.local/state`), `$XDG_RUNTIME_DIR` (`/run/user/UID`, tmpfs, cleared at logout) |
| **Desktop Entry** | `.desktop` files | How your app appears in menus/launchers, handles MIME types, declares actions |
| **Icon Theme** | Icon lookup | Ship SVG at `hicolor/scalable/apps/<app-id>.svg`; never hardcode a path |
| **AppStream (MetaInfo)** | App store metadata | Required by Flathub and by GNOME Software/Discover to show your app at all |
| **MIME (shared-mime-info)** | File types | Custom formats need a MIME XML + magic bytes |
| **Notifications** | `org.freedesktop.Notifications` | D-Bus, not a toolkit API |
| **Autostart** | `~/.config/autostart/*.desktop` | Launch at login (or use a systemd user unit) |
| **Secret Service** | Credential storage | `libsecret` → GNOME Keyring / KWallet. **The Keychain equivalent.** |
| **XDG Desktop Portal** | Sandboxed access to host resources | §12.3 → `desktop-packaging-security-and-testing` — increasingly the *only* way to do screen capture, and the *best* way to do file dialogs |
| **Trash** | `~/.local/share/Trash` | Don't `unlink()` user files; use `gio trash` semantics |

```ini
# /usr/share/applications/com.example.MyApp.desktop  (or ~/.local/share/applications)
# The filename SHOULD equal your app ID — Wayland window matching depends on it.
[Desktop Entry]
Type=Application
Name=My App
Comment=Short one-line description shown in launchers
Exec=myapp %U
Icon=com.example.MyApp
Terminal=false
Categories=Utility;TextEditor;
MimeType=text/plain;application/x-myformat;
StartupNotify=true
StartupWMClass=com.example.MyApp
Keywords=notes;editor;markdown;
X-GNOME-UsesNotifications=true

[Desktop Action NewWindow]
Name=New Window
Exec=myapp --new-window
```

> **⚠️ GOTCHA — the app ID must match everywhere.** Your D-Bus name, `.desktop` filename,
> icon filename, AppStream `<id>`, Flatpak app ID, GTK `Application` `application-id`, and
> (critically) the Wayland `app_id` your toolkit reports must all be the same reverse-DNS
> string. When they don't match, the symptom is: your window shows a generic icon in the
> dock/overview, notifications aren't attributed to your app, and "focus existing window"
> doesn't work. This is the single most common Linux packaging bug and it's invisible in
> development.

```xml
<!-- /usr/share/metainfo/com.example.MyApp.metainfo.xml — required for Flathub -->
<component type="desktop-application">
  <id>com.example.MyApp</id>
  <name>My App</name>
  <summary>Edit notes quickly</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <description><p>Longer description. Shown in software centres.</p></description>
  <launchable type="desktop-id">com.example.MyApp.desktop</launchable>
  <screenshots>
    <screenshot type="default"><image>https://example.com/shot1.png</image></screenshot>
  </screenshots>
  <content_rating type="oars-1.1"/>
  <releases>
    <release version="1.2.0" date="2026-08-01">
      <description><p>Fixed the thing.</p></description>
    </release>
  </releases>
  <branding><color type="primary" scheme_preference="light">#3584e4</color></branding>
</component>
```

### 4.2 D-Bus — the desktop's nervous system

Two buses: the **system bus** (root services: NetworkManager, UPower, logind, UDisks) and
the **session bus** (per-login: notifications, portals, your app, media players).

Anatomy: **bus name** (`org.freedesktop.Notifications`) → **object path**
(`/org/freedesktop/Notifications`) → **interface** (`org.freedesktop.Notifications`) →
**method/signal/property**.

```bash
# The three commands that make D-Bus tractable
busctl --user list                              # what's on the session bus
busctl --user introspect org.freedesktop.portal.Desktop /org/freedesktop/portal/desktop
gdbus call --session --dest org.freedesktop.Notifications \
  --object-path /org/freedesktop/Notifications \
  --method org.freedesktop.Notifications.Notify \
  "MyApp" 0 "dialog-information" "Title" "Body" "[]" "{}" 5000
```

**Why your app should own a D-Bus name**: single-instance enforcement, `Activate`/`Open`
actions from the launcher, MPRIS media control, and the `org.freedesktop.Application`
interface. GTK's `GApplication` and Qt's `QDBusConnection` both give you this. It is also
how "click the launcher again and raise the existing window" works.

**systemd user units** (`~/.config/systemd/user/`) are the modern way to run a background
helper, with socket activation, restart policy, and journal integration — the launchd
equivalent, and preferable to a stray autostart `.desktop` for anything daemon-shaped.

### 4.3 Audio/video: PipeWire

**PipeWire has replaced PulseAudio and JACK** as the default on essentially all modern
distributions, handling both audio and video streams with low latency. What app developers
need:
- Use a **high-level API** (GStreamer, libpulse compatibility, or PipeWire's own) rather
  than talking to ALSA directly.
- **Screen capture on Wayland goes through PipeWire** via the ScreenCast portal — there is
  no `XShmGetImage` equivalent. This is the #1 porting surprise for screenshot, screen
  recording, and video-conferencing apps.
- **WirePlumber** is the session manager (policy); PipeWire is the transport. Bugs are
  usually WirePlumber policy, not PipeWire.
- PipeWire requires an active **D-Bus session bus**. In minimal WM setups without one,
  everything silently fails — `dbus-run-session` is the fix.

### 4.4 Accessibility on Linux — the honest picture

**[UNIVERSAL] Build for accessibility from the start.** On Linux specifically:
- **AT-SPI2** over D-Bus is the current accessibility API. **Orca** is the dominant screen
  reader; **Odilia** is a newer entrant. GTK4 rewrote its a11y layer to talk to the AT-SPI
  registry directly; KDE Plasma 6 added AT-SPI2 support in 6.0.
- **AT-SPI has real architectural problems under Wayland and sandboxing**: the accessibility
  tree is severed from the windowing system (so an AT can't verify an event came from the
  focused app), and its "chatty IPC" requires many round trips, producing latency that
  makes a screen reader unresponsive when the app is merely busy.
- **Newton** is the in-progress Wayland-native replacement (built on AccessKit, with
  Wayland protocol and Mutter/GTK work), specifically designed so **Flatpak apps get
  accessibility without punching a hole in the sandbox for the AT-SPI bus**. It is
  experimental as of 2026 — track it, don't depend on it.
- **The field is chronically under-resourced** — credible assessments put the number of
  people working significantly on Linux a11y in the single digits historically. This means:
  use your toolkit's standard widgets (which carry a11y for free), don't roll custom
  controls without accessible implementations, and test with Orca yourself, because nobody
  else will.

---
