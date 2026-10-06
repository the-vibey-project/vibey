/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-workflows-client.h"

/* ---- one route ------------------------------------------------------------------------- */

typedef struct {
    KrHubClient *client; /* the caller's: alive until the call finishes */
    guint status;        /* the hub's refusal status, or 0 when nothing answered */
} Call;

/* A hub client's failure, said as a workflows failure a person can act on. A cancellation
 * stays what it is. */
static GError *
workflows_error(const KrHubEndpoint *endpoint, GError *failure, guint status, const char *detail)
{
    if (g_error_matches(failure, KR_HUB_ERROR, KR_HUB_ERROR_FINGERPRINT))
        return g_error_new(KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_FINGERPRINT,
                           "The hub at %s did not show the certificate krypton paired with, so "
                           "nothing was sent to it. (%s)",
                           endpoint->host, failure->message);
    if (g_error_matches(failure, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED)) {
        g_autofree char *message = kr_workflows_refusal_message(status, detail);
        return g_error_new_literal(KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_REFUSED, message);
    }
    if (g_error_matches(failure, KR_HUB_ERROR, KR_HUB_ERROR_TRANSPORT))
        return g_error_new(KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_UNREACHABLE,
                           "No hub answers at %s:%u. Is `vibey serve` running there? (%s)",
                           endpoint->host, endpoint->port, failure->message);
    if (failure->domain == KR_HUB_ERROR)
        return g_error_new_literal(KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_COMMAND,
                                   failure->message);
    return g_error_copy(failure);
}

static void
on_called(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    g_autoptr(GTask) task = data;
    Call *call = g_task_get_task_data(task);
    g_autofree char *detail = NULL;
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) body =
        kr_hub_client_call_finish_full(call->client, result, &call->status, &detail, &error);
    if (body == NULL) {
        g_task_return_error(task, workflows_error(kr_hub_client_endpoint(call->client), error,
                                                  call->status, detail));
        return;
    }
    gsize size = 0;
    const char *text = g_bytes_get_data(body, &size);
    KrWorkflowRun *run = kr_workflow_run_parse(text, (gssize) size, &error);
    if (run == NULL) {
        g_task_return_error(task, g_steal_pointer(&error));
        return;
    }
    g_task_return_pointer(task, run, (GDestroyNotify) kr_workflow_run_free);
}

static void
call(KrHubClient *client, KrHubRoute route, const char *id, const char *body, gpointer tag,
     GCancellable *cancellable, GAsyncReadyCallback callback, gpointer user_data)
{
    GTask *task = g_task_new(NULL, cancellable, callback, user_data);
    g_task_set_source_tag(task, tag);
    Call *state = g_new0(Call, 1);
    state->client = client;
    g_task_set_task_data(task, state, g_free);
    kr_hub_client_call_async(client, route, NULL, id, body, cancellable, on_called, task);
}

void
kr_workflows_start_async(KrHubClient *client, const char *const *argv,
                         GCancellable *cancellable, GAsyncReadyCallback callback,
                         gpointer user_data)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *body = kr_workflows_run_body(argv, &error);
    if (body == NULL) {
        GTask *task = g_task_new(NULL, cancellable, callback, user_data);
        g_task_set_source_tag(task, kr_workflows_start_async);
        g_task_return_error(task, g_steal_pointer(&error));
        g_object_unref(task);
        return;
    }
    call(client, KR_HUB_ROUTE_WORKFLOW_RUNS, NULL, body, kr_workflows_start_async, cancellable,
         callback, user_data);
}

KrWorkflowRun *
kr_workflows_start_finish(GAsyncResult *result, GError **error)
{
    return g_task_propagate_pointer(G_TASK(result), error);
}

void
kr_workflows_get_async(KrHubClient *client, const char *request_id, GCancellable *cancellable,
                       GAsyncReadyCallback callback, gpointer user_data)
{
    call(client, KR_HUB_ROUTE_WORKFLOW_RUN, request_id, NULL, kr_workflows_get_async,
         cancellable, callback, user_data);
}

KrWorkflowRun *
kr_workflows_get_finish(GAsyncResult *result, GError **error)
{
    return g_task_propagate_pointer(G_TASK(result), error);
}

/* ---- following a run to its end -------------------------------------------------------- */

typedef struct {
    KrHubClient *client; /* the run's own, from a copy of the endpoint */
    KrWorkflowRun *last; /* the hub's latest answer */
    guint interval_ms;
    guint limit_ms;
    gint64 started; /* monotonic microseconds */
    KrWorkflowsProgress progress;
    gpointer progress_data;
    /* Only while waiting between polls: the timer, and the cancellable's own source, so a
     * cancellation ends the run at once rather than at the next poll. Each holds a reference
     * to the task; whichever fires first removes the other. */
    GSource *wait;
    GSource *cancelled;
} Runner;

static void
drop_source(GSource **source)
{
    if (*source == NULL)
        return;
    g_source_destroy(*source);
    g_clear_pointer(source, g_source_unref);
}

static void
runner_free(Runner *runner)
{
    drop_source(&runner->wait);
    drop_source(&runner->cancelled);
    kr_hub_client_free(runner->client);
    kr_workflow_run_free(runner->last);
    g_free(runner);
}

/* What a poll that failed this way means: wait it out (the hub was not there, too many
 * requests, GitHub could not be read), or stop. */
static gboolean
passing(GError *error, guint status)
{
    if (g_error_matches(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_UNREACHABLE))
        return TRUE;
    return g_error_matches(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_REFUSED) &&
           (status == 429 || status == 502);
}

static void wait_then_poll(GTask *task);

static void
on_polled(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    g_autoptr(GTask) task = data;
    Runner *runner = g_task_get_task_data(task);
    guint status = ((Call *) g_task_get_task_data(G_TASK(result)))->status;
    g_autoptr(GError) error = NULL;
    g_autoptr(KrWorkflowRun) run = kr_workflows_get_finish(result, &error);
    if (run == NULL) {
        if (passing(error, status))
            wait_then_poll(task);
        else
            g_task_return_error(task, g_steal_pointer(&error));
        return;
    }
    kr_workflow_run_free(runner->last);
    runner->last = g_steal_pointer(&run);
    if (runner->progress != NULL)
        runner->progress(runner->last, runner->progress_data);
    if (kr_workflow_run_finished(runner->last)) {
        g_task_return_pointer(task, kr_workflow_run_copy(runner->last),
                              (GDestroyNotify) kr_workflow_run_free);
        return;
    }
    wait_then_poll(task);
}

static gboolean
on_wait_over(gpointer data)
{
    GTask *task = data;
    Runner *runner = g_task_get_task_data(task);
    g_clear_pointer(&runner->wait, g_source_unref); /* it is removed by returning REMOVE */
    drop_source(&runner->cancelled);
    kr_workflows_get_async(runner->client, runner->last->request_id,
                           g_task_get_cancellable(task), on_polled, g_object_ref(task));
    return G_SOURCE_REMOVE;
}

static gboolean
on_cancelled(GCancellable *cancellable, gpointer data)
{
    (void) cancellable;
    g_autoptr(GTask) task = g_object_ref(data);
    Runner *runner = g_task_get_task_data(task);
    g_clear_pointer(&runner->cancelled, g_source_unref);
    drop_source(&runner->wait);
    g_task_return_error_if_cancelled(task);
    return G_SOURCE_REMOVE;
}

static GSource *
attach(GTask *task, GSource *source, GSourceFunc function)
{
    g_source_set_callback(source, function, g_object_ref(task), g_object_unref);
    g_source_attach(source, g_task_get_context(task));
    return source;
}

/* Stops when the limit is reached; otherwise asks again after the interval. */
static void
wait_then_poll(GTask *task)
{
    Runner *runner = g_task_get_task_data(task);
    gint64 elapsed_ms = (g_get_monotonic_time() - runner->started) / 1000;
    if (elapsed_ms >= runner->limit_ms) {
        g_autofree char *said = kr_workflows_timeout_message(runner->last,
                                                             runner->limit_ms / 1000);
        g_task_return_new_error(task, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_TIMEOUT, "%s",
                                said);
        return;
    }
    runner->wait = attach(task, g_timeout_source_new(runner->interval_ms), on_wait_over);
    GCancellable *cancellable = g_task_get_cancellable(task);
    if (cancellable != NULL)
        runner->cancelled = attach(task, g_cancellable_source_new(cancellable),
                                   G_SOURCE_FUNC(on_cancelled));
}

static void
on_started(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    g_autoptr(GTask) task = data;
    Runner *runner = g_task_get_task_data(task);
    g_autoptr(GError) error = NULL;
    runner->last = kr_workflows_start_finish(result, &error);
    if (runner->last == NULL) {
        g_task_return_error(task, g_steal_pointer(&error));
        return;
    }
    if (runner->progress != NULL)
        runner->progress(runner->last, runner->progress_data);
    if (kr_workflow_run_finished(runner->last)) {
        g_task_return_pointer(task, kr_workflow_run_copy(runner->last),
                              (GDestroyNotify) kr_workflow_run_free);
        return;
    }
    wait_then_poll(task);
}

void
kr_workflows_run_async(const KrHubEndpoint *endpoint, const char *const *argv,
                       const KrWorkflowsPolling *polling, KrWorkflowsProgress progress,
                       gpointer progress_data, GCancellable *cancellable,
                       GAsyncReadyCallback callback, gpointer user_data)
{
    GTask *task = g_task_new(NULL, cancellable, callback, user_data);
    g_task_set_source_tag(task, kr_workflows_run_async);
    Runner *runner = g_new0(Runner, 1);
    runner->client = kr_hub_client_new(endpoint, 0);
    runner->interval_ms = polling != NULL && polling->interval_ms != 0
                              ? polling->interval_ms
                              : KR_WORKFLOWS_POLL_SECONDS * 1000;
    runner->limit_ms = polling != NULL && polling->limit_ms != 0
                           ? polling->limit_ms
                           : KR_WORKFLOWS_LIMIT_SECONDS * 1000;
    runner->started = g_get_monotonic_time();
    runner->progress = progress;
    runner->progress_data = progress_data;
    g_task_set_task_data(task, runner, (GDestroyNotify) runner_free);
    kr_workflows_start_async(runner->client, argv, cancellable, on_started, task);
}

KrWorkflowRun *
kr_workflows_run_finish(GAsyncResult *result, GError **error)
{
    return g_task_propagate_pointer(G_TASK(result), error);
}
