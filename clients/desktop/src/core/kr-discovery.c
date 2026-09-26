/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-discovery.h"

#include <string.h>

#if defined(KR_HAVE_AVAHI)
extern const KrDiscoveryBackend kr_discovery_avahi_backend;
#elif defined(KR_HAVE_DNSSD)
extern const KrDiscoveryBackend kr_discovery_dnssd_backend;
#endif

static gboolean
filled(const char *text)
{
    return text != NULL && *text != '\0';
}

const char *
kr_txt_lookup(const char *const *txt, const char *key)
{
    size_t key_length = strlen(key);
    for (size_t i = 0; txt != NULL && txt[i] != NULL; i++) {
        const char *entry = txt[i];
        if (g_ascii_strncasecmp(entry, key, key_length) != 0)
            continue;
        if (entry[key_length] == '=')
            return entry + key_length + 1;
        if (entry[key_length] == '\0')
            return "";
    }
    return NULL;
}

KrHubService *
kr_hub_service_new(const char *name, const char *host, guint16 port, const char *const *txt)
{
    if (!filled(name) || !filled(host) || port == 0)
        return NULL;
    KrHubService *service = g_new0(KrHubService, 1);
    service->name = g_strdup(name);
    service->host = g_strdup(host);
    service->port = port;
    const char *version = kr_txt_lookup(txt, "version");
    service->version = filled(version) ? g_strdup(version) : NULL;
    const char *path = kr_txt_lookup(txt, "path");
    service->path = g_strdup(filled(path) ? path : "/api/v1");
    return service;
}

KrHubService *
kr_hub_service_copy(const KrHubService *service)
{
    KrHubService *copy = g_new0(KrHubService, 1);
    copy->name = g_strdup(service->name);
    copy->host = g_strdup(service->host);
    copy->port = service->port;
    copy->version = g_strdup(service->version);
    copy->path = g_strdup(service->path);
    return copy;
}

void
kr_hub_service_free(KrHubService *service)
{
    if (service == NULL)
        return;
    g_free(service->name);
    g_free(service->host);
    g_free(service->version);
    g_free(service->path);
    g_free(service);
}

static gboolean
same_service(const KrHubService *a, const KrHubService *b)
{
    return g_str_equal(a->host, b->host) && a->port == b->port &&
           g_strcmp0(a->version, b->version) == 0 && g_str_equal(a->path, b->path);
}

const KrDiscoveryBackend *
kr_discovery_platform_backend(void)
{
#if defined(KR_HAVE_AVAHI)
    return &kr_discovery_avahi_backend;
#elif defined(KR_HAVE_DNSSD)
    return &kr_discovery_dnssd_backend;
#else
    return NULL;
#endif
}

KrDiscovery *
kr_discovery_new(const KrDiscoveryBackend *backend, KrDiscoveryFound found, KrDiscoveryLost lost,
                 gpointer user_data)
{
    if (backend == NULL)
        backend = kr_discovery_platform_backend();
    if (backend == NULL)
        return NULL;
    KrDiscovery *discovery = g_new0(KrDiscovery, 1);
    discovery->backend = backend;
    discovery->found = found;
    discovery->lost = lost;
    discovery->user_data = user_data;
    discovery->services = g_hash_table_new_full(g_str_hash, g_str_equal, g_free,
                                                (GDestroyNotify) kr_hub_service_free);
    return discovery;
}

gboolean
kr_discovery_start(KrDiscovery *discovery, GError **error)
{
    return discovery->backend->start(discovery, error);
}

void
kr_discovery_free(KrDiscovery *discovery)
{
    if (discovery == NULL)
        return;
    discovery->backend->stop(discovery);
    g_hash_table_unref(discovery->services);
    g_free(discovery);
}

void
kr_discovery_report_found(KrDiscovery *discovery, const KrHubService *service)
{
    const KrHubService *seen = g_hash_table_lookup(discovery->services, service->name);
    if (seen != NULL && same_service(seen, service))
        return;
    g_hash_table_replace(discovery->services, g_strdup(service->name),
                         kr_hub_service_copy(service));
    if (discovery->found != NULL)
        discovery->found(service, discovery->user_data);
}

void
kr_discovery_report_lost(KrDiscovery *discovery, const char *name)
{
    if (!g_hash_table_remove(discovery->services, name))
        return;
    if (discovery->lost != NULL)
        discovery->lost(name, discovery->user_data);
}

static gint
by_name(gconstpointer a, gconstpointer b)
{
    const KrHubService *left = *(const KrHubService *const *) a;
    const KrHubService *right = *(const KrHubService *const *) b;
    return g_utf8_collate(left->name, right->name);
}

GPtrArray *
kr_discovery_services(KrDiscovery *discovery)
{
    GPtrArray *out = g_ptr_array_new();
    GHashTableIter iter;
    gpointer value;
    g_hash_table_iter_init(&iter, discovery->services);
    while (g_hash_table_iter_next(&iter, NULL, &value))
        g_ptr_array_add(out, value);
    g_ptr_array_sort(out, by_name);
    return out;
}
