/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The hub client against a real HTTP server on loopback (libsoup's own SoupServer), playing
 * the hub's routes: the bearer token, the methods, the bodies and the refusals. */
#include <libsoup/soup.h>
#include <string.h>

#include "kr-hub-client.h"
#include "kr-model.h"

typedef struct {
    SoupServer *server;
    guint16 port;
    char *last_method;
    char *last_path;
    char *last_body;
    char *last_auth;
} Hub;

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
        soup_server_message_set_status(message, 401, NULL);
        return;
    }
    if (g_str_equal(path, "/api/v1/projects")) {
        const char *doc = "[{\"project_id\": \"p\", \"name\": \"greeter\"}]";
        soup_server_message_set_status(message, 200, NULL);
        soup_server_message_set_response(message, "application/json", SOUP_MEMORY_COPY, doc,
                                         strlen(doc));
        return;
    }
    if (g_str_equal(path, "/api/v1/gates/g-1/answer")) {
        soup_server_message_set_status(message, 409, NULL);
        return;
    }
    if (g_str_equal(path, "/api/v1/lanes")) {
        soup_server_message_set_redirect(message, 302, "http://127.0.0.1:1/elsewhere");
        return;
    }
    soup_server_message_set_status(message, 404, NULL);
}

static void
hub_start(Hub *hub)
{
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
    soup_server_disconnect(hub->server);
    g_object_unref(hub->server);
    g_free(hub->last_method);
    g_free(hub->last_path);
    g_free(hub->last_body);
    g_free(hub->last_auth);
}

typedef struct {
    GBytes *body;
    guint status;
    GError *error;
    gboolean done;
} Outcome;

static void
on_done(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Outcome *outcome = data;
    outcome->body = kr_hub_client_call_finish(NULL, result, &outcome->status, &outcome->error);
    outcome->done = TRUE;
}

static Outcome
call(KrHubClient *client, KrHubRoute route, const char *project, const char *id, const char *body)
{
    Outcome outcome = {0};
    kr_hub_client_call_async(client, route, project, id, body, NULL, on_done, &outcome);
    while (!outcome.done)
        g_main_context_iteration(NULL, TRUE);
    return outcome;
}

static void
outcome_clear(Outcome *outcome)
{
    g_clear_pointer(&outcome->body, g_bytes_unref);
    g_clear_error(&outcome->error);
}

static void
test_reads_with_the_token(void)
{
    Hub hub = {0};
    hub_start(&hub);
    g_autoptr(KrHubEndpoint) endpoint = kr_hub_endpoint_new("http", "127.0.0.1", hub.port, "good");
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 5);
    g_assert_cmpuint(kr_hub_client_endpoint(client)->port, ==, hub.port);

    Outcome ok = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_no_error(ok.error);
    g_assert_cmpuint(ok.status, ==, 200);
    gsize size = 0;
    const char *text = g_bytes_get_data(ok.body, &size);
    g_autoptr(GError) error = NULL;
    g_autoptr(GPtrArray) projects = kr_projects_parse(text, (gssize) size, &error);
    g_assert_no_error(error);
    g_assert_cmpuint(projects->len, ==, 1);
    g_assert_cmpstr(hub.last_method, ==, "GET");
    g_assert_cmpstr(hub.last_auth, ==, "Bearer good");
    outcome_clear(&ok);

    Outcome missing = call(client, KR_HUB_ROUTE_DOCTOR, NULL, NULL, NULL);
    g_assert_error(missing.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(missing.status, ==, 404);
    outcome_clear(&missing);

    hub_stop(&hub);
}

static void
test_writes_and_refusals(void)
{
    Hub hub = {0};
    hub_start(&hub);
    g_autoptr(KrHubEndpoint) endpoint = kr_hub_endpoint_new("http", "127.0.0.1", hub.port, "good");
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 0);

    Outcome answered = call(client, KR_HUB_ROUTE_GATE_ANSWER, NULL, "g-1", "{\"answer\":{}}");
    g_assert_error(answered.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(answered.status, ==, 409);
    g_assert_cmpstr(hub.last_method, ==, "POST");
    g_assert_cmpstr(hub.last_body, ==, "{\"answer\":{}}");
    outcome_clear(&answered);

    Outcome bumped = call(client, KR_HUB_ROUTE_JOB_BUMP, "p", "j", NULL);
    g_assert_cmpstr(hub.last_body, ==, "{}");
    g_assert_cmpuint(bumped.status, ==, 404);
    outcome_clear(&bumped);

    Outcome redirected = call(client, KR_HUB_ROUTE_LANES, NULL, NULL, NULL);
    g_assert_error(redirected.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(redirected.status, ==, 302);
    outcome_clear(&redirected);

    Outcome no_id = call(client, KR_HUB_ROUTE_GATE_ANSWER, NULL, NULL, NULL);
    g_assert_error(no_id.error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT);
    outcome_clear(&no_id);

    g_autoptr(KrHubEndpoint) stranger = kr_hub_endpoint_new("http", "127.0.0.1", hub.port, NULL);
    g_autoptr(KrHubClient) anonymous = kr_hub_client_new(stranger, 5);
    Outcome refused = call(anonymous, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(refused.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(refused.status, ==, 401);
    g_assert_null(hub.last_auth);
    outcome_clear(&refused);

    hub_stop(&hub);
}

static void
test_bad_endpoints(void)
{
    g_autoptr(KrHubEndpoint) ftp = kr_hub_endpoint_new("ftp", "h", 1, NULL);
    g_autoptr(KrHubClient) client = kr_hub_client_new(ftp, 5);
    Outcome bad = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(bad.error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT);
    outcome_clear(&bad);

    /* Port 1 on loopback: nothing listens, so nothing answers. */
    g_autoptr(KrHubEndpoint) closed = kr_hub_endpoint_new("http", "127.0.0.1", 1, "good");
    g_autoptr(KrHubClient) nobody = kr_hub_client_new(closed, 5);
    Outcome silent = call(nobody, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(silent.error, KR_HUB_ERROR, KR_HUB_ERROR_TRANSPORT);
    g_assert_cmpuint(silent.status, ==, 0);
    outcome_clear(&silent);
    kr_hub_client_free(NULL);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/hub-client/reads-with-the-token", test_reads_with_the_token);
    g_test_add_func("/hub-client/writes-and-refusals", test_writes_and_refusals);
    g_test_add_func("/hub-client/bad-endpoints", test_bad_endpoints);
    return g_test_run();
}
