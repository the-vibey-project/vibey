/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-hub.h"

#include <errno.h>
#include <fcntl.h>
#include <glib/gstdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

G_DEFINE_QUARK(kr-hub-error-quark, kr_hub_error)

/* The most a token file may hold: the hub writes 32 random bytes, well under this. */
#define TOKEN_MAX 4096

/* Overwrites a secret before its memory is released. A volatile store is not optimised
 * away, and explicit_bzero is not on every platform this builds for. */
static void
wipe(void *memory, size_t size)
{
    volatile unsigned char *byte = memory;
    while (size-- > 0)
        *byte++ = 0;
}

KrHubEndpoint *
kr_hub_endpoint_new(const char *scheme, const char *host, guint16 port, const char *token)
{
    KrHubEndpoint *endpoint = g_new0(KrHubEndpoint, 1);
    endpoint->scheme = g_strdup(scheme != NULL ? scheme : "http");
    endpoint->host = g_strdup(host != NULL ? host : KR_HUB_DEFAULT_HOST);
    endpoint->port = port != 0 ? port : KR_HUB_DEFAULT_PORT;
    endpoint->token = g_strdup(token);
    return endpoint;
}

KrHubEndpoint *
kr_hub_endpoint_new_local(const char *token)
{
    return kr_hub_endpoint_new("http", KR_HUB_DEFAULT_HOST, KR_HUB_DEFAULT_PORT, token);
}

KrHubEndpoint *
kr_hub_endpoint_copy(const KrHubEndpoint *endpoint)
{
    return kr_hub_endpoint_new(endpoint->scheme, endpoint->host, endpoint->port,
                               endpoint->token);
}

void
kr_hub_endpoint_free(KrHubEndpoint *endpoint)
{
    if (endpoint == NULL)
        return;
    g_free(endpoint->scheme);
    g_free(endpoint->host);
    if (endpoint->token != NULL)
        wipe(endpoint->token, strlen(endpoint->token));
    g_free(endpoint->token);
    g_free(endpoint);
}

char *
kr_hub_endpoint_base(const KrHubEndpoint *endpoint, GError **error)
{
    if (!g_str_equal(endpoint->scheme, "http") && !g_str_equal(endpoint->scheme, "https")) {
        g_set_error(error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT, "the hub speaks http or https, "
                    "not %s", endpoint->scheme);
        return NULL;
    }
    const char *host = endpoint->host;
    if (*host == '\0' || strpbrk(host, "/?#@ \t\r\n") != NULL) {
        g_set_error(error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT, "\"%s\" is not a host name",
                    host);
        return NULL;
    }
    /* An IPv6 literal goes in brackets; one already bracketed stays as it is. */
    gboolean v6 = strchr(host, ':') != NULL && host[0] != '[';
    return g_strdup_printf("%s://%s%s%s:%u", endpoint->scheme, v6 ? "[" : "", host, v6 ? "]" : "",
                           endpoint->port);
}

static gboolean
present(const char *text)
{
    return text != NULL && *text != '\0';
}

char *
kr_hub_path(KrHubRoute route, const char *project_id, const char *id)
{
    g_autofree char *project = present(project_id) ? g_uri_escape_string(project_id, NULL, FALSE)
                                                   : NULL;
    g_autofree char *other = present(id) ? g_uri_escape_string(id, NULL, FALSE) : NULL;

    switch (route) {
    case KR_HUB_ROUTE_HEALTH_LIVE:
        return g_strdup("/health/live");
    case KR_HUB_ROUTE_HEALTH_READY:
        return g_strdup("/health/ready");
    case KR_HUB_ROUTE_PROJECTS:
        return g_strdup("/api/v1/projects");
    case KR_HUB_ROUTE_PROJECT_STATUS:
        return project ? g_strdup_printf("/api/v1/projects/%s/status", project) : NULL;
    case KR_HUB_ROUTE_PROJECT_BUDGET:
        return project ? g_strdup_printf("/api/v1/projects/%s/budget", project) : NULL;
    case KR_HUB_ROUTE_PROJECT_QUEUE:
        return project ? g_strdup_printf("/api/v1/projects/%s/queue", project) : NULL;
    case KR_HUB_ROUTE_JOB_BUMP:
        return project && other
                   ? g_strdup_printf("/api/v1/projects/%s/queue/%s/bump", project, other)
                   : NULL;
    case KR_HUB_ROUTE_GATES:
        return project ? g_strdup_printf("/api/v1/gates?project_id=%s", project)
                       : g_strdup("/api/v1/gates");
    case KR_HUB_ROUTE_GATE_ANSWER:
        return other ? g_strdup_printf("/api/v1/gates/%s/answer", other) : NULL;
    case KR_HUB_ROUTE_LANES:
        return g_strdup("/api/v1/lanes");
    case KR_HUB_ROUTE_LOOPS:
        return g_strdup("/api/v1/loops");
    case KR_HUB_ROUTE_DOCTOR:
        return g_strdup("/api/v1/doctor");
    }
    return NULL;
}

gboolean
kr_hub_route_writes(KrHubRoute route)
{
    return route == KR_HUB_ROUTE_JOB_BUMP || route == KR_HUB_ROUTE_GATE_ANSWER;
}

static gboolean
token_error(GError **error, const char *path, const char *why)
{
    g_set_error(error, KR_HUB_ERROR, KR_HUB_ERROR_TOKEN, "the hub token %s %s", path, why);
    return FALSE;
}

char *
kr_hub_read_token(const char *path, GError **error)
{
    /* O_NOFOLLOW: a symlink is refused, as the hub refuses one (ADR-0068). The checks are
     * made on the open descriptor, so the file cannot be swapped between check and read. */
    int fd = g_open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC, 0);
    if (fd < 0) {
        token_error(error, path, errno == ELOOP ? "is a symlink" : g_strerror(errno));
        return NULL;
    }
    struct stat info;
    if (fstat(fd, &info) != 0 || !S_ISREG(info.st_mode)) {
        close(fd);
        token_error(error, path, "is not a regular file");
        return NULL;
    }
    if ((info.st_mode & (S_IRWXG | S_IRWXO)) != 0) {
        close(fd);
        token_error(error, path, "can be read by others: it must be mode 0600");
        return NULL;
    }
    char buffer[TOKEN_MAX + 1];
    ssize_t got = read(fd, buffer, TOKEN_MAX);
    close(fd);
    if (got < 0) {
        token_error(error, path, "cannot be read");
        return NULL;
    }
    buffer[got] = '\0';
    char *token = g_strstrip(g_strdup(buffer));
    wipe(buffer, sizeof buffer);
    if (*token == '\0' || strpbrk(token, "\r\n") != NULL) {
        g_free(token);
        token_error(error, path, "does not hold one token");
        return NULL;
    }
    return token;
}

char *
kr_hub_token_path(const char *state_dir)
{
    if (present(state_dir))
        return g_build_filename(state_dir, "token", NULL);
#ifdef __APPLE__
    return g_build_filename(g_get_home_dir(), "Library", "Application Support", "vibey", "hub",
                            "token", NULL);
#else
    return g_build_filename(g_get_user_state_dir(), "vibey", "hub", "token", NULL);
#endif
}

const char *
kr_hub_status_text(guint status)
{
    switch (status) {
    case 401:
        return "The hub does not know this device. Pair it again.";
    case 403:
        return "This device may not do that. Its scopes do not permit it.";
    case 404:
        return "That project or gate is not there any more.";
    case 409:
        return "Someone else answered first, or the queue refused the change.";
    case 421:
        return "The hub does not answer to that address. Check its [hub] names.";
    case 422:
        return "The hub could not read that request.";
    case 429:
        return "Too many requests. Krypton will try again shortly.";
    case 503:
        return "The hub is up, but its database is not answering.";
    default:
        if (status >= 200 && status < 300)
            return "OK";
        if (status >= 500)
            return "The hub failed while answering.";
        return "The hub refused the request.";
    }
}
