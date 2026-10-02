/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-hub-client.h"

#include <json-glib/json-glib.h>
#include <libsoup/soup.h>
#include <string.h>
#include <sys/random.h>

#define DEFAULT_TIMEOUT 15
#define NONCE_BYTES 16

struct _KrHubClient {
    KrHubEndpoint *endpoint;
    SoupSession *session;
};

typedef struct {
    SoupMessage *message;
    char *pinned; /* the fingerprint the hub's certificate must have, or NULL */
    char *seen;   /* the fingerprint of the certificate the hub showed, once it showed one */
    char *detail; /* the hub's own words for a refusal ({"detail": ...}), or NULL */
} Call;

static void
call_free(Call *call)
{
    g_clear_object(&call->message);
    g_free(call->pinned);
    g_free(call->seen);
    g_free(call->detail);
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
    /* A pinned hub is trusted for its certificate's fingerprint, never for who signed it:
     * with no certificate database every certificate is unverified, so every handshake
     * reaches on_certificate below, which admits the pinned one and nothing else. */
    if (client->endpoint->fingerprint != NULL)
        soup_session_set_tls_database(client->session, NULL);
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

char *
kr_hub_certificate_fingerprint(GTlsCertificate *certificate)
{
    g_autoptr(GByteArray) der = NULL;
    g_object_get(certificate, "certificate", &der, NULL);
    return g_compute_checksum_for_data(G_CHECKSUM_SHA256, der->data, der->len);
}

static gboolean
on_certificate(SoupMessage *message, GTlsCertificate *certificate, GTlsCertificateFlags errors,
               gpointer data)
{
    (void) message;
    (void) errors;
    Call *call = data;
    g_free(call->seen);
    call->seen = kr_hub_certificate_fingerprint(certificate);
    return g_str_equal(call->seen, call->pinned);
}

/* The hub refuses with {"detail": "..."}; anything else says nothing more. */
static char *
refusal_detail(GBytes *body)
{
    gsize size = 0;
    const char *text = g_bytes_get_data(body, &size);
    g_autoptr(JsonParser) parser = json_parser_new();
    if (size == 0 || !json_parser_load_from_data(parser, text, (gssize) size, NULL))
        return NULL;
    JsonNode *root = json_parser_get_root(parser);
    if (!JSON_NODE_HOLDS_OBJECT(root))
        return NULL;
    JsonNode *detail = json_object_get_member(json_node_get_object(root), "detail");
    if (detail == NULL || json_node_get_value_type(detail) != G_TYPE_STRING)
        return NULL;
    return g_strdup(json_node_get_string(detail));
}

static void
on_sent(GObject *source, GAsyncResult *result, gpointer data)
{
    g_autoptr(GTask) task = data;
    Call *call = g_task_get_task_data(task);
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) body = soup_session_send_and_read_finish(SOUP_SESSION(source), result,
                                                               &error);
    if (call->seen != NULL && !g_str_equal(call->seen, call->pinned)) {
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_FINGERPRINT,
                                "the hub showed a certificate krypton did not pair with "
                                "(sha256 %s, not %s); nothing was sent to it",
                                call->seen, call->pinned);
        return;
    }
    if (body == NULL) {
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_TRANSPORT,
                                "the hub did not answer: %s", error->message);
        return;
    }
    if (call->pinned != NULL) {
        /* The handshake was checked; this checks the connection the answer came on. */
        GTlsCertificate *peer = soup_message_get_tls_peer_certificate(call->message);
        g_autofree char *seen = peer != NULL ? kr_hub_certificate_fingerprint(peer) : NULL;
        if (seen == NULL || !g_str_equal(seen, call->pinned)) {
            g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_FINGERPRINT,
                                    "the hub answered without the certificate krypton paired "
                                    "with (sha256 %s)", call->pinned);
            return;
        }
    }
    guint status = soup_message_get_status(call->message);
    if (status < 200 || status >= 300) {
        call->detail = refusal_detail(body);
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED, "%u: %s", status,
                                kr_hub_status_text(status));
        return;
    }
    g_task_return_pointer(task, g_steal_pointer(&body), (GDestroyNotify) g_bytes_unref);
}

/* Sixteen bytes from the operating system's CSPRNG, as hex. A nonce must be unique, so a
 * platform that cannot supply them gets a random UUID instead, which is. */
static char *
fresh_nonce(void)
{
    guchar bytes[NONCE_BYTES];
    if (getentropy(bytes, sizeof bytes) != 0)
        return g_uuid_string_random();
    GString *hex = g_string_sized_new(NONCE_BYTES * 2);
    for (size_t i = 0; i < sizeof bytes; i++)
        g_string_append_printf(hex, "%02x", bytes[i]);
    return g_string_free(hex, FALSE);
}

/* A paired device's four headers over this request (kr_hub_canonical). FALSE when the
 * request cannot be put in canonical form. */
static gboolean
sign(SoupMessageHeaders *headers, const KrHubEndpoint *endpoint, const char *method,
     const char *path_and_query, const char *body)
{
    g_auto(GStrv) parts = g_strsplit(path_and_query, "?", 2);
    /* The hub reads the path percent-decoded and the query as it was sent. */
    g_autofree char *path = g_uri_unescape_string(parts[0], NULL);
    const char *query = parts[1] != NULL ? parts[1] : "";
    g_autofree char *timestamp = g_strdup_printf("%" G_GINT64_FORMAT,
                                                 g_get_real_time() / G_USEC_PER_SEC);
    g_autofree char *nonce = fresh_nonce();
    g_autofree char *digest = g_compute_checksum_for_string(G_CHECKSUM_SHA256, body, -1);
    g_autofree char *canonical = kr_hub_canonical(endpoint->device_id, method, path, query,
                                                  timestamp, nonce, digest);
    if (canonical == NULL)
        return FALSE;
    g_autofree char *hmac = kr_hub_signature(endpoint->token, canonical);
    g_autofree char *signature = g_strconcat("sha256=", hmac, NULL);
    const char *values[] = {endpoint->device_id, timestamp, nonce, signature};
    for (size_t i = 0; i < G_N_ELEMENTS(values); i++)
        soup_message_headers_replace(headers, kr_hub_device_headers[i], values[i]);
    return TRUE;
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
    const char *method = writes ? SOUP_METHOD_POST : SOUP_METHOD_GET;
    SoupMessage *message = soup_message_new(method, url);
    if (message == NULL) {
        g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT, "%s is not a URL",
                                url);
        g_object_unref(task);
        return;
    }
    soup_message_add_flags(message, SOUP_MESSAGE_NO_REDIRECT);
    SoupMessageHeaders *headers = soup_message_get_request_headers(message);
    soup_message_headers_replace(headers, "Accept", "application/json");
    const char *text = writes ? (body != NULL ? body : "{}") : "";
    /* A claim is how a device gets its key, so it carries no credential at all. */
    gboolean credential = client->endpoint->token != NULL && route != KR_HUB_ROUTE_PAIRING_CLAIM;
    if (credential && client->endpoint->device_id != NULL) {
        if (!sign(headers, client->endpoint, method, path, text)) {
            g_task_return_new_error(task, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT,
                                    "that request cannot be signed");
            g_object_unref(message);
            g_object_unref(task);
            return;
        }
    } else if (credential) {
        g_autofree char *bearer = g_strconcat("Bearer ", client->endpoint->token, NULL);
        soup_message_headers_replace(headers, "Authorization", bearer);
    }
    if (writes) {
        g_autoptr(GBytes) bytes = g_bytes_new(text, strlen(text));
        soup_message_set_request_body_from_bytes(message, "application/json", bytes);
    }

    Call *call = g_new0(Call, 1);
    call->message = message;
    call->pinned = g_strdup(client->endpoint->fingerprint);
    if (call->pinned != NULL)
        g_signal_connect(message, "accept-certificate", G_CALLBACK(on_certificate), call);
    g_task_set_task_data(task, call, (GDestroyNotify) call_free);
    soup_session_send_and_read_async(client->session, message, G_PRIORITY_DEFAULT, cancellable,
                                     on_sent, task);
}

GBytes *
kr_hub_client_call_finish_full(KrHubClient *client, GAsyncResult *result, guint *status,
                               char **detail, GError **error)
{
    (void) client;
    GTask *task = G_TASK(result);
    Call *call = g_task_get_task_data(task);
    if (status != NULL)
        *status = call != NULL ? soup_message_get_status(call->message) : 0;
    if (detail != NULL)
        *detail = call != NULL ? g_strdup(call->detail) : NULL;
    return g_task_propagate_pointer(task, error);
}

GBytes *
kr_hub_client_call_finish(KrHubClient *client, GAsyncResult *result, guint *status,
                          GError **error)
{
    return kr_hub_client_call_finish_full(client, result, status, NULL, error);
}
