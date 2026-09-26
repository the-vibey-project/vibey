/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-discovery: finding hubs on the local network.
 *
 * A hub on the LAN advertises itself over mDNS/DNS-SD as `_vibey._tcp` (ADR-0068). Krypton
 * browses for it with Avahi on Linux and dns_sd.h on macOS; both backends sit behind the one
 * interface below, so the views never know which is running. Finding a hub is not trusting
 * it: a found hub still has to be paired (kr-pairing.h). */

#ifndef KR_DISCOVERY_H
#define KR_DISCOVERY_H

#include <glib.h>

G_BEGIN_DECLS

#define KR_DISCOVERY_SERVICE_TYPE "_vibey._tcp"

typedef struct {
    char *name; /* the service instance name, what a person sees */
    char *host; /* the host name the service resolved to */
    guint16 port;
    char *version; /* TXT "version", NULL when absent */
    char *path;    /* TXT "path", the API prefix; "/api/v1" when absent */
} KrHubService;

/* Builds a service from what the resolver reported. `txt` is a NULL-terminated array of
 * "key=value" strings (either may be NULL). NULL when name or host is empty or port is 0. */
KrHubService *kr_hub_service_new(const char *name, const char *host, guint16 port,
                                 const char *const *txt);
KrHubService *kr_hub_service_copy(const KrHubService *service);
void kr_hub_service_free(KrHubService *service);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrHubService, kr_hub_service_free)

/* The value of `key` in a TXT list; NULL when absent. Keys compare case-insensitively
 * (RFC 6763 section 6.4). A bare "key" with no "=" has the empty value. */
const char *kr_txt_lookup(const char *const *txt, const char *key);

/* ---- the backend interface ----------------------------------------------------------- */

typedef void (*KrDiscoveryFound)(const KrHubService *service, gpointer user_data);
typedef void (*KrDiscoveryLost)(const char *name, gpointer user_data);

typedef struct _KrDiscovery KrDiscovery;

/* What a backend provides. `start` begins browsing on the thread-default main context and
 * returns FALSE with an error when the platform service is not there (no Avahi daemon, for
 * instance): Krypton then says so and offers the 6-digit code instead. */
typedef struct {
    const char *name;
    gboolean (*start)(KrDiscovery *discovery, GError **error);
    void (*stop)(KrDiscovery *discovery);
} KrDiscoveryBackend;

struct _KrDiscovery {
    const KrDiscoveryBackend *backend;
    KrDiscoveryFound found;
    KrDiscoveryLost lost;
    gpointer user_data;
    gpointer backend_data; /* the backend's own state */
    GHashTable *services;  /* name -> KrHubService, what is currently seen */
};

/* A discovery over `backend`, or over this platform's own when `backend` is NULL. NULL when
 * there is neither (a build without discovery). */
KrDiscovery *kr_discovery_new(const KrDiscoveryBackend *backend, KrDiscoveryFound found,
                              KrDiscoveryLost lost, gpointer user_data);
gboolean kr_discovery_start(KrDiscovery *discovery, GError **error);
void kr_discovery_free(KrDiscovery *discovery);

/* Called by a backend: records the service and tells the listener. A service already seen
 * with the same name is replaced, and reported again only when it changed. */
void kr_discovery_report_found(KrDiscovery *discovery, const KrHubService *service);
void kr_discovery_report_lost(KrDiscovery *discovery, const char *name);

/* The services currently seen, sorted by name (a new array of borrowed pointers). */
GPtrArray *kr_discovery_services(KrDiscovery *discovery);

/* This platform's backend, or NULL when the build has none. */
const KrDiscoveryBackend *kr_discovery_platform_backend(void);

G_END_DECLS

#endif /* KR_DISCOVERY_H */
