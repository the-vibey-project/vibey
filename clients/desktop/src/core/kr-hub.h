/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-hub: where the hub is, what to ask it, and what its refusals mean.
 *
 * The pure half of the hub client (ADR-0068, docs/reference/hub-api.md): an endpoint, the
 * route paths with every id escaped, the host token read the way the hub writes it, and
 * each refusal status said in words. The transport that actually speaks HTTP is
 * kr-hub-client.h, over libsoup 3. */

#ifndef KR_HUB_H
#define KR_HUB_H

#include <glib.h>

G_BEGIN_DECLS

/* `vibey serve` listens here unless vibey.toml says otherwise (hub/settings.py). */
#define KR_HUB_DEFAULT_PORT 8765
#define KR_HUB_DEFAULT_HOST "127.0.0.1"

#define KR_HUB_ERROR (kr_hub_error_quark())
GQuark kr_hub_error_quark(void);

typedef enum {
    KR_HUB_ERROR_TOKEN,     /* the token file is missing, empty or readable by others */
    KR_HUB_ERROR_ENDPOINT,  /* the endpoint cannot be said as a URL */
    KR_HUB_ERROR_REFUSED,   /* the hub answered with a refusal status */
    KR_HUB_ERROR_TRANSPORT, /* the request never got an answer */
} KrHubError;

typedef struct {
    char *scheme; /* "http" on loopback; "https" once pairing lands */
    char *host;
    guint16 port;
    char *token; /* the bearer token; NULL until known */
} KrHubEndpoint;

KrHubEndpoint *kr_hub_endpoint_new(const char *scheme, const char *host, guint16 port,
                                   const char *token);
KrHubEndpoint *kr_hub_endpoint_new_local(const char *token);
KrHubEndpoint *kr_hub_endpoint_copy(const KrHubEndpoint *endpoint);
void kr_hub_endpoint_free(KrHubEndpoint *endpoint);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrHubEndpoint, kr_hub_endpoint_free)

/* "http://127.0.0.1:8765", "https://[fe80::1]:8765". NULL with KR_HUB_ERROR_ENDPOINT when
 * the scheme is not http or https, or the host is empty or holds a URL delimiter. */
char *kr_hub_endpoint_base(const KrHubEndpoint *endpoint, GError **error);

/* The routes a client calls. */
typedef enum {
    KR_HUB_ROUTE_HEALTH_LIVE,
    KR_HUB_ROUTE_HEALTH_READY,
    KR_HUB_ROUTE_PROJECTS,
    KR_HUB_ROUTE_PROJECT_STATUS, /* needs project_id */
    KR_HUB_ROUTE_PROJECT_BUDGET, /* needs project_id */
    KR_HUB_ROUTE_PROJECT_QUEUE,  /* needs project_id */
    KR_HUB_ROUTE_JOB_BUMP,       /* needs project_id and id (the job) */
    KR_HUB_ROUTE_GATES,          /* project_id optional: ?project_id=... */
    KR_HUB_ROUTE_GATE_ANSWER,    /* needs id (the gate) */
    KR_HUB_ROUTE_LANES,
    KR_HUB_ROUTE_LOOPS,
    KR_HUB_ROUTE_DOCTOR,
} KrHubRoute;

/* The path (and query) of a route, every id percent-escaped. NULL when a needed id is
 * missing or empty. */
char *kr_hub_path(KrHubRoute route, const char *project_id, const char *id);

/* Whether the route changes something (POST) rather than reads it (GET). */
gboolean kr_hub_route_writes(KrHubRoute route);

/* Reads the host token from `path` the way the hub demands it be kept: a regular file, not
 * a symlink, readable by its owner alone, holding one non-empty line. Surrounding
 * whitespace is dropped. */
char *kr_hub_read_token(const char *path, GError **error);

/* Where the host token is, when the hub runs on this computer under `state_dir`. A NULL
 * or empty `state_dir` means the hub's default, platformdirs' user_state_dir("vibey")/hub:
 * ~/Library/Application Support/vibey/hub on macOS, $XDG_STATE_HOME/vibey/hub elsewhere. */
char *kr_hub_token_path(const char *state_dir);

/* A refusal status in words a person can act on (hub-api.md, "Refusals"). Static. */
const char *kr_hub_status_text(guint status);

G_END_DECLS

#endif /* KR_HUB_H */
