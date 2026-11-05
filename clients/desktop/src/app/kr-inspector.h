/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-inspector: right-hand inspector panel matching the frontier AI desktop app.
 *
 * Displays:
 * - Environment: host ("This computer" / IP), repo path, git branch & worktree, Remote Control toggle.
 * - Context: active context window budget & level bar.
 * - Connectors: active tools / MCP servers and authentication status.
 * - Changes: working tree file/line diff metrics (+lines, -lines) with Create PR button. */

#ifndef KR_INSPECTOR_H
#define KR_INSPECTOR_H

#include <adwaita.h>
#include "kr-app.h"

G_BEGIN_DECLS

GtkWidget *kr_inspector_new(KrApp *app);

void kr_inspector_refresh(GtkWidget *inspector);

G_END_DECLS

#endif /* KR_INSPECTOR_H */
