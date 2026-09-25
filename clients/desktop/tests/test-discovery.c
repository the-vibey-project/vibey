/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include <gio/gio.h>

#include "kr-discovery.h"

/* A backend under the test's control: it reports what the test tells it to. */
static gboolean fake_fails;
static int fake_started;
static int fake_stopped;

static gboolean
fake_start(KrDiscovery *discovery, GError **error)
{
    (void) discovery;
    fake_started++;
    if (fake_fails) {
        g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_NOT_FOUND, "no daemon");
        return FALSE;
    }
    return TRUE;
}

static void
fake_stop(KrDiscovery *discovery)
{
    (void) discovery;
    fake_stopped++;
}

static const KrDiscoveryBackend FAKE = {"fake", fake_start, fake_stop};

typedef struct {
    GPtrArray *found;
    GPtrArray *lost;
} Heard;

static void
on_found(const KrHubService *service, gpointer data)
{
    Heard *heard = data;
    g_ptr_array_add(heard->found, g_strdup(service->name));
}

static void
on_lost(const char *name, gpointer data)
{
    Heard *heard = data;
    g_ptr_array_add(heard->lost, g_strdup(name));
}

static void
test_txt(void)
{
    const char *const txt[] = {"Version=3.0.0", "path=/api/v1", "flag", NULL};
    g_assert_cmpstr(kr_txt_lookup(txt, "version"), ==, "3.0.0");
    g_assert_cmpstr(kr_txt_lookup(txt, "PATH"), ==, "/api/v1");
    g_assert_cmpstr(kr_txt_lookup(txt, "flag"), ==, "");
    g_assert_null(kr_txt_lookup(txt, "fla"));
    g_assert_null(kr_txt_lookup(txt, "missing"));
    g_assert_null(kr_txt_lookup(NULL, "version"));
}

static void
test_service(void)
{
    const char *const txt[] = {"version=3.0.0", NULL};
    g_autoptr(KrHubService) service = kr_hub_service_new("Studio", "studio.local", 8765, txt);
    g_assert_cmpstr(service->version, ==, "3.0.0");
    g_assert_cmpstr(service->path, ==, "/api/v1");
    g_autoptr(KrHubService) copy = kr_hub_service_copy(service);
    g_assert_cmpstr(copy->host, ==, "studio.local");
    g_assert_cmpuint(copy->port, ==, 8765);

    g_autoptr(KrHubService) bare = kr_hub_service_new("S", "h", 1, NULL);
    g_assert_null(bare->version);
    g_assert_null(kr_hub_service_new("", "h", 1, NULL));
    g_assert_null(kr_hub_service_new("S", NULL, 1, NULL));
    g_assert_null(kr_hub_service_new("S", "h", 0, NULL));
    kr_hub_service_free(NULL);
}

static void
test_discovery(void)
{
    Heard heard = {g_ptr_array_new_with_free_func(g_free), g_ptr_array_new_with_free_func(g_free)};
    fake_fails = FALSE;
    fake_started = fake_stopped = 0;
    KrDiscovery *discovery = kr_discovery_new(&FAKE, on_found, on_lost, &heard);
    g_assert_nonnull(discovery);
    g_assert_true(kr_discovery_start(discovery, NULL));
    g_assert_cmpint(fake_started, ==, 1);

    g_autoptr(KrHubService) b = kr_hub_service_new("Beta", "b.local", 8765, NULL);
    g_autoptr(KrHubService) a = kr_hub_service_new("Alpha", "a.local", 8765, NULL);
    g_autoptr(KrHubService) moved = kr_hub_service_new("Beta", "b.local", 9000, NULL);
    kr_discovery_report_found(discovery, b);
    kr_discovery_report_found(discovery, a);
    kr_discovery_report_found(discovery, b); /* the same again: not reported twice */
    kr_discovery_report_found(discovery, moved);
    g_assert_cmpuint(heard.found->len, ==, 3);

    g_autoptr(GPtrArray) seen = kr_discovery_services(discovery);
    g_assert_cmpuint(seen->len, ==, 2);
    g_assert_cmpstr(((KrHubService *) g_ptr_array_index(seen, 0))->name, ==, "Alpha");
    g_assert_cmpuint(((KrHubService *) g_ptr_array_index(seen, 1))->port, ==, 9000);

    kr_discovery_report_lost(discovery, "Alpha");
    kr_discovery_report_lost(discovery, "Alpha"); /* already gone */
    g_assert_cmpuint(heard.lost->len, ==, 1);

    kr_discovery_free(discovery);
    g_assert_cmpint(fake_stopped, ==, 1);
    kr_discovery_free(NULL);
    g_ptr_array_unref(heard.found);
    g_ptr_array_unref(heard.lost);
}

static void
test_quiet_listener_and_failure(void)
{
    fake_fails = TRUE;
    KrDiscovery *discovery = kr_discovery_new(&FAKE, NULL, NULL, NULL);
    g_autoptr(GError) error = NULL;
    g_assert_false(kr_discovery_start(discovery, &error));
    g_assert_error(error, G_IO_ERROR, G_IO_ERROR_NOT_FOUND);
    g_autoptr(KrHubService) service = kr_hub_service_new("S", "h", 1, NULL);
    kr_discovery_report_found(discovery, service);
    kr_discovery_report_lost(discovery, "S");
    kr_discovery_free(discovery);
}

static void
test_platform(void)
{
    const KrDiscoveryBackend *backend = kr_discovery_platform_backend();
    KrDiscovery *discovery = kr_discovery_new(NULL, NULL, NULL, NULL);
    if (backend == NULL) {
        g_assert_null(discovery);
        return;
    }
    g_assert_nonnull(backend->name);
    g_assert_true(discovery->backend == backend);
    /* Browsing is not started here: a CI runner has no mDNS daemon to talk to. */
    discovery->backend = &FAKE;
    kr_discovery_free(discovery);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/discovery/txt", test_txt);
    g_test_add_func("/discovery/service", test_service);
    g_test_add_func("/discovery/found-and-lost", test_discovery);
    g_test_add_func("/discovery/quiet-and-failing", test_quiet_listener_and_failure);
    g_test_add_func("/discovery/platform", test_platform);
    return g_test_run();
}
