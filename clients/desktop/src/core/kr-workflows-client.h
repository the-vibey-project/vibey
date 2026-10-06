/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-workflows-client: running a vibey command on the repository's GitHub-hosted runners
 * through the hub, over libsoup 3 (kr-workflows.h says what the routes are).
 *
 * Two calls, one per route, made with a KrHubClient the caller keeps alive until they
 * finish; and kr_workflows_run_async, which sends the command and then follows it: it asks
 * the hub every KR_WORKFLOWS_POLL_SECONDS where the run is, says each answer through
 * `progress`, and finishes with the run once it is done or failed. After
 * KR_WORKFLOWS_LIMIT_SECONDS it stops following, with KR_WORKFLOWS_ERROR_TIMEOUT saying
 * where the run still is; the run itself goes on. A hub that does not answer one poll,
 * too many requests (429) and GitHub not being readable (502) are waited out; any other
 * refusal ends it. Cancelling `cancellable` ends it at once, with G_IO_ERROR_CANCELLED, and
 * nothing more is said through `progress`.
 *
 * Every failure is a KR_WORKFLOWS_ERROR whose message a person can act on, except a
 * cancellation, which stays G_IO_ERROR_CANCELLED. */

#ifndef KR_WORKFLOWS_CLIENT_H
#define KR_WORKFLOWS_CLIENT_H

#include <gio/gio.h>

#include "kr-hub-client.h"
#include "kr-workflows.h"

G_BEGIN_DECLS

/* POST /api/v1/workflows/runs with `argv` (the command, without `vibey` or `-w`). */
void kr_workflows_start_async(KrHubClient *client, const char *const *argv,
                              GCancellable *cancellable, GAsyncReadyCallback callback,
                              gpointer user_data);
/* The run as the hub first answered (normally queued), or NULL with an error. */
KrWorkflowRun *kr_workflows_start_finish(GAsyncResult *result, GError **error);

/* GET /api/v1/workflows/runs/{request_id}. */
void kr_workflows_get_async(KrHubClient *client, const char *request_id,
                            GCancellable *cancellable, GAsyncReadyCallback callback,
                            gpointer user_data);
KrWorkflowRun *kr_workflows_get_finish(GAsyncResult *result, GError **error);

/* How a run is followed. A field of 0 takes the default: KR_WORKFLOWS_POLL_SECONDS between
 * polls, KR_WORKFLOWS_LIMIT_SECONDS in all. */
typedef struct {
    guint interval_ms;
    guint limit_ms;
} KrWorkflowsPolling;

/* Said with every answer the hub gives about the run, the first (queued) included. */
typedef void (*KrWorkflowsProgress)(const KrWorkflowRun *run, gpointer user_data);

/* Sends `argv` to the hub at `endpoint` (copied: the run keeps its own client) and follows
 * the run to its end. `polling` NULL takes the defaults. */
void kr_workflows_run_async(const KrHubEndpoint *endpoint, const char *const *argv,
                            const KrWorkflowsPolling *polling, KrWorkflowsProgress progress,
                            gpointer progress_data, GCancellable *cancellable,
                            GAsyncReadyCallback callback, gpointer user_data);
/* The finished run (done or failed), or NULL with an error. */
KrWorkflowRun *kr_workflows_run_finish(GAsyncResult *result, GError **error);

G_END_DECLS

#endif /* KR_WORKFLOWS_CLIENT_H */
