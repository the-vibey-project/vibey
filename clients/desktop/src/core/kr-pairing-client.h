/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-pairing-client: claiming a pairing code from a hub, over libsoup 3.
 *
 * The device's half of ADR-0068's pairing (kr-pairing.h): it sends the code to the hub the
 * person chose, with no credential, over the pinned certificate when the hub is elsewhere;
 * reads the key the hub answers with; and keeps it, owner-only, before it reports success.
 * Every way it can fail is a KR_PAIRING_ERROR whose message says what happened and what to
 * do: a wrong or spent code, pairing not enabled, no hub answering, a certificate that is
 * not the pinned one (refused before the code is sent), an answer that is not a pairing,
 * or a key that could not be kept. */

#ifndef KR_PAIRING_CLIENT_H
#define KR_PAIRING_CLIENT_H

#include <gio/gio.h>

#include "kr-hub.h"
#include "kr-pairing.h"

G_BEGIN_DECLS

/* Claims `code` from the hub at `target` (kr_pairing_target) as `name`, then saves the key
 * at `credential_path` (kr_device_credential_save). */
void kr_pairing_claim_async(const KrHubEndpoint *target, const char *code, const char *name,
                            const char *credential_path, GCancellable *cancellable,
                            GAsyncReadyCallback callback, gpointer user_data);

/* The kept credential, or NULL with a KR_PAIRING_ERROR. */
KrDeviceCredential *kr_pairing_claim_finish(GAsyncResult *result, GError **error);

G_END_DECLS

#endif /* KR_PAIRING_CLIENT_H */
