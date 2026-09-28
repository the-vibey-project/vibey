---
id: skill-6-wayland-and-x11-9c7ace5e9b
purpose: 6 wayland and x11
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-linux-platform/SKILL.md
requires: ["skill-5-linux-ui-toolkits-28f8c97fc2"]
links: []
---

## §6. Wayland and X11

### 6.1 The state of the transition (2026) — this changed recently

- **GNOME removed X11 session support**: the X11 session was disabled by default in
  GNOME 49, and the X11 backend code was **removed from Mutter**, with GNOME 50 (March
  2026) shipping with no X11 code at all.
- **KDE Plasma will be Wayland-only in Plasma 6.8**, expected **October 2026**; the Plasma
  X11 session is supported into **early 2027** for 6.7 users. KDE's stated rationale: the
  vast majority of Plasma users are already on Wayland and many distros already dropped
  the X11 session independently.
- Distros moved first in several cases: **Fedora 43** and **Ubuntu 25.10** already ship
  without a GNOME X11 session.
- Other desktops lag: **XFCE 4.20** added initial Wayland support (using labwc as a
  stop-gap; xfwm4 is not yet a compositor); LXQt is further along than expected; Cinnamon
  and MATE are behind.
- **Xorg is not abandoned but its feature development is halted** — the same maintainers
  fix security issues; new capability work happens in Wayland. **XLibre** is a fork with
  more active development, of contested provenance, adopted by a small number of distros.
- **X11 applications keep working** through **XWayland**. Dropping the X11 *session* is not
  dropping X11 *apps*.

**[UNIVERSAL, practical] Your app must work under Wayland in 2026.** Testing only on X11 is
now testing on a legacy path.

### 6.2 What Wayland takes away, and what replaces it

This is the porting checklist. Under Wayland, a client **cannot**, by design:

| X11 capability | Wayland status | Replacement |
|---|---|---|
| Read other windows' pixels (screenshot/capture) | Forbidden | **ScreenCast portal** → PipeWire stream |
| Global hotkeys | Not in core | **GlobalShortcuts portal**, or compositor-specific |
| Set absolute window position | Forbidden | Compositor decides. `xdg-positioner` for popups only |
| Query/set the pointer position | Forbidden | Relative motion only (pointer-constraints for games) |
| Inject input into other apps | Forbidden | **RemoteDesktop portal**, **libEI** |
| Read the clipboard without focus | Forbidden | `wl_data_device`, requires focus/user action |
| Override-redirect windows | No | `xdg-shell` roles: toplevel, popup; `layer-shell` for panels |
| `XTest` automation | No | libEI / portal, or compositor-specific test protocols |

> **⚠️ GOTCHA — this list *is* the port.** If your app does screen capture, global
> hotkeys, remote control, window positioning, or input automation, "porting to Wayland"
> is not a rendering change — it's replacing those features with portal-mediated,
> user-consenting equivalents that have different UX (a permission prompt, a picker
> dialog). Budget for the UX redesign, not just the code.

**Server-side vs client-side decorations (SSD/CSD)** is a long-running friction point:
GNOME/Mutter prefers CSD (the app draws its own titlebar — that's what a GTK `HeaderBar`
is); KDE supports SSD via the `xdg-decoration` protocol. An app that assumes one gets
either a double titlebar or none. Toolkits handle this; hand-rolled Wayland clients must
negotiate it.

**Fractional scaling**: `wp_fractional_scale_v1` lets clients render at a fractional
buffer scale instead of rendering at 2× and downscaling (which is blurry). Modern GTK4/Qt6
support it; older toolkits and XWayland clients often don't, which is why "text is blurry
at 125%" is still a live complaint.

**Remote desktop is the current genuine regression.** GNOME and KDE offer RDP-based remote
desktop; many third-party tools require someone physically present to accept the
connection because of Wayland's permission model. TigerVNC has shipped a Wayland-first VNC
server. If your product does unattended remote access, investigate carefully — this is not
solved to X11 parity.
