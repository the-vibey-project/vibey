---
id: skill-5-linux-ui-toolkits-28f8c97fc2
purpose: 5 linux ui toolkits
source: src/vibey_tools/skills/plugins/desktop-apps-macos-linux/skills/desktop-linux-platform/SKILL.md
requires: ["skill-4-linux-desktop-architecture-ece1614b4a"]
links: ["skill-6-wayland-and-x11-9c7ace5e9b"]
---

## §5. Linux UI Toolkits

### 5.1 GTK4 + libadwaita

**GTK 4** is the current major version (4.22.x as of mid-2026); **libadwaita** is the
separate library that supplies GNOME's design language: adaptive containers, modern
widgets (`AdwToastOverlay`, `AdwNavigationSplitView`, `AdwPreferencesPage`,
`AdwStatusPage`), and the Adwaita style.

**[CONTESTED] The GTK/libadwaita split is politically live.** GNOME's position: GTK is a
general toolkit; libadwaita is GNOME's design language layered on top, so GTK doesn't have
to encode one desktop's opinions. Critics (notably from the Mint/Cinnamon direction, and
much of the theming community): libadwaita apps resist system theming, look foreign
outside GNOME, and the split effectively makes "GTK app" mean "GNOME app." Both readings
are defensible. **Practical consequence for you:** if you use libadwaita, your app will
look excellent on GNOME and slightly alien on KDE/XFCE, and users *will* file issues about
theming. If you use plain GTK4 without libadwaita, you get more theme neutrality and less
polish.

```c
/* GTK4 + libadwaita, C. Note GtkApplication gives you D-Bus name ownership,
   single-instance, and the org.freedesktop.Application interface for free. */
#include <adwaita.h>

static void on_activate(GtkApplication *app, gpointer user_data) {
    GtkWidget *window = adw_application_window_new(app);
    gtk_window_set_default_size(GTK_WINDOW(window), 900, 600);

    GtkWidget *header = adw_header_bar_new();
    GtkWidget *toast_overlay = adw_toast_overlay_new();
    GtkWidget *content = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);

    gtk_box_append(GTK_BOX(content), header);
    gtk_box_append(GTK_BOX(content), toast_overlay);
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(window), content);
    gtk_window_present(GTK_WINDOW(window));
}

int main(int argc, char **argv) {
    /* app id MUST match .desktop filename, icon name, and AppStream id */
    AdwApplication *app = adw_application_new("com.example.MyApp",
                                              G_APPLICATION_HANDLES_OPEN);
    g_signal_connect(app, "activate", G_CALLBACK(on_activate), NULL);
    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);
    return status;
}
```

```rust
// GTK4 from Rust via gtk4-rs — increasingly the default for new GTK apps.
// Keep the gtk4 and libadwaita crate versions in lockstep; they're coupled.
use adw::prelude::*;
use adw::{Application, ApplicationWindow, HeaderBar};
use gtk::{Box as GtkBox, Orientation};

fn main() -> glib::ExitCode {
    let app = Application::builder()
        .application_id("com.example.MyApp")
        .build();
    app.connect_activate(|app| {
        let content = GtkBox::new(Orientation::Vertical, 0);
        content.append(&HeaderBar::new());
        ApplicationWindow::builder()
            .application(app)
            .default_width(900).default_height(600)
            .content(&content)
            .build()
            .present();
    });
    app.run()
}
```
Note the trend: GNOME itself is migrating components to Rust (GNOME Disks' 51 rewrite
moved UI code and libgdu utilities to Rust talking to UDisks2 via `udisks-rs`). gtk4-rs is
production-grade.

**GTK4 concepts that trip people up:** the shift from GTK3's `pack_start`/container model
to explicit `append`/single-child layout; `GtkListView`/`GtkColumnView` with
`GListModel`+factories replacing `GtkTreeView`/`GtkListStore`; CSS-based styling with GTK's
own subset (not web CSS); `GtkEventController` replacing direct event handling; and
`GtkBuilder`/`.ui` XML plus **Blueprint** (a friendlier DSL that compiles to `.ui`) for
declarative UI.

**GTK5** is not imminent; treat GTK4 as the target for the foreseeable future.

### 5.2 Qt 6

Current: **Qt 6.11.x** (6.11.1, May 2026), on a ~6-month minor cadence. **Licensing is the
decision, not the technology:**
- **LGPLv3** (most modules): free, but you must permit relinking — practically, dynamic
  linking, or shipping object files. Some modules are **GPL-only** (notably Qt Charts,
  Qt Data Visualization, and parts of the tooling), which will contaminate a proprietary
  app if you use them.
- **Commercial**: required for static linking in a closed-source product, and for LTS
  patch releases. **LTS patch releases are commercial-only**; open-source users get LTS
  branches treated as ordinary releases. Since 6.8.0, LTS support runs five years
  (three before that).
- The KDE Free Qt Foundation agreement is the backstop that keeps Qt open-source.

**Qt Widgets vs Qt Quick/QML [CONTESTED]:**
- *Widgets*: mature, native-ish look, excellent for dense desktop tools (IDEs, CAD,
  engineering software), C++ only, retained-mode. Not deprecated but not where new
  investment goes.
- *Quick/QML*: declarative, GPU-accelerated, animation-friendly, JavaScript for logic,
  designed for touch/embedded/fluid UI. Better for modern-looking apps; worse for dense
  data grids and for teams that don't want a second language in the build.
- Most desktop-tool companies still ship Widgets. Most new embedded/HMI work is Quick.

**PySide6** (official, LGPL) and **PyQt6** (Riverbank, GPL/commercial) are the Python
bindings; PySide6's licensing is friendlier for proprietary work. Note that free-threaded
(GIL-less) Python support is still being worked out because a GIL-less runtime requires
Qt's own locking against the event loop.

### 5.3 The rest

| Toolkit | Status | Use when |
|---|---|---|
| **wxWidgets** | Alive, native controls per platform | You want genuinely native widgets and C++ |
| **FLTK** | Alive, tiny | Minimal dependency footprint, simple tools |
| **Tk/Tkinter** | Alive, ancient | Python scripts that need *a* window |
| **Dear ImGui** | Thriving | Debug UIs, tools, game editors. Immediate-mode; not for consumer apps |
| **EFL/Enlightenment** | Niche | — |
| **Motif/Xt** | Legacy | Maintaining 1990s software |

---
