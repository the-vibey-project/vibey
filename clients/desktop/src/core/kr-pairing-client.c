/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-pairing-client.h"

#include "kr-hub-client.h"

/* A claim waits no longer than this for the hub. */
#define CLAIM_TIMEOUT 15

typedef struct {
    KrHubClient *client;
    char *name;
    char *path;
} Claim;

static void
claim_free(Claim *claim)
{
    kr_hub_client_free(claim->client);
    g_free(claim->name);
    g_free(claim->path);
    g_free(claim);
}

/* A hub client's failure, said as a pairing failure a person can act on. */
static GError *
pairing_error(const KrHubEndpoint *target, GError *failure, guint status, const char *detail)
{
    if (g_error_matches(failure, KR_HUB_ERROR, KR_HUB_ERROR_FINGERPRINT))
        return g_error_new(KR_PAIRING_ERROR, KR_PAIRING_ERROR_FINGERPRINT,
                           "The hub at %s did not show the certificate its pairing code names, "
                           "so krypton refused it before sending the code. Check that you chose "
                           "the right hub. (%s)",
                           target->host, failure->message);
    if (g_error_matches(failure, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED)) {
        g_autofree char *message = kr_pairing_refusal_message(status, detail);
        return g_error_new_literal(KR_PAIRING_ERROR, KR_PAIRING_ERROR_REFUSED, message);
    }
    if (g_error_matches(failure, KR_HUB_ERROR, KR_HUB_ERROR_TRANSPORT))
        return g_error_new(KR_PAIRING_ERROR, KR_PAIRING_ERROR_UNREACHABLE,
                           "No hub answers at %s:%u. Is `vibey serve` running there? (%s)",
                           target->host, target->port, failure->message);
    return g_error_new_literal(KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID, failure->message);
}

static void
on_claimed(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    g_autoptr(GTask) task = data;
    Claim *claim = g_task_get_task_data(task);
    guint status = 0;
    g_autofree char *detail = NULL;
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) body =
        kr_hub_client_call_finish_full(claim->client, result, &status, &detail, &error);
    const KrHubEndpoint *target = kr_hub_client_endpoint(claim->client);
    if (body == NULL) {
        g_task_return_error(task, pairing_error(target, error, status, detail));
        return;
    }
    gsize size = 0;
    const char *text = g_bytes_get_data(body, &size);
    KrDeviceCredential *credential =
        kr_device_credential_from_claim(target, claim->name, text, (gssize) size, &error);
    if (credential == NULL || !kr_device_credential_save(credential, claim->path, &error)) {
        kr_device_credential_free(credential);
        g_task_return_error(task, g_steal_pointer(&error));
        return;
    }
    g_task_return_pointer(task, credential, (GDestroyNotify) kr_device_credential_free);
}

void
kr_pairing_claim_async(const KrHubEndpoint *target, const char *code, const char *name,
                       const char *credential_path, GCancellable *cancellable,
                       GAsyncReadyCallback callback, gpointer user_data)
{
    GTask *task = g_task_new(NULL, cancellable, callback, user_data);
    g_task_set_source_tag(task, kr_pairing_claim_async);
    if (!kr_pairing_code_valid(code)) {
        g_task_return_new_error(task, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID,
                                "A pairing code is the six digits the host shows.");
        g_object_unref(task);
        return;
    }
    Claim *claim = g_new0(Claim, 1);
    /* The claim carries no credential: the target names only where, and which certificate. */
    g_autoptr(KrHubEndpoint) bare = kr_hub_endpoint_new_device(
        target->scheme, target->host, target->port, NULL, NULL, target->fingerprint);
    claim->client = kr_hub_client_new(bare, CLAIM_TIMEOUT);
    claim->name = g_strdup(name);
    claim->path = g_strdup(credential_path);
    g_task_set_task_data(task, claim, (GDestroyNotify) claim_free);
    g_autofree char *body = kr_pairing_claim_body(code, name);
    kr_hub_client_call_async(claim->client, KR_HUB_ROUTE_PAIRING_CLAIM, NULL, NULL, body,
                             cancellable, on_claimed, task);
}

KrDeviceCredential *
kr_pairing_claim_finish(GAsyncResult *result, GError **error)
{
    return g_task_propagate_pointer(G_TASK(result), error);
}
