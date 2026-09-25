/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-window: the main window. A sidebar of places (AdwNavigationSplitView, which folds to
 * one pane on a narrow window) and a page per place, each redrawn from the state. */

#ifndef KR_WINDOW_H
#define KR_WINDOW_H

#include "kr-app.h"

G_BEGIN_DECLS

/* The places, in sidebar order. Each is also a page name ("projects", "gates", ...). */
#define KR_WINDOW_PAGES 8
extern const char *const kr_window_page_names[KR_WINDOW_PAGES];

GtkWidget *kr_window_new(KrApp *app);
void kr_window_show_page(GtkWidget *window, const char *name);
void kr_window_toast(GtkWidget *window, const char *text);
/* The hubs seen on the network changed: redraw the Devices page. */
void kr_window_devices_changed(GtkWidget *window);

G_END_DECLS

#endif /* KR_WINDOW_H */
