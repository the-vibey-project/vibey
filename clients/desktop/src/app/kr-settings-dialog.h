/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-settings-dialog: multi-category Settings modal dialog matching the frontier AI desktop app. */

#ifndef KR_SETTINGS_DIALOG_H
#define KR_SETTINGS_DIALOG_H

#include <adwaita.h>
#include "kr-app.h"

G_BEGIN_DECLS

void kr_settings_dialog_present(GtkWidget *parent_window, KrApp *app);

G_END_DECLS

#endif /* KR_SETTINGS_DIALOG_H */
