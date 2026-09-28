---
id: skill-9-the-desktop-idioms-what-makes-an-app-feel-native-39eaf1e604
purpose: 9 the desktop idioms what makes an app feel native
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-cross-platform-and-architecture/SKILL.md
requires: ["skill-8-application-architecture-and-patterns-1b88ff0dc8"]
links: []
---

## §9. The Desktop Idioms — what makes an app feel native

This section is the difference between "a program with a window" and "a Mac app" / "a
GNOME app." It is mostly unglamorous and almost entirely what users notice.

### 9.1 Windows

- **Restore state**: size, position, which display, scroll offset, open documents,
  sidebar width, selected tab. macOS: `NSWindow.setFrameAutosaveName` /
  `@SceneStorage`; Linux: persist to `$XDG_STATE_HOME` yourself (Wayland will not let
  you set absolute position — restore *size* and let the compositor place it).
- **Multi-window is the norm on desktop**, not an edge case. Two documents open side by
  side must not share mutable state.
- **Minimum sizes** that are actually usable, and **resizability** that reflows rather
  than clips.
- **Multi-monitor**: different scale factors per display, windows dragged between them
  mid-render, monitors disconnected while a window is on them. Test all three.

### 9.2 Menus and keyboard

**[PLATFORM] The macOS menu bar is a contract.** Users expect: an App menu with
About/Settings(⌘,)/Services/Hide/Quit(⌘Q); File with New(⌘N)/Open(⌘O)/Close(⌘W)/Save(⌘S);
Edit with Undo(⌘Z)/Redo(⇧⌘Z)/Cut/Copy/Paste/Select All; a Window menu with
Minimize(⌘M)/Zoom and the window list; a Help menu with searchable help. **Every command
in your app should be in a menu**, even if it's also a toolbar button — that's how Help
search and accessibility find it, and how power users discover shortcuts.

**[PLATFORM] On Linux, menu conventions are contested.** GNOME's HIG moved away from menu
bars toward header bars with a hamburger menu; KDE retains traditional menu bars. If you
use libadwaita you follow GNOME; if you use Qt/KDE you follow the traditional model. Either
is defensible; **inconsistency within your own app is not.**

**Keyboard, everywhere [UNIVERSAL]:**
- Full keyboard navigation: Tab order that matches visual order, Escape closes/cancels,
  Enter activates the default, arrow keys move within lists/grids.
- Visible focus indicators. (Removing the focus ring because it's "ugly" is an
  accessibility regression; style it instead.)
- Don't steal system shortcuts. On Linux, don't grab Super/Meta.
- Platform modifier differences: ⌘ on macOS vs Ctrl on Linux, ⌥ vs Alt, and — the one
  people always miss — **Home/End/PageUp/PageDown and word-movement semantics differ**
  (⌥← vs Ctrl+←, ⌘← vs Home).

### 9.3 Files, drag & drop, clipboard

- **Use the platform file dialog.** On macOS, `NSOpenPanel`/`fileImporter`. On Linux, the
  **FileChooser portal** — even if you're not sandboxed, because it gives the user their
  desktop's real dialog, with their bookmarks and recent files. A custom file browser is
  almost always a mistake.
- **Drag & drop both ways.** Accept drops from Finder/Files; support dragging *out* to
  other apps. Declare the right UTIs (macOS) / MIME types (Linux).
- **Clipboard**: offer multiple representations (rich text *and* plain text; image *and*
  file reference). Respect that on Linux the clipboard lives in the source app — copying
  and then quitting loses the data unless a clipboard manager is running.
- **Recent files**: macOS `NSDocumentController` handles it; Linux uses
  `GtkRecentManager` / the `recently-used.xbel` spec.

### 9.4 Appearance: dark mode, HiDPI, theming

- **Dark mode**: use **semantic colors** (`NSColor.labelColor`, `Color.primary`,
  GTK's `@theme_fg_color`, Qt's palette roles), never hardcoded hex. React to live
  changes (macOS: `NSApp.effectiveAppearance` KVO / SwiftUI `@Environment(\.colorScheme)`;
  Linux: the **Settings portal**'s `color-scheme` key, which works for sandboxed apps too).
- **HiDPI**: ship vector assets or @2x/@3x rasters; never assume integer scale factors
  (fractional scaling is normal on Linux); test at 100%, 125%, 150%, 200%, and with two
  displays at different scales.
- **Reduce Motion / Reduce Transparency / Increase Contrast**: honour them. On macOS these
  are accessibility settings with APIs; on Linux, `gtk-enable-animations` and the
  high-contrast theme.
- **[CONTESTED] Linux theming.** Users expect apps to follow their system theme; libadwaita
  apps largely don't, and Flatpak apps can't read host theme files from inside the sandbox
  without an explicit runtime. GNOME's position is that arbitrary restyling breaks apps and
  that the accent-color/light-dark API is the supported surface. Users' position is that
  their desktop should look coherent. There is no resolution; know that you will receive
  issues about it either way.

### 9.5 Internationalization

- **Externalize every user-visible string** from commit one. Retrofitting i18n is
  brutal. macOS: `String(localized:)` + String Catalogs (`.xcstrings`). Linux: `gettext`
  (`_("...")`), `.po`/`.mo`, or Qt's `tr()` + Linguist. Rust: `fluent`.
- **Never concatenate translated fragments.** Use format strings with positional
  arguments, because word order differs.
- **Plurals** need real plural rules (Arabic has six forms), not `if n == 1`.
- **RTL** (Arabic, Hebrew) mirrors your entire layout. Toolkits do it if you use logical
  (leading/trailing) rather than physical (left/right) constraints. Test with a
  force-RTL flag before a user tells you.
- **Locale affects more than language**: date formats, decimal separators (`,` vs `.` —
  a classic parsing bug), sort order, first day of the week, paper size (A4 vs Letter),
  and address/name formats.
- Leave ~30–40% expansion room; German is long, and truncated buttons are the visible
  symptom of a fixed-width layout.

### 9.6 Accessibility

**[UNIVERSAL] Non-negotiable, increasingly a legal requirement** (ADA/Section 508 in the
US; the **European Accessibility Act** obligations that landed in 2025 for many consumer
products in the EU). The floor:
- Every interactive element has an accessible **name**, **role**, and **value**.
- Keyboard-only operation of every feature.
- Contrast ratios ≥ 4.5:1 for body text (WCAG AA).
- Respect system font size settings; don't hardcode point sizes.
- Announce dynamic changes (macOS: `NSAccessibility.post(element:notification:)`;
  ARIA-live equivalents in web shells).

**Testing**: macOS → **VoiceOver** (⌘F5) and Accessibility Inspector (bundled with Xcode).
Linux → **Orca** plus Accerciser to inspect the AT-SPI tree. Web shells → the browser's
accessibility tree devtools. **Custom-drawn UI has zero accessibility unless you build
it** — this is the strongest practical argument for native widget toolkits.

### 9.7 Performance targets that users perceive

| Metric | Target | Why |
|---|---|---|
| Cold launch to interactive | < 1 s (macOS), < 2 s | Beyond this it "feels slow" |
| Frame time | < 16 ms (60 Hz), < 8 ms (120 Hz ProMotion) | Dropped frames read as jank |
| Input → visible response | < 100 ms | Perceived as instantaneous |
| Any operation > 1 s | Must show progress | Otherwise "it froze" |
| Any operation > 10 s | Must be cancellable + backgroundable | |
| Idle CPU | ~0% | A desktop app that burns CPU idle drains laptops and gets uninstalled |
| Idle RAM | As low as the framework allows | The most common complaint about Electron apps |

**The idle-CPU point deserves emphasis.** Timers that fire every 100 ms "just in case",
animations that never stop, polling loops, and immediate-mode GUIs that re-render
continuously all produce measurable battery drain. Use event-driven updates and pause work
when the window isn't visible (macOS: `occlusionState`; Wayland: `frame` callbacks stop
for hidden surfaces — respect them rather than rendering blind).
