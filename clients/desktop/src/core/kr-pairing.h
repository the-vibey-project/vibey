/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-pairing: pairing this computer with a hub, and the key it is given.
 *
 * Being on the same network proves nothing (SD-01, ADR-0068): a device pairs once, with
 * the 6-digit code the host shows (`vibey hub pair`), and only then is trusted. The hub
 * defines the exchange (src/vibey/domain/hub_pairing.py, src/vibey/infrastructure/hub/
 * pairing.py, docs/reference/hub-api.json):
 *
 *   - the host's offer is shown as a pairing URI, also printed as text beneath its QR code:
 *
 *         vibey-pair://<host>:<port>?fp=<SHA-256 of the hub certificate, hex>&code=<6>&v=1
 *
 *     `fp` is empty only for a hub on loopback, which serves no TLS;
 *   - the device POSTs {"code", "name"} to /api/v1/pairing/claim with no credential, and
 *     the first correct claim within two minutes is answered, once, with
 *     {"device_id", "key", "scopes", "fingerprint"};
 *   - every later request is signed with that key (kr-hub.h, kr_hub_canonical).
 *
 * The certificate fingerprint is what makes the encrypted connection trustworthy: krypton
 * pins it at pairing, and a hub that shows any other certificate is refused, the claim
 * included. A hub on another computer is paired only when its fingerprint is known -- from
 * the pairing URI, or from the hub's own advertisement, which the Devices page shows for a
 * person to compare with the one the host shows.
 *
 * The key is kept the way the hub keeps its own token and its devices' keys
 * (local_token.py, devices.py): a file this account alone may read (mode 0600, in a 0700
 * directory), never through a symlink. Whoever can read it can act as this device, so it
 * is no weaker than the hub's own files and no stronger. */

#ifndef KR_PAIRING_H
#define KR_PAIRING_H

#include <glib.h>

#include "kr-hub.h"

G_BEGIN_DECLS

#define KR_PAIRING_SCHEME "vibey-pair"
#define KR_PAIRING_CODE_LENGTH 6
#define KR_PAIRING_FINGERPRINT_LENGTH 64 /* SHA-256, as lowercase hex */
#define KR_PAIRING_NAME_MAX 64           /* the longest name the hub takes for a device */

#define KR_PAIRING_ERROR (kr_pairing_error_quark())
GQuark kr_pairing_error_quark(void);

typedef enum {
    KR_PAIRING_ERROR_INVALID,     /* not a code or pairing URI krypton can use */
    KR_PAIRING_ERROR_UNPINNED,    /* a hub elsewhere, with no certificate to pin */
    KR_PAIRING_ERROR_REFUSED,     /* the hub answered the claim with a refusal */
    KR_PAIRING_ERROR_UNREACHABLE, /* no hub answered at all */
    KR_PAIRING_ERROR_FINGERPRINT, /* the hub showed a certificate other than the pinned one */
    KR_PAIRING_ERROR_RESPONSE,    /* the hub's answer is not a pairing */
    KR_PAIRING_ERROR_STORE,       /* the key could not be kept, or what is kept is unsafe */
} KrPairingError;

typedef struct {
    char *host;
    guint16 port;
    char *code;        /* six digits */
    char *fingerprint; /* 64 lowercase hex characters; NULL for a loopback hub */
} KrPairingOffer;

/* Exactly six ASCII digits, nothing around them. */
gboolean kr_pairing_code_valid(const char *code);

/* A code as typed: spaces and dashes a person adds ("123 456", "123-456") are dropped.
 * NULL when what remains is not a valid code. */
char *kr_pairing_code_normalise(const char *typed);

/* 64 hex characters. */
gboolean kr_pairing_fingerprint_valid(const char *fingerprint);

/* Reads a pairing URI. An empty or missing fingerprint is accepted only for a loopback
 * host; a version other than 1 is refused. */
KrPairingOffer *kr_pairing_offer_parse(const char *uri, GError **error);
void kr_pairing_offer_free(KrPairingOffer *offer);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrPairingOffer, kr_pairing_offer_free)

/* The fingerprint grouped for a person to compare by eye: "ab12 cd34 ...". */
char *kr_pairing_fingerprint_display(const char *fingerprint);

/* Where a claim goes: https and the pinned certificate when `fingerprint` is given, plain
 * http for a loopback hub without one. A hub elsewhere with no fingerprint is refused
 * (KR_PAIRING_ERROR_UNPINNED): its certificate could be anyone's. */
KrHubEndpoint *kr_pairing_target(const char *host, guint16 port, const char *fingerprint,
                                 GError **error);

/* The name this device gives the hub, "krypton on <host name>": printable ASCII, at most
 * KR_PAIRING_NAME_MAX characters. */
char *kr_pairing_device_name(const char *host_name);

/* The claim's JSON body. */
char *kr_pairing_claim_body(const char *code, const char *name);

/* A refusal of a claim in words a person can act on; `detail` is the hub's own, or NULL. */
char *kr_pairing_refusal_message(guint status, const char *detail);

/* ---- the key a pairing gives ---------------------------------------------------------- */

typedef struct {
    char *scheme; /* "https", or "http" for a loopback hub */
    char *host;
    guint16 port;
    char *fingerprint; /* the pinned certificate; NULL only with "http" on loopback */
    char *device_id;
    char *key;     /* the per-device key; signs, is never sent */
    char *name;    /* what this device called itself */
    char **scopes; /* what the host let it do */
} KrDeviceCredential;

void kr_device_credential_free(KrDeviceCredential *credential);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrDeviceCredential, kr_device_credential_free)

/* Reads the hub's answer to a claim sent to `target` as `name`. Refused
 * (KR_PAIRING_ERROR_RESPONSE) when it lacks an id or key, or names a certificate other
 * than the one `target` pinned. */
KrDeviceCredential *kr_device_credential_from_claim(const KrHubEndpoint *target,
                                                    const char *name, const char *json,
                                                    gssize length, GError **error);

/* The endpoint a paired device reaches its hub with: signed, and pinned when it has one. */
KrHubEndpoint *kr_device_credential_endpoint(const KrDeviceCredential *credential);

/* Whether the credential is for the hub at `host` and `port` (0 means the default port). */
gboolean kr_device_credential_matches(const KrDeviceCredential *credential, const char *host,
                                      guint16 port);

/* Where the key is kept: "paired-hub.ini" beside the settings file at `settings_path`. */
char *kr_device_credential_path(const char *settings_path);

/* Writes atomically as mode 0600, creating the directory (0700) when needed. */
gboolean kr_device_credential_save(const KrDeviceCredential *credential, const char *path,
                                   GError **error);

/* Reads it back, refusing a symlink, anything but a regular file, a file another account
 * could read, and anything malformed. A missing file is G_FILE_ERROR_NOENT. */
KrDeviceCredential *kr_device_credential_load(const char *path, GError **error);

G_END_DECLS

#endif /* KR_PAIRING_H */
