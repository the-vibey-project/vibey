/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The Linux discovery backend: Avahi's client library, driven by the GLib main loop. */
#include "kr-discovery.h"

#include <avahi-client/client.h>
#include <avahi-client/lookup.h>
#include <avahi-common/error.h>
#include <avahi-common/strlst.h>
#include <avahi-glib/glib-watch.h>
#include <gio/gio.h>

typedef struct {
    AvahiGLibPoll *poll;
    AvahiClient *client;
    AvahiServiceBrowser *browser;
} AvahiState;

static void
on_resolved(AvahiServiceResolver *resolver, AvahiIfIndex interface, AvahiProtocol protocol,
            AvahiResolverEvent event, const char *name, const char *type, const char *domain,
            const char *host_name, const AvahiAddress *address, uint16_t port,
            AvahiStringList *txt, AvahiLookupResultFlags flags, void *user_data)
{
    (void) interface;
    (void) protocol;
    (void) type;
    (void) domain;
    (void) address;
    (void) flags;
    KrDiscovery *discovery = user_data;
    if (event == AVAHI_RESOLVER_FOUND) {
        GStrvBuilder *builder = g_strv_builder_new();
        for (AvahiStringList *entry = txt; entry != NULL; entry = avahi_string_list_get_next(entry))
            g_strv_builder_take(builder, g_strndup((const char *) avahi_string_list_get_text(entry),
                                                   avahi_string_list_get_size(entry)));
        g_auto(GStrv) strings = g_strv_builder_end(builder);
        g_strv_builder_unref(builder);
        g_autoptr(KrHubService) service =
            kr_hub_service_new(name, host_name, port, (const char *const *) strings);
        if (service != NULL)
            kr_discovery_report_found(discovery, service);
    }
    avahi_service_resolver_free(resolver);
}

static void
on_browse(AvahiServiceBrowser *browser, AvahiIfIndex interface, AvahiProtocol protocol,
          AvahiBrowserEvent event, const char *name, const char *type, const char *domain,
          AvahiLookupResultFlags flags, void *user_data)
{
    (void) flags;
    KrDiscovery *discovery = user_data;
    AvahiClient *client = avahi_service_browser_get_client(browser);
    switch (event) {
    case AVAHI_BROWSER_NEW:
        /* The resolver frees itself in on_resolved; a failure to create one is a hub we
         * simply do not show, never a crash. */
        (void) avahi_service_resolver_new(client, interface, protocol, name, type, domain,
                                          AVAHI_PROTO_UNSPEC, 0, on_resolved, discovery);
        break;
    case AVAHI_BROWSER_REMOVE:
        kr_discovery_report_lost(discovery, name);
        break;
    case AVAHI_BROWSER_FAILURE:
    case AVAHI_BROWSER_ALL_FOR_NOW:
    case AVAHI_BROWSER_CACHE_EXHAUSTED:
        break;
    }
}

static void
on_client(AvahiClient *client, AvahiClientState state, void *user_data)
{
    (void) client;
    (void) state;
    (void) user_data;
}

static gboolean
avahi_start(KrDiscovery *discovery, GError **error)
{
    AvahiState *state = g_new0(AvahiState, 1);
    discovery->backend_data = state;
    state->poll = avahi_glib_poll_new(NULL, G_PRIORITY_DEFAULT);
    int failure = 0;
    state->client = avahi_client_new(avahi_glib_poll_get(state->poll), AVAHI_CLIENT_NO_FAIL,
                                     on_client, discovery, &failure);
    if (state->client == NULL) {
        g_set_error(error, G_IO_ERROR, G_IO_ERROR_NOT_FOUND,
                    "cannot reach the Avahi daemon: %s", avahi_strerror(failure));
        return FALSE;
    }
    state->browser = avahi_service_browser_new(state->client, AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC,
                                               KR_DISCOVERY_SERVICE_TYPE, NULL, 0, on_browse,
                                               discovery);
    if (state->browser == NULL) {
        g_set_error(error, G_IO_ERROR, G_IO_ERROR_FAILED, "cannot browse for hubs: %s",
                    avahi_strerror(avahi_client_errno(state->client)));
        return FALSE;
    }
    return TRUE;
}

static void
avahi_stop(KrDiscovery *discovery)
{
    AvahiState *state = discovery->backend_data;
    if (state == NULL)
        return;
    if (state->browser != NULL)
        avahi_service_browser_free(state->browser);
    if (state->client != NULL)
        avahi_client_free(state->client);
    if (state->poll != NULL)
        avahi_glib_poll_free(state->poll);
    g_free(state);
    discovery->backend_data = NULL;
}

const KrDiscoveryBackend kr_discovery_avahi_backend = {
    .name = "avahi",
    .start = avahi_start,
    .stop = avahi_stop,
};
