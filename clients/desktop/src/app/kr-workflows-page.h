/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-workflows-page: the "Run on GitHub" page. A vibey command line, typed as it would follow
 * `vibey -w`, is sent through the hub to the repository's GitHub-hosted runners (ADR-0085)
 * and followed to its end: where it is, its GitHub run, its exit code, and what it printed.
 * The core does the work (kr-workflows-client.h); this view only says it. */

#ifndef KR_WORKFLOWS_PAGE_H
#define KR_WORKFLOWS_PAGE_H

#include "kr-app.h"

G_BEGIN_DECLS

GtkWidget *kr_workflows_page_new(KrApp *app);

/* The hub or the pairing changed: say again whether this device may run commands there. */
void kr_workflows_page_refresh(GtkWidget *page);

G_END_DECLS

#endif /* KR_WORKFLOWS_PAGE_H */
