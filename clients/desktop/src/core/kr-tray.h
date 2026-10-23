/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-tray: what the tray item (the menu bar on macOS, the notification area elsewhere) shows
 * and offers, as plain data. The platform shims (src/app/kr-tray-*.c) only draw it and report
 * a click as an action name, so everything a person reads there is decided, and tested, here.
 *
 * An action is the name of an application action ("open", "show-gates", "start-project",
 * "quit"); the app activates it exactly as the window's own menu does. */

#ifndef KR_TRAY_H
#define KR_TRAY_H

#include <glib.h>

#include "kr-state.h"

G_BEGIN_DECLS

typedef struct {
    char *label;
    char *action;
} KrTrayEntry;

typedef struct {
    gboolean attention; /* a gate waits: the item asks to be noticed */
    char *tooltip;
    GPtrArray *entries; /* KrTrayEntry*, in menu order */
} KrTrayModel;

/* The model for the state as it is now. `name` is the app's display name. */
KrTrayModel *kr_tray_model_new(KrState *state, const char *name);
void kr_tray_model_free(KrTrayModel *model);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrTrayModel, kr_tray_model_free)

/* An independent copy, for a shim that keeps what it last drew. */
KrTrayModel *kr_tray_model_copy(const KrTrayModel *model);

/* Whether two models draw the same thing, so a shim redraws only when something changed. */
gboolean kr_tray_model_equal(const KrTrayModel *a, const KrTrayModel *b);

G_END_DECLS

#endif /* KR_TRAY_H */
