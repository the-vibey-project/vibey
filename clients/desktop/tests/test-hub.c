/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include <glib/gstdio.h>
#include <unistd.h>

#include "kr-hub.h"

static void
base_is(KrHubEndpoint *endpoint, const char *want)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *base = kr_hub_endpoint_base(endpoint, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(base, ==, want);
    kr_hub_endpoint_free(endpoint);
}

static void
base_refused(KrHubEndpoint *endpoint)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *base = kr_hub_endpoint_base(endpoint, &error);
    g_assert_null(base);
    g_assert_error(error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT);
    kr_hub_endpoint_free(endpoint);
}

static void
test_endpoint(void)
{
    base_is(kr_hub_endpoint_new_local("t"), "http://127.0.0.1:8765");
    base_is(kr_hub_endpoint_new(NULL, NULL, 0, NULL), "http://127.0.0.1:8765");
    base_is(kr_hub_endpoint_new("https", "studio.local", 9000, NULL), "https://studio.local:9000");
    base_is(kr_hub_endpoint_new("https", "fe80::1", 8765, NULL), "https://[fe80::1]:8765");
    base_is(kr_hub_endpoint_new("https", "[::1]", 8765, NULL), "https://[::1]:8765");
    base_refused(kr_hub_endpoint_new("ftp", "x", 1, NULL));
    base_refused(kr_hub_endpoint_new("http", "", 1, NULL));
    base_refused(kr_hub_endpoint_new("http", "evil.com/x", 1, NULL));
    base_refused(kr_hub_endpoint_new("http", "user@host", 1, NULL));

    g_autoptr(KrHubEndpoint) original = kr_hub_endpoint_new("https", "h", 1, "secret");
    g_autoptr(KrHubEndpoint) copy = kr_hub_endpoint_copy(original);
    g_assert_cmpstr(copy->token, ==, "secret");
    g_assert_cmpstr(copy->host, ==, "h");
    kr_hub_endpoint_free(NULL);
}

static void
path_is(KrHubRoute route, const char *project, const char *id, const char *want)
{
    g_autofree char *path = kr_hub_path(route, project, id);
    g_assert_cmpstr(path, ==, want);
}

static void
test_paths(void)
{
    path_is(KR_HUB_ROUTE_HEALTH_LIVE, NULL, NULL, "/health/live");
    path_is(KR_HUB_ROUTE_HEALTH_READY, NULL, NULL, "/health/ready");
    path_is(KR_HUB_ROUTE_PROJECTS, NULL, NULL, "/api/v1/projects");
    path_is(KR_HUB_ROUTE_PROJECT_STATUS, "p 1", NULL, "/api/v1/projects/p%201/status");
    path_is(KR_HUB_ROUTE_PROJECT_STATUS, NULL, NULL, NULL);
    path_is(KR_HUB_ROUTE_PROJECT_BUDGET, "p", NULL, "/api/v1/projects/p/budget");
    path_is(KR_HUB_ROUTE_PROJECT_BUDGET, "", NULL, NULL);
    path_is(KR_HUB_ROUTE_PROJECT_QUEUE, "p", NULL, "/api/v1/projects/p/queue");
    path_is(KR_HUB_ROUTE_PROJECT_QUEUE, NULL, NULL, NULL);
    path_is(KR_HUB_ROUTE_JOB_BUMP, "p", "j/../x", "/api/v1/projects/p/queue/j%2F..%2Fx/bump");
    path_is(KR_HUB_ROUTE_JOB_BUMP, "p", NULL, NULL);
    path_is(KR_HUB_ROUTE_GATES, NULL, NULL, "/api/v1/gates");
    path_is(KR_HUB_ROUTE_GATES, "p&x=1", NULL, "/api/v1/gates?project_id=p%26x%3D1");
    path_is(KR_HUB_ROUTE_GATE_ANSWER, NULL, "g", "/api/v1/gates/g/answer");
    path_is(KR_HUB_ROUTE_GATE_ANSWER, NULL, NULL, NULL);
    path_is(KR_HUB_ROUTE_LANES, NULL, NULL, "/api/v1/lanes");
    path_is(KR_HUB_ROUTE_LOOPS, NULL, NULL, "/api/v1/loops");
    path_is(KR_HUB_ROUTE_DOCTOR, NULL, NULL, "/api/v1/doctor");
    path_is((KrHubRoute) 999, NULL, NULL, NULL);

    g_assert_true(kr_hub_route_writes(KR_HUB_ROUTE_GATE_ANSWER));
    g_assert_true(kr_hub_route_writes(KR_HUB_ROUTE_JOB_BUMP));
    g_assert_false(kr_hub_route_writes(KR_HUB_ROUTE_PROJECTS));
}

static char *
write_token(const char *dir, const char *name, const char *content, int mode)
{
    char *path = g_build_filename(dir, name, NULL);
    g_assert_true(g_file_set_contents(path, content, -1, NULL));
    g_assert_cmpint(g_chmod(path, mode), ==, 0);
    return path;
}

static void
token_refused(const char *path)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *token = kr_hub_read_token(path, &error);
    g_assert_null(token);
    g_assert_error(error, KR_HUB_ERROR, KR_HUB_ERROR_TOKEN);
}

static void
test_token(void)
{
    g_autofree char *dir = g_dir_make_tmp("krypton-token-XXXXXX", NULL);
    g_autofree char *good = write_token(dir, "good", "  abc123\n", 0600);
    g_autoptr(GError) error = NULL;
    g_autofree char *token = kr_hub_read_token(good, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(token, ==, "abc123");

    g_autofree char *shared = write_token(dir, "shared", "abc", 0644);
    token_refused(shared);
    g_autofree char *empty = write_token(dir, "empty", " \n", 0600);
    token_refused(empty);
    g_autofree char *two = write_token(dir, "two", "a\nb", 0600);
    token_refused(two);
    g_autofree char *missing = g_build_filename(dir, "missing", NULL);
    token_refused(missing);
    g_autofree char *link = g_build_filename(dir, "link", NULL);
    g_assert_cmpint(symlink(good, link), ==, 0);
    token_refused(link);
    token_refused(dir);
    g_autofree char *unreadable = write_token(dir, "unreadable", "abc", 0200);
    if (geteuid() != 0)
        token_refused(unreadable);

    for (const char *const *name = (const char *const[]){"good", "shared", "empty", "two", "link",
                                                        "unreadable", NULL};
         *name != NULL; name++) {
        g_autofree char *path = g_build_filename(dir, *name, NULL);
        g_unlink(path);
    }
    g_rmdir(dir);
}

static void
test_token_path(void)
{
    g_autofree char *explicit = kr_hub_token_path("/var/hub");
    g_assert_cmpstr(explicit, ==, "/var/hub/token");
    g_autofree char *fallback = kr_hub_token_path(NULL);
    g_assert_true(g_str_has_suffix(fallback, "/vibey/hub/token"));
    g_autofree char *empty = kr_hub_token_path("");
    g_assert_cmpstr(empty, ==, fallback);
}

static void
test_status_text(void)
{
    const guint statuses[] = {401, 403, 404, 409, 421, 422, 429, 503};
    for (size_t i = 0; i < G_N_ELEMENTS(statuses); i++) {
        const char *text = kr_hub_status_text(statuses[i]);
        g_assert_nonnull(text);
        g_assert_cmpstr(text, !=, kr_hub_status_text(418));
    }
    g_assert_cmpstr(kr_hub_status_text(200), ==, "OK");
    g_assert_cmpstr(kr_hub_status_text(500), ==, "The hub failed while answering.");
    g_assert_cmpstr(kr_hub_status_text(418), ==, "The hub refused the request.");
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/hub/endpoint", test_endpoint);
    g_test_add_func("/hub/paths", test_paths);
    g_test_add_func("/hub/token", test_token);
    g_test_add_func("/hub/token-path", test_token_path);
    g_test_add_func("/hub/status-text", test_status_text);
    return g_test_run();
}
