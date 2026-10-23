/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* No tray on this build: the window closes as a window does. */
#include "kr-tray-host.h"

gboolean
kr_tray_supported(void)
{
    return FALSE;
}

KrTray *
kr_tray_new(const char *app_id, const char *name, KrTrayActivate activate, gpointer user_data)
{
    (void) app_id;
    (void) name;
    (void) activate;
    (void) user_data;
    return NULL;
}

void
kr_tray_show(KrTray *tray, const KrTrayModel *model)
{
    (void) tray;
    (void) model;
}

gboolean
kr_tray_ready(const KrTray *tray)
{
    (void) tray;
    return FALSE;
}

void
kr_tray_free(KrTray *tray)
{
    (void) tray;
}
