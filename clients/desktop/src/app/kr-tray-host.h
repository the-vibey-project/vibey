/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-tray-host: the tray item (the menu bar on macOS, the notification area elsewhere).
 *
 * One interface, one implementation per platform, chosen at build time (-Dtray): the macOS
 * NSStatusItem (kr-tray-macos.m), the freedesktop StatusNotifierItem (kr-tray-sni.c), or
 * none (kr-tray-none.c). What it shows is the core's KrTrayModel; a click comes back as an
 * action name. GTK 4 has no tray of its own, so this is the only place that knows one. */

#ifndef KR_TRAY_HOST_H
#define KR_TRAY_HOST_H

#include <glib.h>

#include "kr-tray.h"

G_BEGIN_DECLS

typedef struct KrTray KrTray;

/* Called on the main loop with an action name from the model ("open", "quit", ...). */
typedef void (*KrTrayActivate)(const char *action, gpointer user_data);

/* Whether this build has a tray at all (the Settings switch is shown only then). */
gboolean kr_tray_supported(void);
/* NULL when this platform has no tray or it cannot start (no session bus, say). */
KrTray *kr_tray_new(const char *app_id, const char *name, KrTrayActivate activate,
                    gpointer user_data);
/* Draws `model`. Cheap to call; the caller skips a model equal to the last one. */
void kr_tray_show(KrTray *tray, const KrTrayModel *model);
/* Whether a person can see and use the item right now. The window closes to the tray only
 * while this is TRUE: hiding it with nothing to bring it back would lose the app. */
gboolean kr_tray_ready(const KrTray *tray);
void kr_tray_free(KrTray *tray);

G_END_DECLS

#endif /* KR_TRAY_HOST_H */
