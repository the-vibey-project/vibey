/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The macOS discovery backend: dns_sd.h (Bonjour), its socket watched by the GLib main loop. */
#include "kr-discovery.h"

#include <dns_sd.h>
#include <gio/gio.h>
#include <glib-unix.h>
#include <string.h>

typedef struct {
    DNSServiceRef browse;
    GSource *browse_source;
    GHashTable *resolving; /* instance name -> Resolving */
} DnssdState;

typedef struct {
    KrDiscovery *discovery;
    char *name;
    DNSServiceRef ref;
    GSource *source;
} Resolving;

static gboolean
on_ready(gint fd, GIOCondition condition, gpointer data)
{
    (void) fd;
    (void) condition;
    DNSServiceRef ref = data;
    return DNSServiceProcessResult(ref) == kDNSServiceErr_NoError ? G_SOURCE_CONTINUE
                                                                   : G_SOURCE_REMOVE;
}

static GSource *
watch(DNSServiceRef ref)
{
    GSource *source = g_unix_fd_source_new(DNSServiceRefSockFD(ref), G_IO_IN);
    g_source_set_callback(source, G_SOURCE_FUNC(on_ready), ref, NULL);
    g_source_attach(source, g_main_context_get_thread_default());
    return source;
}

static void
resolving_free(Resolving *resolving)
{
    if (resolving->source != NULL) {
        g_source_destroy(resolving->source);
        g_source_unref(resolving->source);
    }
    if (resolving->ref != NULL)
        DNSServiceRefDeallocate(resolving->ref);
    g_free(resolving->name);
    g_free(resolving);
}

/* TXT record bytes -> "key=value" strings. */
static char **
txt_strings(uint16_t length, const unsigned char *record)
{
    GStrvBuilder *builder = g_strv_builder_new();
    uint16_t count = TXTRecordGetCount(length, record);
    for (uint16_t i = 0; i < count; i++) {
        char key[256];
        uint8_t value_length = 0;
        const void *value = NULL;
        if (TXTRecordGetItemAtIndex(length, record, i, sizeof key, key, &value_length, &value) !=
            kDNSServiceErr_NoError)
            continue;
        g_autofree char *text = g_strndup(value != NULL ? value : "", value_length);
        g_strv_builder_take(builder, g_strdup_printf("%s=%s", key, text));
    }
    char **out = g_strv_builder_end(builder);
    g_strv_builder_unref(builder);
    return out;
}

static void DNSSD_API
on_resolved(DNSServiceRef ref, DNSServiceFlags flags, uint32_t interface, DNSServiceErrorType error,
            const char *full_name, const char *host, uint16_t port_network, uint16_t txt_length,
            const unsigned char *txt, void *context)
{
    (void) ref;
    (void) flags;
    (void) interface;
    (void) full_name;
    Resolving *resolving = context;
    if (error == kDNSServiceErr_NoError) {
        g_auto(GStrv) strings = txt_strings(txt_length, txt);
        g_autoptr(KrHubService) service = kr_hub_service_new(
            resolving->name, host, g_ntohs(port_network), (const char *const *) strings);
        if (service != NULL)
            kr_discovery_report_found(resolving->discovery, service);
    }
}

static void DNSSD_API
on_browse(DNSServiceRef ref, DNSServiceFlags flags, uint32_t interface, DNSServiceErrorType error,
          const char *name, const char *type, const char *domain, void *context)
{
    (void) ref;
    KrDiscovery *discovery = context;
    DnssdState *state = discovery->backend_data;
    if (error != kDNSServiceErr_NoError)
        return;
    if ((flags & kDNSServiceFlagsAdd) == 0) {
        g_hash_table_remove(state->resolving, name);
        kr_discovery_report_lost(discovery, name);
        return;
    }
    Resolving *resolving = g_new0(Resolving, 1);
    resolving->discovery = discovery;
    resolving->name = g_strdup(name);
    if (DNSServiceResolve(&resolving->ref, 0, interface, name, type, domain, on_resolved,
                          resolving) != kDNSServiceErr_NoError) {
        resolving->ref = NULL;
        resolving_free(resolving);
        return;
    }
    resolving->source = watch(resolving->ref);
    g_hash_table_replace(state->resolving, g_strdup(name), resolving);
}

static gboolean
dnssd_start(KrDiscovery *discovery, GError **error)
{
    DnssdState *state = g_new0(DnssdState, 1);
    state->resolving =
        g_hash_table_new_full(g_str_hash, g_str_equal, g_free, (GDestroyNotify) resolving_free);
    discovery->backend_data = state;
    DNSServiceErrorType failure = DNSServiceBrowse(&state->browse, 0, kDNSServiceInterfaceIndexAny,
                                                   KR_DISCOVERY_SERVICE_TYPE, NULL, on_browse,
                                                   discovery);
    if (failure != kDNSServiceErr_NoError) {
        state->browse = NULL;
        g_set_error(error, G_IO_ERROR, G_IO_ERROR_NOT_FOUND,
                    "cannot browse for hubs with Bonjour (error %d)", (int) failure);
        return FALSE;
    }
    state->browse_source = watch(state->browse);
    return TRUE;
}

static void
dnssd_stop(KrDiscovery *discovery)
{
    DnssdState *state = discovery->backend_data;
    if (state == NULL)
        return;
    g_hash_table_unref(state->resolving);
    if (state->browse_source != NULL) {
        g_source_destroy(state->browse_source);
        g_source_unref(state->browse_source);
    }
    if (state->browse != NULL)
        DNSServiceRefDeallocate(state->browse);
    g_free(state);
    discovery->backend_data = NULL;
}

const KrDiscoveryBackend kr_discovery_dnssd_backend = {
    .name = "dns_sd",
    .start = dnssd_start,
    .stop = dnssd_stop,
};
