/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* Running a command on the workflows against a real HTTP server on loopback (libsoup's own
 * SoupServer) playing the hub's two `workflows` routes: the request, every state of the run
 * the poller follows to its end, the refusals in words, the hub going away, the limit, and
 * a cancellation. */
#include <libsoup/soup.h>
#include <string.h>

#include "kr-workflows-client.h"

#define RUNS "/api/v1/workflows/runs"
#define RUN_URL "https://github.com/o/r/actions/runs/7"

/* One answer the fake hub gives: a status and a body. */
typedef struct {
    guint status;
    const char *body;
} Reply;

#define QUEUED                                                                                    \
    "{\"request_id\": \"r-12345678\", \"state\": \"queued\", \"url\": \"\", \"exit_code\": "     \
    "null, \"stdout\": \"\", \"stderr\": \"\", \"detail\": \"\"}"
#define RUNNING                                                                                   \
    "{\"request_id\": \"r-12345678\", \"state\": \"running\", \"url\": \"" RUN_URL "\", "         \
    "\"exit_code\": null, \"stdout\": \"\", \"stderr\": \"\", \"detail\": \"\"}"
#define DONE                                                                                      \
    "{\"request_id\": \"r-12345678\", \"state\": \"done\", \"url\": \"" RUN_URL "\", "            \
    "\"exit_code\": 0, \"stdout\": \"all green\\n\", \"stderr\": \"\", \"detail\": \"\"}"
#define FAILED                                                                                    \
    "{\"request_id\": \"r-12345678\", \"state\": \"failed\", \"url\": \"" RUN_URL "\", "          \
    "\"exit_code\": null, \"stdout\": \"\", \"stderr\": \"\", \"detail\": \"the runner died\"}"

typedef struct {
    SoupServer *server;
    guint16 port;
    Reply start;         /* what POST /runs answers */
    const Reply *polls;  /* what each GET /runs/{id} answers, in turn; the last repeats */
    guint n_polls;
    guint polled;        /* how many GETs came */
    char *last_method;
    char *last_path;
    char *last_body;
    char *last_auth;
} Hub;

static void
respond(SoupServerMessage *message, const Reply *reply)
{
    soup_server_message_set_status(message, reply->status, NULL);
    if (reply->body != NULL)
        soup_server_message_set_response(message, "application/json", SOUP_MEMORY_COPY,
                                          reply->body, strlen(reply->body));
}

static void
serve(SoupServer *server, SoupServerMessage *message, const char *path, GHashTable *query,
      gpointer data)
{
    (void) server;
    (void) query;
    Hub *hub = data;
    g_free(hub->last_method);
    g_free(hub->last_path);
    g_free(hub->last_body);
    g_free(hub->last_auth);
    hub->last_method = g_strdup(soup_server_message_get_method(message));
    hub->last_path = g_strdup(path);
    SoupMessageBody *body = soup_server_message_get_request_body(message);
    hub->last_body = g_strndup(body->data != NULL ? body->data : "", (gsize) body->length);
    hub->last_auth = g_strdup(soup_message_headers_get_one(
        soup_server_message_get_request_headers(message), "Authorization"));
    if (g_strcmp0(hub->last_auth, "Bearer good") != 0) {
        respond(message, &(Reply){401, "{\"detail\": \"who are you\"}"});
        return;
    }
    if (g_str_equal(path, RUNS) && g_str_equal(hub->last_method, "POST")) {
        respond(message, &hub->start);
        return;
    }
    if (g_str_has_prefix(path, RUNS "/") && g_str_equal(hub->last_method, "GET")) {
        guint turn = MIN(hub->polled, hub->n_polls - 1);
        hub->polled++;
        respond(message, &hub->polls[turn]);
        return;
    }
    soup_server_message_set_status(message, 404, NULL);
}

static void
hub_start(Hub *hub, Reply start, const Reply *polls, guint n_polls)
{
    hub->start = start;
    hub->polls = polls;
    hub->n_polls = n_polls;
    hub->server = soup_server_new(NULL, NULL);
    soup_server_add_handler(hub->server, NULL, serve, hub, NULL);
    g_autoptr(GError) error = NULL;
    g_assert_true(soup_server_listen_local(hub->server, 0, SOUP_SERVER_LISTEN_IPV4_ONLY, &error));
    g_assert_no_error(error);
    GSList *uris = soup_server_get_uris(hub->server);
    hub->port = (guint16) g_uri_get_port(uris->data);
    g_slist_free_full(uris, (GDestroyNotify) g_uri_unref);
}

static void
hub_stop(Hub *hub)
{
    if (hub->server != NULL) {
        soup_server_disconnect(hub->server);
        g_clear_object(&hub->server);
    }
    g_free(hub->last_method);
    g_free(hub->last_path);
    g_free(hub->last_body);
    g_free(hub->last_auth);
}

static KrHubEndpoint *
endpoint_for(Hub *hub)
{
    return kr_hub_endpoint_new("http", "127.0.0.1", hub->port, "good");
}

/* ---- one call -------------------------------------------------------------------------- */

typedef struct {
    KrWorkflowRun *run;
    GError *error;
    gboolean done;
} Outcome;

static void
on_started(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Outcome *outcome = data;
    outcome->run = kr_workflows_start_finish(result, &outcome->error);
    outcome->done = TRUE;
}

static void
on_got(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Outcome *outcome = data;
    outcome->run = kr_workflows_get_finish(result, &outcome->error);
    outcome->done = TRUE;
}

static void
wait_for(Outcome *outcome)
{
    while (!outcome->done)
        g_main_context_iteration(NULL, TRUE);
}

static Outcome
start(KrHubClient *client, const char *const *argv)
{
    Outcome outcome = {0};
    kr_workflows_start_async(client, argv, NULL, on_started, &outcome);
    wait_for(&outcome);
    return outcome;
}

static Outcome
get(KrHubClient *client, const char *request_id)
{
    Outcome outcome = {0};
    kr_workflows_get_async(client, request_id, NULL, on_got, &outcome);
    wait_for(&outcome);
    return outcome;
}

static void
outcome_clear(Outcome *outcome)
{
    g_clear_pointer(&outcome->run, kr_workflow_run_free);
    g_clear_error(&outcome->error);
}

static void
refused_with(Outcome *outcome, int code, const char *says)
{
    g_assert_null(outcome->run);
    g_assert_error(outcome->error, KR_WORKFLOWS_ERROR, code);
    if (strstr(outcome->error->message, says) == NULL)
        g_error("\"%s\" does not say \"%s\"", outcome->error->message, says);
    outcome_clear(outcome);
}

static const char *const STATUS_JSON[] = {"status", "--json", NULL};

static void
test_start_and_get(void)
{
    Hub hub = {0};
    const Reply polls[] = {{200, RUNNING}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    g_autoptr(KrHubEndpoint) endpoint = endpoint_for(&hub);
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 5);

    Outcome started = start(client, STATUS_JSON);
    g_assert_no_error(started.error);
    g_assert_cmpstr(started.run->request_id, ==, "r-12345678");
    g_assert_cmpint(started.run->state, ==, KR_WORKFLOW_QUEUED);
    g_assert_cmpstr(hub.last_method, ==, "POST");
    g_assert_cmpstr(hub.last_path, ==, RUNS);
    g_assert_cmpstr(hub.last_body, ==, "{\"argv\":[\"status\",\"--json\"]}");
    g_assert_cmpstr(hub.last_auth, ==, "Bearer good");
    outcome_clear(&started);

    Outcome got = get(client, "r-12345678");
    g_assert_no_error(got.error);
    g_assert_cmpint(got.run->state, ==, KR_WORKFLOW_RUNNING);
    g_assert_cmpstr(got.run->url, ==, RUN_URL);
    g_assert_cmpstr(hub.last_method, ==, "GET");
    g_assert_cmpstr(hub.last_path, ==, RUNS "/r-12345678");
    outcome_clear(&got);

    /* Nothing to send is never sent; an empty request id names no route. */
    Outcome empty = start(client, (const char *const[]){NULL});
    refused_with(&empty, KR_WORKFLOWS_ERROR_COMMAND, "Type a vibey command");
    Outcome no_id = get(client, "");
    refused_with(&no_id, KR_WORKFLOWS_ERROR_COMMAND, "needs an id");
    hub_stop(&hub);
}

static void
start_refused(guint status, const char *body, int code, const char *says)
{
    Hub hub = {0};
    const Reply polls[] = {{200, QUEUED}};
    hub_start(&hub, (Reply){status, body}, polls, G_N_ELEMENTS(polls));
    g_autoptr(KrHubEndpoint) endpoint = endpoint_for(&hub);
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 5);
    Outcome refused = start(client, STATUS_JSON);
    refused_with(&refused, code, says);
    hub_stop(&hub);
}

static void
test_refusals(void)
{
    /* The hub's own refusals of a run, as app.py words them. */
    start_refused(403, "{\"detail\": \"krypton on x may not run commands on the workflows\"}",
                  KR_WORKFLOWS_ERROR_REFUSED,
                  "(the hub said: krypton on x may not run commands on the workflows)");
    start_refused(403, "{\"detail\": \"krypton on x may not run `work` there: it needs run\"}",
                  KR_WORKFLOWS_ERROR_REFUSED, "It needs the workflows scope");
    start_refused(403,
                  "{\"detail\": \"`migrate` reaches migrations, which the hub never offers\"}",
                  KR_WORKFLOWS_ERROR_REFUSED, "migrate, budget set");
    start_refused(503, "{\"detail\": \"workflows are not enabled on this hub\"}",
                  KR_WORKFLOWS_ERROR_REFUSED,
                  "Running vibey on GitHub is not enabled on this hub (the hub said: "
                  "workflows are not enabled on this hub)");
    start_refused(422, "{\"detail\": [{\"loc\": [\"body\", \"argv\"]}]}",
                  KR_WORKFLOWS_ERROR_REFUSED, "could not take that command line.");
    start_refused(429, NULL, KR_WORKFLOWS_ERROR_REFUSED, "Too many requests");
    start_refused(502, "{\"detail\": \"GitHub refused the dispatch: 404\"}",
                  KR_WORKFLOWS_ERROR_REFUSED, "GitHub refused the run");
    /* A 2xx that is not a run is not taken for one. */
    start_refused(202, "{}", KR_WORKFLOWS_ERROR_RESPONSE, "no request_id");

    /* A device the hub does not know. */
    Hub hub = {0};
    const Reply polls[] = {{200, QUEUED}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    g_autoptr(KrHubEndpoint) stranger = kr_hub_endpoint_new("http", "127.0.0.1", hub.port, "bad");
    g_autoptr(KrHubClient) client = kr_hub_client_new(stranger, 5);
    Outcome unknown = start(client, STATUS_JSON);
    refused_with(&unknown, KR_WORKFLOWS_ERROR_REFUSED, "does not know this device");
    hub_stop(&hub);
}

static void
test_unreachable(void)
{
    /* Port 1 on loopback: nothing listens, so nothing answers. */
    g_autoptr(KrHubEndpoint) closed = kr_hub_endpoint_new("http", "127.0.0.1", 1, "good");
    g_autoptr(KrHubClient) nobody = kr_hub_client_new(closed, 5);
    Outcome silent = start(nobody, STATUS_JSON);
    refused_with(&silent, KR_WORKFLOWS_ERROR_UNREACHABLE, "No hub answers at 127.0.0.1:1");

    g_autoptr(KrHubEndpoint) ftp = kr_hub_endpoint_new("ftp", "h", 1, "good");
    g_autoptr(KrHubClient) unusable = kr_hub_client_new(ftp, 5);
    Outcome bad = start(unusable, STATUS_JSON);
    refused_with(&bad, KR_WORKFLOWS_ERROR_COMMAND, "not ftp");

    /* A pinned hub that answers without TLS has no certificate to match: refused. */
    Hub hub = {0};
    const Reply polls[] = {{200, QUEUED}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    g_autoptr(KrHubEndpoint) pinned = kr_hub_endpoint_new_device(
        "http", "127.0.0.1", hub.port, "dev-1", "k3y",
        "0000000000000000000000000000000000000000000000000000000000000000");
    g_autoptr(KrHubClient) client = kr_hub_client_new(pinned, 5);
    Outcome unpinned = start(client, STATUS_JSON);
    refused_with(&unpinned, KR_WORKFLOWS_ERROR_FINGERPRINT, "did not show the certificate");
    hub_stop(&hub);
}

/* ---- following a run ------------------------------------------------------------------- */

typedef struct {
    Outcome outcome;
    GPtrArray *states; /* each state progress said, as its name */
    char *last_url;
    GCancellable *cancel_on_first; /* cancelled when progress first speaks */
    Hub *stop_on_first;            /* this hub goes away when progress first speaks */
} Followed;

static void
on_progress(const KrWorkflowRun *run, gpointer data)
{
    Followed *followed = data;
    g_ptr_array_add(followed->states, g_strdup(kr_workflow_state_name(run->state)));
    g_free(followed->last_url);
    followed->last_url = g_strdup(run->url);
    if (followed->cancel_on_first != NULL)
        g_cancellable_cancel(followed->cancel_on_first);
    if (followed->stop_on_first != NULL) {
        soup_server_disconnect(followed->stop_on_first->server);
        g_clear_object(&followed->stop_on_first->server);
        followed->stop_on_first = NULL;
    }
}

static void
on_followed(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Followed *followed = data;
    followed->outcome.run = kr_workflows_run_finish(result, &followed->outcome.error);
    followed->outcome.done = TRUE;
}

/* Follows a run of `status --json` on `hub`, polling every 5 ms for at most `limit_ms`. */
static void
follow(Hub *hub, Followed *followed, guint limit_ms, GCancellable *cancellable)
{
    followed->states = g_ptr_array_new_with_free_func(g_free);
    g_autoptr(KrHubEndpoint) endpoint = endpoint_for(hub);
    KrWorkflowsPolling polling = {.interval_ms = 5, .limit_ms = limit_ms};
    kr_workflows_run_async(endpoint, STATUS_JSON, &polling, on_progress, followed, cancellable,
                           on_followed, followed);
    wait_for(&followed->outcome);
}

static void
followed_clear(Followed *followed)
{
    outcome_clear(&followed->outcome);
    g_clear_pointer(&followed->states, g_ptr_array_unref);
    g_clear_pointer(&followed->last_url, g_free);
}

static void
states_were(Followed *followed, const char *const *want)
{
    g_ptr_array_add(followed->states, NULL);
    g_assert_cmpstrv((char **) followed->states->pdata, want);
    g_ptr_array_remove_index(followed->states, followed->states->len - 1);
}

static void
test_follows_to_done(void)
{
    Hub hub = {0};
    const Reply polls[] = {{200, QUEUED}, {200, RUNNING}, {200, RUNNING}, {200, DONE}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    Followed followed = {0};
    follow(&hub, &followed, 60000, NULL);
    g_assert_no_error(followed.outcome.error);
    g_assert_cmpint(followed.outcome.run->state, ==, KR_WORKFLOW_DONE);
    g_assert_true(followed.outcome.run->has_exit_code);
    g_assert_cmpint(followed.outcome.run->exit_code, ==, 0);
    g_assert_cmpstr(followed.outcome.run->output, ==, "all green\n");
    g_assert_cmpstr(followed.outcome.run->url, ==, RUN_URL);
    states_were(&followed, (const char *const[]){"queued", "queued", "running", "running",
                                                 "done", NULL});
    g_assert_cmpuint(hub.polled, ==, 4);
    g_assert_cmpstr(hub.last_path, ==, RUNS "/r-12345678");
    followed_clear(&followed);
    hub_stop(&hub);
}

static void
test_follows_to_failed(void)
{
    Hub hub = {0};
    const Reply polls[] = {{200, FAILED}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    Followed followed = {0};
    GCancellable *cancellable = g_cancellable_new();
    follow(&hub, &followed, 60000, cancellable);
    g_assert_no_error(followed.outcome.error);
    g_assert_cmpint(followed.outcome.run->state, ==, KR_WORKFLOW_FAILED);
    g_assert_cmpstr(followed.outcome.run->detail, ==, "the runner died");
    states_were(&followed, (const char *const[]){"queued", "failed", NULL});
    followed_clear(&followed);
    g_object_unref(cancellable);
    hub_stop(&hub);

    /* A hub that answers the POST with a finished run is not asked again. */
    Hub quick = {0};
    hub_start(&quick, (Reply){202, DONE}, polls, G_N_ELEMENTS(polls));
    Followed at_once = {0};
    follow(&quick, &at_once, 60000, NULL);
    g_assert_no_error(at_once.outcome.error);
    g_assert_cmpint(at_once.outcome.run->state, ==, KR_WORKFLOW_DONE);
    g_assert_cmpuint(quick.polled, ==, 0);
    followed_clear(&at_once);
    hub_stop(&quick);
}

static void
test_waits_out_trouble(void)
{
    /* Too many requests and GitHub not readable are passing: the run is asked again. */
    Hub hub = {0};
    const Reply polls[] = {{429, NULL},
                           {502, "{\"detail\": \"GitHub could not be read\"}"},
                           {200, RUNNING},
                           {200, DONE}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    Followed followed = {0};
    follow(&hub, &followed, 60000, NULL);
    g_assert_no_error(followed.outcome.error);
    g_assert_cmpint(followed.outcome.run->state, ==, KR_WORKFLOW_DONE);
    states_were(&followed, (const char *const[]){"queued", "running", "done", NULL});
    followed_clear(&followed);
    hub_stop(&hub);
}

static void
test_stops_on_refusal(void)
{
    /* Any other refusal mid-run ends it, said in words. */
    Hub hub = {0};
    const Reply polls[] = {{200, RUNNING}, {403, "{\"detail\": \"scope withdrawn\"}"}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    Followed followed = {0};
    follow(&hub, &followed, 60000, NULL);
    refused_with(&followed.outcome, KR_WORKFLOWS_ERROR_REFUSED, "(the hub said: scope withdrawn)");
    states_were(&followed, (const char *const[]){"queued", "running", NULL});
    followed_clear(&followed);
    hub_stop(&hub);

    /* A run the hub will not start is never followed. */
    Hub off = {0};
    hub_start(&off, (Reply){503, "{\"detail\": \"workflows are not enabled on this hub\"}"},
              polls, G_N_ELEMENTS(polls));
    Followed never = {0};
    follow(&off, &never, 60000, NULL);
    refused_with(&never.outcome, KR_WORKFLOWS_ERROR_REFUSED, "not enabled on this hub");
    g_assert_cmpuint(never.states->len, ==, 0);
    g_assert_cmpuint(off.polled, ==, 0);
    followed_clear(&never);
    hub_stop(&off);
}

static void
test_gives_up_at_the_limit(void)
{
    /* Still running at the limit: krypton stops following, and says where it still is. */
    Hub hub = {0};
    const Reply polls[] = {{200, RUNNING}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    Followed followed = {0};
    follow(&hub, &followed, 1000, NULL);
    refused_with(&followed.outcome, KR_WORKFLOWS_ERROR_TIMEOUT,
                 "krypton stopped following it after 1 second; it is still running at " RUN_URL);
    g_assert_cmpuint(hub.polled, >, 1);
    g_assert_cmpstr(followed.last_url, ==, RUN_URL);
    followed_clear(&followed);
    hub_stop(&hub);
}

static void
test_waits_out_a_hub_that_went_away(void)
{
    /* The hub goes away after the POST: every poll goes unanswered until the limit, and the
     * run is said to be still queued, by its request id. */
    Hub hub = {0};
    const Reply polls[] = {{200, RUNNING}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    Followed followed = {.stop_on_first = &hub};
    follow(&hub, &followed, 1000, NULL);
    refused_with(&followed.outcome, KR_WORKFLOWS_ERROR_TIMEOUT,
                 "it is still queued, and GitHub has not shown its run yet. Its request id is "
                 "r-12345678.");
    g_assert_cmpuint(hub.polled, ==, 0);
    states_were(&followed, (const char *const[]){"queued", NULL});
    followed_clear(&followed);
    hub_stop(&hub);
}

static void
test_cancelled(void)
{
    /* Cancelled while waiting between polls: it ends at once, and says nothing more. */
    Hub hub = {0};
    const Reply polls[] = {{200, RUNNING}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    g_autoptr(GCancellable) cancellable = g_cancellable_new();
    Followed followed = {.cancel_on_first = cancellable};
    gint64 before = g_get_monotonic_time();
    /* An interval far longer than the test: only the cancellation can end it in time. */
    followed.states = g_ptr_array_new_with_free_func(g_free);
    g_autoptr(KrHubEndpoint) endpoint = endpoint_for(&hub);
    KrWorkflowsPolling polling = {.interval_ms = 60000};
    kr_workflows_run_async(endpoint, STATUS_JSON, &polling, on_progress, &followed, cancellable,
                           on_followed, &followed);
    wait_for(&followed.outcome);
    g_assert_cmpint(g_get_monotonic_time() - before, <, 10 * G_USEC_PER_SEC);
    g_assert_null(followed.outcome.run);
    g_assert_error(followed.outcome.error, G_IO_ERROR, G_IO_ERROR_CANCELLED);
    states_were(&followed, (const char *const[]){"queued", NULL});
    g_assert_cmpuint(hub.polled, ==, 0);
    followed_clear(&followed);

    /* Cancelled before it starts: the request is cancelled too. */
    g_autoptr(GCancellable) already = g_cancellable_new();
    g_cancellable_cancel(already);
    Followed early = {0};
    follow(&hub, &early, 60000, already);
    g_assert_error(early.outcome.error, G_IO_ERROR, G_IO_ERROR_CANCELLED);
    g_assert_cmpuint(early.states->len, ==, 0);
    followed_clear(&early);
    hub_stop(&hub);
}

static void
test_bad_command_is_never_sent(void)
{
    Hub hub = {0};
    const Reply polls[] = {{200, RUNNING}};
    hub_start(&hub, (Reply){202, QUEUED}, polls, G_N_ELEMENTS(polls));
    Followed followed = {0};
    followed.states = g_ptr_array_new_with_free_func(g_free);
    g_autoptr(KrHubEndpoint) endpoint = endpoint_for(&hub);
    kr_workflows_run_async(endpoint, NULL, NULL, NULL, NULL, NULL, on_followed, &followed);
    wait_for(&followed.outcome);
    refused_with(&followed.outcome, KR_WORKFLOWS_ERROR_COMMAND, "Type a vibey command");
    g_assert_null(hub.last_method);
    followed_clear(&followed);
    hub_stop(&hub);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/workflows-client/start-and-get", test_start_and_get);
    g_test_add_func("/workflows-client/refusals", test_refusals);
    g_test_add_func("/workflows-client/unreachable", test_unreachable);
    g_test_add_func("/workflows-client/follows-to-done", test_follows_to_done);
    g_test_add_func("/workflows-client/follows-to-failed", test_follows_to_failed);
    g_test_add_func("/workflows-client/waits-out-trouble", test_waits_out_trouble);
    g_test_add_func("/workflows-client/stops-on-refusal", test_stops_on_refusal);
    g_test_add_func("/workflows-client/gives-up-at-the-limit", test_gives_up_at_the_limit);
    g_test_add_func("/workflows-client/waits-out-a-hub-that-went-away",
                    test_waits_out_a_hub_that_went_away);
    g_test_add_func("/workflows-client/cancelled", test_cancelled);
    g_test_add_func("/workflows-client/bad-command-is-never-sent",
                    test_bad_command_is_never_sent);
    return g_test_run();
}
