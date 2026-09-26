/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-hub-client.h"

#include <libsoup/soup.h>
#include <string.h>

#define DEFAULT_TIMEOUT 15

struct _KrHubClient {
    KrHubEndpoint *endpoint;
    SoupSession *session;
};

typedef struct {
    SoupMessage *message;
} Call;

static void
call_free(Call *call)
{
    g_clear_object(&call->message);
    g_free(call);
}

KrHubClient *
kr_hub_client_new(const KrHubEndpoint *endpoint, guint timeout_seconds)
{
    KrHubClient *client = g_new0(KrHubClient, 1);
    client->endpoint = kr_hub_endpoint_copy(endpoint);
    client->session = soup_session_new_with_options(
        "timeout", timeout_seconds != 0 ? timeout_seconds : DEFAULT_TIMEOUT, "user-agent",
        "krypton-desktop", NULL);
    return client;
}

void
kr_hub_client_free(KrHubClient *client)
{
    if (client == NULL)
        return;
    soup_session_abort(client->session);
    g_object_unref(client->session);
    kr_hub_endpoint_free(client->endpoint);
    g_free(client);
}

const KrHubEndpoint *
kr_hub_client_endpoint(KrHubClient *client)
{
    return client->endpoint;
}

static void
on_sent(GObject *source, GAsyncResult *result, gpointer data)
{
    g_autoptr(GTask) task = data;
    Call *call = g_task_get_task_data(task);
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) body = soup_session_send_and_read_finish(SOUP_SESSION(source), result,
                                                               &error);
    if (body == NULL) {
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_TRANSPORT,
                                "the hub did not answer: %s", error->message);
        return;
    }
    guint status = soup_message_get_status(call->message);
    if (status < 200 || status >= 300) {
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED, "%u: %s", status,
                                kr_hub_status_text(status));
        return;
    }
    g_task_return_pointer(task, g_steal_pointer(&body), (GDestroyNotify) g_bytes_unref);
}

void
kr_hub_client_call_async(KrHubClient *client, KrHubRoute route, const char *project_id,
                         const char *id, const char *body, GCancellable *cancellable,
                         GAsyncReadyCallback callback, gpointer user_data)
{
    GTask *task = g_task_new(NULL, cancellable, callback, user_data);
    g_task_set_source_tag(task, kr_hub_client_call_async);

    g_autoptr(GError) error = NULL;
    g_autofree char *base = kr_hub_endpoint_base(client->endpoint, &error);
    g_autofree char *path = kr_hub_path(route, project_id, id);
    if (base == NULL || path == NULL) {
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT, "%s",
                                base == NULL ? error->message : "that route needs an id");
        g_object_unref(task);
        return;
    }
    g_autofree char *url = g_strconcat(base, path, NULL);
    gboolean writes = kr_hub_route_writes(route);
    SoupMessage *message = soup_message_new(writes ? SOUP_METHOD_POST : SOUP_METHOD_GET, url);
    if (message == NULL) {
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT, "%s is not a URL",
                                url);
        g_object_unref(task);
        return;
    }
    soup_message_add_flags(message, SOUP_MESSAGE_NO_REDIRECT);
    SoupMessageHeaders *headers = soup_message_get_request_headers(message);
    soup_message_headers_replace(headers, "Accept", "application/json");
    if (client->endpoint->token != NULL) {
        g_autofree char *bearer = g_strconcat("Bearer ", client->endpoint->token, NULL);
        soup_message_headers_replace(headers, "Authorization", bearer);
    }
    if (writes) {
        const char *text = body != NULL ? body : "{}";
        g_autoptr(GBytes) bytes = g_bytes_new(text, strlen(text));
        soup_message_set_request_body_from_bytes(message, "application/json", bytes);
    }

    Call *call = g_new0(Call, 1);
    call->message = message;
    g_task_set_task_data(task, call, (GDestroyNotify) call_free);
    soup_session_send_and_read_async(client->session, message, G_PRIORITY_DEFAULT, cancellable,
                                     on_sent, task);
}

GBytes *
kr_hub_client_call_finish(KrHubClient *client, GAsyncResult *result, guint *status,
                          GError **error)
{
    (void) client;
    GTask *task = G_TASK(result);
    Call *call = g_task_get_task_data(task);
    if (status != NULL)
        *status = call != NULL ? soup_message_get_status(call->message) : 0;
    return g_task_propagate_pointer(task, error);
}
