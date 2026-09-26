/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-app: the running Krypton desktop -- the core's state, the hub it talks to, the
 * settings it keeps -- and the few things a view may ask of it. The views never talk to the
 * hub themselves; they ask the app, and redraw when the state says something changed. */

#ifndef KR_APP_H
#define KR_APP_H

#include <adwaita.h>

#include "kr-discovery.h"
#include "kr-hub-client.h"
#include "kr-settings.h"
#include "kr-state.h"

G_BEGIN_DECLS

typedef struct {
    AdwApplication *application;
    KrChannel channel;
    KrState *state;
    KrSettings *settings;
    char *settings_path;
    KrHubClient *client;
    KrDiscovery *discovery;
    char *discovery_problem; /* why discovery is not running, or NULL */
    GCancellable *cancel;
    guint refresh_source;
    GtkWidget *window;
} KrApp;

/* Asks the hub for everything the views show; the answers land in app->state. */
void kr_app_refresh(KrApp *app);
/* The budget of one project (the Budgets page asks when a project is chosen). */
void kr_app_refresh_budget(KrApp *app, const char *project_id);
/* Answers a gate with `value` (see kr-answer.h); says the outcome in a toast. */
void kr_app_answer(KrApp *app, const KrGate *gate, const char *value);
/* Points the app at a hub; NULL host means this computer's. Saves the choice. */
void kr_app_use_hub(KrApp *app, const char *host, guint16 port);
/* Applies the theme in app->settings through AdwStyleManager (saving is the caller's). */
void kr_app_apply_theme(KrApp *app);
void kr_app_save_settings(KrApp *app);
/* A short message at the bottom of the window. */
void kr_app_toast(KrApp *app, const char *text);

G_END_DECLS

#endif /* KR_APP_H */
