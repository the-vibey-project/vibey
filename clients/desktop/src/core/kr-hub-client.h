/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-hub-client: the hub over HTTP, with libsoup 3.
 *
 * One asynchronous call per route: it proves who is calling -- the host's bearer token, or
 * a paired device's signature (kr_hub_canonical; the key itself is never sent) -- never
 * follows a redirect (a hub that redirects is not the hub), and hands back the body on a
 * 2xx or a KR_HUB_ERROR_REFUSED carrying the status and its words otherwise. The body is
 * the document kr-model.h parses.
 *
 * An endpoint with a pinned fingerprint is reached over TLS and trusts exactly one
 * certificate: the one whose SHA-256 the pairing code carried. Any other certificate on
 * that address ends the handshake before a byte of the request is sent, as
 * KR_HUB_ERROR_FINGERPRINT. */

#ifndef KR_HUB_CLIENT_H
#define KR_HUB_CLIENT_H

#include <gio/gio.h>

#include "kr-hub.h"

G_BEGIN_DECLS

typedef struct _KrHubClient KrHubClient;

/* The client copies the endpoint. `timeout_seconds` of 0 means 15. */
KrHubClient *kr_hub_client_new(const KrHubEndpoint *endpoint, guint timeout_seconds);
void kr_hub_client_free(KrHubClient *client);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrHubClient, kr_hub_client_free)

const KrHubEndpoint *kr_hub_client_endpoint(KrHubClient *client);

/* Calls `route`. `body` is the JSON a writing route sends (kr_hub_route_writes) and is
 * ignored by a reading one. */
void kr_hub_client_call_async(KrHubClient *client, KrHubRoute route, const char *project_id,
                              const char *id, const char *body, GCancellable *cancellable,
                              GAsyncReadyCallback callback, gpointer user_data);

/* The response body on a 2xx. Otherwise NULL, with *status (when not NULL) set to the HTTP
 * status (0 when nothing answered) and the error KR_HUB_ERROR_REFUSED or
 * KR_HUB_ERROR_TRANSPORT. */
GBytes *kr_hub_client_call_finish(KrHubClient *client, GAsyncResult *result, guint *status,
                                  GError **error);

/* As kr_hub_client_call_finish, and on a refusal *detail (when not NULL) is the hub's own
 * words for it ({"detail": "..."}), or NULL when it said none. */
GBytes *kr_hub_client_call_finish_full(KrHubClient *client, GAsyncResult *result,
                                       guint *status, char **detail, GError **error);

/* The SHA-256 of a certificate's DER encoding, as lowercase hex: what the hub's pairing
 * code carries (src/vibey/infrastructure/hub/tls.py, `fingerprint`). */
char *kr_hub_certificate_fingerprint(GTlsCertificate *certificate);

G_END_DECLS

#endif /* KR_HUB_CLIENT_H */
