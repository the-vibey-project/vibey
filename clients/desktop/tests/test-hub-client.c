/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The hub client against a real HTTP server on loopback (libsoup's own SoupServer), playing
 * the hub's routes: the bearer token, a paired device's signature (checked here the way
 * DeviceAuthenticator checks it), the methods, the bodies and the refusals; then pairing --
 * the claim, every way it can be refused, and the certificate pin over real TLS. */
#include <glib/gstdio.h>
#include <libsoup/soup.h>
#include <string.h>
#include <sys/stat.h>

#include "kr-hub-client.h"
#include "kr-model.h"
#include "kr-pairing-client.h"

#define DEVICE_ID "dev-1"
#define DEVICE_KEY "k3y-from-the-hub"
#define PINNED_ELSEWHERE "0000000000000000000000000000000000000000000000000000000000000000"

typedef struct {
    SoupServer *server;
    guint16 port;
    char *fingerprint; /* the certificate's, when the hub serves TLS */
    guint requests;
    char *last_method;
    char *last_path;
    char *last_body;
    char *last_auth;
    char *last_device;
    /* What the claim route answers: its status, and the body it sends. */
    guint claim_status;
    const char *claim_body;
} Hub;

static const char *
header(SoupServerMessage *message, const char *name)
{
    return soup_message_headers_get_one(soup_server_message_get_request_headers(message), name);
}

/* DeviceAuthenticator's check: the canonical form, signed with the device's key. */
static gboolean
signed_by_device(SoupServerMessage *message, const char *path, const char *body)
{
    const char *device = header(message, "x-vibey-device");
    const char *stamp = header(message, "x-vibey-timestamp");
    const char *nonce = header(message, "x-vibey-nonce");
    const char *signature = header(message, "x-vibey-signature");
    if (g_strcmp0(device, DEVICE_ID) != 0 || stamp == NULL || nonce == NULL || signature == NULL)
        return FALSE;
    const char *query = g_uri_get_query(soup_server_message_get_uri(message));
    g_autofree char *digest = g_compute_checksum_for_string(G_CHECKSUM_SHA256, body, -1);
    g_autofree char *canonical =
        g_strjoin("\n", device, soup_server_message_get_method(message), path,
                  query != NULL ? query : "", stamp, nonce, digest, NULL);
    g_autofree char *expected = g_compute_hmac_for_string(
        G_CHECKSUM_SHA256, (const guchar *) DEVICE_KEY, strlen(DEVICE_KEY), canonical, -1);
    g_autofree char *with_prefix = g_strconcat("sha256=", expected, NULL);
    gint64 age = g_get_real_time() / G_USEC_PER_SEC - g_ascii_strtoll(stamp, NULL, 10);
    return g_str_equal(signature, with_prefix) && age > -60 && age < 60;
}

static void
respond(SoupServerMessage *message, guint status, const char *doc)
{
    soup_server_message_set_status(message, status, NULL);
    if (doc != NULL)
        soup_server_message_set_response(message, "application/json", SOUP_MEMORY_COPY, doc,
                                          strlen(doc));
}

static void
serve(SoupServer *server, SoupServerMessage *message, const char *path, GHashTable *query,
      gpointer data)
{
    (void) server;
    (void) query;
    Hub *hub = data;
    hub->requests++;
    g_free(hub->last_method);
    g_free(hub->last_path);
    g_free(hub->last_body);
    g_free(hub->last_auth);
    g_free(hub->last_device);
    hub->last_method = g_strdup(soup_server_message_get_method(message));
    hub->last_path = g_strdup(path);
    SoupMessageBody *body = soup_server_message_get_request_body(message);
    hub->last_body = g_strndup(body->data != NULL ? body->data : "", (gsize) body->length);
    hub->last_auth = g_strdup(header(message, "Authorization"));
    hub->last_device = g_strdup(header(message, "x-vibey-device"));

    if (g_str_equal(path, "/api/v1/pairing/claim")) {
        respond(message, hub->claim_status, hub->claim_body);
        return;
    }
    gboolean host = g_strcmp0(hub->last_auth, "Bearer good") == 0;
    if (!host && !signed_by_device(message, path, hub->last_body)) {
        soup_server_message_set_status(message, 401, NULL);
        return;
    }
    if (g_str_equal(path, "/api/v1/projects")) {
        respond(message, 200, "[{\"project_id\": \"p\", \"name\": \"greeter\"}]");
        return;
    }
    if (g_str_equal(path, "/api/v1/gates/g-1/answer")) {
        soup_server_message_set_status(message, 409, NULL);
        return;
    }
    if (g_str_equal(path, "/api/v1/lanes")) {
        soup_server_message_set_redirect(message, 302, "http://127.0.0.1:1/elsewhere");
        return;
    }
    soup_server_message_set_status(message, 404, NULL);
}

static void
hub_listen(Hub *hub, GTlsCertificate *certificate)
{
    hub->server = certificate != NULL ? soup_server_new("tls-certificate", certificate, NULL)
                                      : soup_server_new(NULL, NULL);
    soup_server_add_handler(hub->server, NULL, serve, hub, NULL);
    g_autoptr(GError) error = NULL;
    SoupServerListenOptions options = SOUP_SERVER_LISTEN_IPV4_ONLY;
    if (certificate != NULL)
        options |= SOUP_SERVER_LISTEN_HTTPS;
    g_assert_true(soup_server_listen_local(hub->server, 0, options, &error));
    g_assert_no_error(error);
    GSList *uris = soup_server_get_uris(hub->server);
    hub->port = (guint16) g_uri_get_port(uris->data);
    g_slist_free_full(uris, (GDestroyNotify) g_uri_unref);
    hub->claim_status = 200;
}

static void
hub_start(Hub *hub)
{
    hub_listen(hub, NULL);
}

static void
hub_stop(Hub *hub)
{
    soup_server_disconnect(hub->server);
    g_object_unref(hub->server);
    g_free(hub->fingerprint);
    g_free(hub->last_method);
    g_free(hub->last_path);
    g_free(hub->last_body);
    g_free(hub->last_auth);
    g_free(hub->last_device);
}

typedef struct {
    GBytes *body;
    guint status;
    GError *error;
    gboolean done;
} Outcome;

static void
on_done(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Outcome *outcome = data;
    outcome->body = kr_hub_client_call_finish(NULL, result, &outcome->status, &outcome->error);
    outcome->done = TRUE;
}

static Outcome
call(KrHubClient *client, KrHubRoute route, const char *project, const char *id, const char *body)
{
    Outcome outcome = {0};
    kr_hub_client_call_async(client, route, project, id, body, NULL, on_done, &outcome);
    while (!outcome.done)
        g_main_context_iteration(NULL, TRUE);
    return outcome;
}

static void
outcome_clear(Outcome *outcome)
{
    g_clear_pointer(&outcome->body, g_bytes_unref);
    g_clear_error(&outcome->error);
}

static void
test_reads_with_the_token(void)
{
    Hub hub = {0};
    hub_start(&hub);
    g_autoptr(KrHubEndpoint) endpoint = kr_hub_endpoint_new("http", "127.0.0.1", hub.port, "good");
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 5);
    g_assert_cmpuint(kr_hub_client_endpoint(client)->port, ==, hub.port);

    Outcome ok = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_no_error(ok.error);
    g_assert_cmpuint(ok.status, ==, 200);
    gsize size = 0;
    const char *text = g_bytes_get_data(ok.body, &size);
    g_autoptr(GError) error = NULL;
    g_autoptr(GPtrArray) projects = kr_projects_parse(text, (gssize) size, &error);
    g_assert_no_error(error);
    g_assert_cmpuint(projects->len, ==, 1);
    g_assert_cmpstr(hub.last_method, ==, "GET");
    g_assert_cmpstr(hub.last_auth, ==, "Bearer good");
    g_assert_null(hub.last_device);
    outcome_clear(&ok);

    Outcome missing = call(client, KR_HUB_ROUTE_DOCTOR, NULL, NULL, NULL);
    g_assert_error(missing.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(missing.status, ==, 404);
    outcome_clear(&missing);

    hub_stop(&hub);
}

static void
test_writes_and_refusals(void)
{
    Hub hub = {0};
    hub_start(&hub);
    g_autoptr(KrHubEndpoint) endpoint = kr_hub_endpoint_new("http", "127.0.0.1", hub.port, "good");
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 0);

    Outcome answered = call(client, KR_HUB_ROUTE_GATE_ANSWER, NULL, "g-1", "{\"answer\":{}}");
    g_assert_error(answered.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(answered.status, ==, 409);
    g_assert_cmpstr(hub.last_method, ==, "POST");
    g_assert_cmpstr(hub.last_body, ==, "{\"answer\":{}}");
    outcome_clear(&answered);

    Outcome bumped = call(client, KR_HUB_ROUTE_JOB_BUMP, "p", "j", NULL);
    g_assert_cmpstr(hub.last_body, ==, "{}");
    g_assert_cmpuint(bumped.status, ==, 404);
    outcome_clear(&bumped);

    Outcome redirected = call(client, KR_HUB_ROUTE_LANES, NULL, NULL, NULL);
    g_assert_error(redirected.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(redirected.status, ==, 302);
    outcome_clear(&redirected);

    Outcome no_id = call(client, KR_HUB_ROUTE_GATE_ANSWER, NULL, NULL, NULL);
    g_assert_error(no_id.error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT);
    outcome_clear(&no_id);

    g_autoptr(KrHubEndpoint) stranger = kr_hub_endpoint_new("http", "127.0.0.1", hub.port, NULL);
    g_autoptr(KrHubClient) anonymous = kr_hub_client_new(stranger, 5);
    Outcome refused = call(anonymous, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(refused.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(refused.status, ==, 401);
    g_assert_null(hub.last_auth);
    outcome_clear(&refused);

    hub_stop(&hub);
}

static void
test_bad_endpoints(void)
{
    g_autoptr(KrHubEndpoint) ftp = kr_hub_endpoint_new("ftp", "h", 1, NULL);
    g_autoptr(KrHubClient) client = kr_hub_client_new(ftp, 5);
    Outcome bad = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(bad.error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT);
    outcome_clear(&bad);

    /* Port 1 on loopback: nothing listens, so nothing answers. */
    g_autoptr(KrHubEndpoint) closed = kr_hub_endpoint_new("http", "127.0.0.1", 1, "good");
    g_autoptr(KrHubClient) nobody = kr_hub_client_new(closed, 5);
    Outcome silent = call(nobody, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(silent.error, KR_HUB_ERROR, KR_HUB_ERROR_TRANSPORT);
    g_assert_cmpuint(silent.status, ==, 0);
    outcome_clear(&silent);
    kr_hub_client_free(NULL);
}

/* ---- a paired device ------------------------------------------------------------------ */

static void
test_signed_requests(void)
{
    Hub hub = {0};
    hub_start(&hub);
    g_autoptr(KrHubEndpoint) device =
        kr_hub_endpoint_new_device("http", "127.0.0.1", hub.port, DEVICE_ID, DEVICE_KEY, NULL);
    g_autoptr(KrHubClient) client = kr_hub_client_new(device, 5);

    Outcome read = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_no_error(read.error);
    g_assert_cmpuint(read.status, ==, 200);
    g_assert_cmpstr(hub.last_device, ==, DEVICE_ID);
    g_assert_null(hub.last_auth); /* the key signs; it is never sent */
    outcome_clear(&read);

    /* A write's signature covers its body; the query is signed as sent. */
    Outcome answered = call(client, KR_HUB_ROUTE_GATE_ANSWER, NULL, "g-1", "{\"answer\":{}}");
    g_assert_cmpuint(answered.status, ==, 409);
    outcome_clear(&answered);
    Outcome gates = call(client, KR_HUB_ROUTE_GATES, "p 1", NULL, NULL);
    g_assert_cmpuint(gates.status, ==, 404); /* signed and admitted; the fake has no gates */
    outcome_clear(&gates);

    /* A key the hub did not give proves nothing. */
    g_autoptr(KrHubEndpoint) forged =
        kr_hub_endpoint_new_device("http", "127.0.0.1", hub.port, DEVICE_ID, "guess", NULL);
    g_autoptr(KrHubClient) forger = kr_hub_client_new(forged, 5);
    Outcome refused = call(forger, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(refused.error, KR_HUB_ERROR, KR_HUB_ERROR_REFUSED);
    g_assert_cmpuint(refused.status, ==, 401);
    outcome_clear(&refused);

    /* An id that cannot be put in canonical form is not sent at all. */
    g_autoptr(KrHubEndpoint) broken =
        kr_hub_endpoint_new_device("http", "127.0.0.1", hub.port, "dev\n1", DEVICE_KEY, NULL);
    g_autoptr(KrHubClient) unsignable = kr_hub_client_new(broken, 5);
    guint before = hub.requests;
    Outcome unsent = call(unsignable, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(unsent.error, KR_HUB_ERROR, KR_HUB_ERROR_ENDPOINT);
    g_assert_cmpuint(hub.requests, ==, before);
    outcome_clear(&unsent);

    hub_stop(&hub);
}

typedef struct {
    KrDeviceCredential *credential;
    GError *error;
    gboolean done;
} Paired;

static void
on_paired(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Paired *paired = data;
    paired->credential = kr_pairing_claim_finish(result, &paired->error);
    paired->done = TRUE;
}

static Paired
claim(const KrHubEndpoint *target, const char *code, const char *path)
{
    Paired paired = {0};
    kr_pairing_claim_async(target, code, "krypton on test", path, NULL, on_paired, &paired);
    while (!paired.done)
        g_main_context_iteration(NULL, TRUE);
    return paired;
}

static void
paired_clear(Paired *paired)
{
    g_clear_pointer(&paired->credential, kr_device_credential_free);
    g_clear_error(&paired->error);
}

static char *
answer_for(const char *fingerprint)
{
    return g_strdup_printf("{\"device_id\": \"" DEVICE_ID "\", \"key\": \"" DEVICE_KEY "\", "
                           "\"scopes\": [\"read\"], \"fingerprint\": \"%s\"}",
                           fingerprint != NULL ? fingerprint : "");
}

static void
test_claim_switches_the_client(void)
{
    Hub hub = {0};
    hub_start(&hub);
    g_autofree char *answer = answer_for(NULL);
    hub.claim_body = answer;
    g_autofree char *dir = g_dir_make_tmp("krypton-claim-XXXXXX", NULL);
    g_autofree char *path = g_build_filename(dir, "krypton", "paired-hub.ini", NULL);

    g_autoptr(KrHubEndpoint) target = kr_pairing_target("127.0.0.1", hub.port, NULL, NULL);
    Paired paired = claim(target, "123456", path);
    g_assert_no_error(paired.error);
    g_assert_cmpstr(paired.credential->device_id, ==, DEVICE_ID);
    g_assert_cmpstr(paired.credential->key, ==, DEVICE_KEY);
    g_assert_cmpstr(paired.credential->name, ==, "krypton on test");
    g_assert_cmpstr(paired.credential->scheme, ==, "http");
    g_assert_cmpstrv(paired.credential->scopes, ((const char *const[]){"read", NULL}));

    /* The claim carried the code and the name, and no credential of any kind. */
    g_assert_cmpstr(hub.last_method, ==, "POST");
    g_assert_cmpstr(hub.last_path, ==, "/api/v1/pairing/claim");
    g_assert_cmpstr(hub.last_body, ==, "{\"code\":\"123456\",\"name\":\"krypton on test\"}");
    g_assert_null(hub.last_auth);
    g_assert_null(hub.last_device);

    /* The key was kept, owner-only, before success was reported. */
    GStatBuf info;
    g_assert_cmpint(g_stat(path, &info), ==, 0);
    g_assert_cmpint(info.st_mode & 0777, ==, 0600);

    /* What was kept is what the client now speaks as: signed requests the hub admits. */
    g_autoptr(GError) error = NULL;
    g_autoptr(KrDeviceCredential) kept = kr_device_credential_load(path, &error);
    g_assert_no_error(error);
    g_assert_true(kr_device_credential_matches(kept, "127.0.0.1", hub.port));
    g_autoptr(KrHubEndpoint) endpoint = kr_device_credential_endpoint(kept);
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 5);
    Outcome read = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_no_error(read.error);
    g_assert_cmpuint(read.status, ==, 200);
    g_assert_cmpstr(hub.last_device, ==, DEVICE_ID);
    outcome_clear(&read);
    paired_clear(&paired);

    /* A claim through a client that holds a key still sends none of it. */
    g_autofree char *body = kr_pairing_claim_body("654321", "again");
    Outcome again = call(client, KR_HUB_ROUTE_PAIRING_CLAIM, NULL, NULL, body);
    g_assert_no_error(again.error);
    g_assert_null(hub.last_auth);
    g_assert_null(hub.last_device);
    outcome_clear(&again);

    g_unlink(path);
    g_autofree char *parent = g_path_get_dirname(path);
    g_rmdir(parent);
    g_rmdir(dir);
    hub_stop(&hub);
}

static void
claim_refused(Hub *hub, guint status, const char *body, const char *says, const char *path)
{
    hub->claim_status = status;
    hub->claim_body = body;
    g_autoptr(KrHubEndpoint) target = kr_pairing_target("127.0.0.1", hub->port, NULL, NULL);
    Paired paired = claim(target, "123456", path);
    g_assert_null(paired.credential);
    g_assert_error(paired.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_REFUSED);
    if (strstr(paired.error->message, says) == NULL)
        g_error("\"%s\" does not say \"%s\"", paired.error->message, says);
    g_assert_false(g_file_test(path, G_FILE_TEST_EXISTS));
    paired_clear(&paired);
}

static void
test_claim_refusals(void)
{
    Hub hub = {0};
    hub_start(&hub);
    g_autofree char *dir = g_dir_make_tmp("krypton-refused-XXXXXX", NULL);
    g_autofree char *path = g_build_filename(dir, "paired-hub.ini", NULL);

    /* The hub's own refusals, as app.py and pairing.py word them. */
    claim_refused(&hub, 403, "{\"detail\": \"that code is not one this hub is offering\"}",
                  "wrong, already used, or more than two minutes old", path);
    claim_refused(&hub, 403, "{\"detail\": \"that code is not one this hub is offering\"}",
                  "(the hub said: that code is not one this hub is offering)", path);
    claim_refused(&hub, 503, "{\"detail\": \"pairing is not enabled on this hub\"}",
                  "Pairing is not enabled on this hub", path);
    claim_refused(&hub, 429, "{\"detail\": \"Too Many Requests\"}", "Too many pairing attempts",
                  path);
    claim_refused(&hub, 422, "{\"detail\": [{\"loc\": [\"body\", \"code\"]}]}",
                  "could not read that request", path);
    claim_refused(&hub, 421, "{\"detail\": \"this hub does not answer that Host\"}",
                  "[hub] names", path);
    claim_refused(&hub, 500, "not json", "(500)", path);
    claim_refused(&hub, 500, "[1]", "failed while answering", path);
    claim_refused(&hub, 500, NULL, "failed while answering", path);

    /* An answer that is not a pairing is not kept. */
    hub.claim_status = 200;
    hub.claim_body = "{}";
    g_autoptr(KrHubEndpoint) target = kr_pairing_target("127.0.0.1", hub.port, NULL, NULL);
    Paired odd = claim(target, "123456", path);
    g_assert_error(odd.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_RESPONSE);
    g_assert_false(g_file_test(path, G_FILE_TEST_EXISTS));
    paired_clear(&odd);

    /* A key that cannot be kept is not a pairing either. */
    g_autofree char *answer = answer_for(NULL);
    hub.claim_body = answer;
    g_autofree char *file = g_build_filename(dir, "a-file", NULL);
    g_assert_true(g_file_set_contents(file, "", 0, NULL));
    g_autofree char *beneath = g_build_filename(file, "paired-hub.ini", NULL);
    Paired unkept = claim(target, "123456", beneath);
    g_assert_error(unkept.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_STORE);
    paired_clear(&unkept);

    /* A code that is not six digits is never sent. */
    guint before = hub.requests;
    Paired short_code = claim(target, "12345", path);
    g_assert_error(short_code.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID);
    g_assert_cmpuint(hub.requests, ==, before);
    paired_clear(&short_code);

    g_unlink(file);
    g_rmdir(dir);
    hub_stop(&hub);
}

static void
test_claim_unreachable(void)
{
    g_autoptr(KrHubEndpoint) nowhere = kr_pairing_target("127.0.0.1", 1, NULL, NULL);
    Paired silent = claim(nowhere, "123456", "/nonexistent/paired-hub.ini");
    g_assert_error(silent.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_UNREACHABLE);
    g_assert_nonnull(strstr(silent.error->message, "No hub answers at 127.0.0.1:1"));
    paired_clear(&silent);

    g_autoptr(KrHubEndpoint) ftp = kr_hub_endpoint_new("ftp", "h", 1, NULL);
    Paired unusable = claim(ftp, "123456", "/nonexistent/paired-hub.ini");
    g_assert_error(unusable.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID);
    paired_clear(&unusable);
}

static void
test_pinned_but_plain(void)
{
    /* A pinned hub that answers without TLS has no certificate to match: refused. */
    Hub hub = {0};
    hub_start(&hub);
    g_autoptr(KrHubEndpoint) plain = kr_hub_endpoint_new_device(
        "http", "127.0.0.1", hub.port, DEVICE_ID, DEVICE_KEY, PINNED_ELSEWHERE);
    g_autoptr(KrHubClient) client = kr_hub_client_new(plain, 5);
    Outcome refused = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(refused.error, KR_HUB_ERROR, KR_HUB_ERROR_FINGERPRINT);
    outcome_clear(&refused);
    hub_stop(&hub);
}

/* ---- the certificate pin, over real TLS --------------------------------------------- */

#ifdef KR_TEST_CERT
static GTlsCertificate *
test_certificate(void)
{
    if (!g_tls_backend_supports_tls(g_tls_backend_get_default())) {
        g_test_skip("GIO has no TLS backend here (glib-networking is not installed)");
        return NULL;
    }
    g_autoptr(GError) error = NULL;
    GTlsCertificate *certificate =
        g_tls_certificate_new_from_files(KR_TEST_CERT, KR_TEST_KEY, &error);
    g_assert_no_error(error);
    return certificate;
}

/* openssl's "SHA256 Fingerprint=AB:CD:..." as lowercase hex. */
static char *
openssl_fingerprint(void)
{
    g_autofree char *text = NULL;
    g_assert_true(g_file_get_contents(KR_TEST_FINGERPRINT, &text, NULL, NULL));
    const char *value = strchr(text, '=');
    g_assert_nonnull(value);
    GString *hex = g_string_new(NULL);
    for (const char *c = value + 1; *c != '\0'; c++) {
        if (g_ascii_isxdigit(*c))
            g_string_append_c(hex, g_ascii_tolower(*c));
    }
    return g_string_free(hex, FALSE);
}

static void
test_fingerprint(void)
{
    g_autoptr(GTlsCertificate) certificate = test_certificate();
    if (certificate == NULL)
        return;
    g_autofree char *ours = kr_hub_certificate_fingerprint(certificate);
    g_autofree char *theirs = openssl_fingerprint();
    g_assert_cmpstr(ours, ==, theirs);
}

static void
test_pinned_pairing(void)
{
    g_autoptr(GTlsCertificate) certificate = test_certificate();
    if (certificate == NULL)
        return;
    Hub hub = {0};
    hub_listen(&hub, certificate);
    hub.fingerprint = kr_hub_certificate_fingerprint(certificate);
    g_autofree char *answer = answer_for(hub.fingerprint);
    hub.claim_body = answer;
    g_autofree char *dir = g_dir_make_tmp("krypton-pinned-XXXXXX", NULL);
    g_autofree char *path = g_build_filename(dir, "paired-hub.ini", NULL);

    /* The certificate the pairing code names: the claim goes through, and is kept pinned. */
    g_autoptr(KrHubEndpoint) target =
        kr_pairing_target("127.0.0.1", hub.port, hub.fingerprint, NULL);
    Paired paired = claim(target, "123456", path);
    g_assert_no_error(paired.error);
    g_assert_cmpstr(paired.credential->scheme, ==, "https");
    g_assert_cmpstr(paired.credential->fingerprint, ==, hub.fingerprint);

    g_autoptr(KrHubEndpoint) endpoint = kr_device_credential_endpoint(paired.credential);
    g_autoptr(KrHubClient) client = kr_hub_client_new(endpoint, 5);
    Outcome read = call(client, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_no_error(read.error);
    g_assert_cmpuint(read.status, ==, 200);
    outcome_clear(&read);
    paired_clear(&paired);
    g_unlink(path);

    /* Any other certificate on that address: refused before the code is sent. */
    guint before = hub.requests;
    g_autoptr(KrHubEndpoint) impostor =
        kr_pairing_target("127.0.0.1", hub.port, PINNED_ELSEWHERE, NULL);
    Paired refused = claim(impostor, "123456", path);
    g_assert_null(refused.credential);
    g_assert_error(refused.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_FINGERPRINT);
    g_assert_nonnull(strstr(refused.error->message, hub.fingerprint));
    g_assert_cmpuint(hub.requests, ==, before);
    g_assert_false(g_file_test(path, G_FILE_TEST_EXISTS));
    paired_clear(&refused);

    /* And so is a paired device's request. */
    g_autoptr(KrHubEndpoint) misplaced = kr_hub_endpoint_new_device(
        "https", "127.0.0.1", hub.port, DEVICE_ID, DEVICE_KEY, PINNED_ELSEWHERE);
    g_autoptr(KrHubClient) wary = kr_hub_client_new(misplaced, 5);
    Outcome unsent = call(wary, KR_HUB_ROUTE_PROJECTS, NULL, NULL, NULL);
    g_assert_error(unsent.error, KR_HUB_ERROR, KR_HUB_ERROR_FINGERPRINT);
    g_assert_cmpuint(hub.requests, ==, before);
    outcome_clear(&unsent);

    /* A claim answer that names another certificate than the one pinned is refused. */
    g_autofree char *contradicting = answer_for(PINNED_ELSEWHERE);
    hub.claim_body = contradicting;
    Paired contradicted = claim(target, "123456", path);
    g_assert_error(contradicted.error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_RESPONSE);
    paired_clear(&contradicted);

    g_rmdir(dir);
    hub_stop(&hub);
}
#endif

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/hub-client/reads-with-the-token", test_reads_with_the_token);
    g_test_add_func("/hub-client/writes-and-refusals", test_writes_and_refusals);
    g_test_add_func("/hub-client/bad-endpoints", test_bad_endpoints);
    g_test_add_func("/hub-client/signed-requests", test_signed_requests);
    g_test_add_func("/hub-client/claim-switches-the-client", test_claim_switches_the_client);
    g_test_add_func("/hub-client/claim-refusals", test_claim_refusals);
    g_test_add_func("/hub-client/claim-unreachable", test_claim_unreachable);
    g_test_add_func("/hub-client/pinned-but-plain", test_pinned_but_plain);
#ifdef KR_TEST_CERT
    g_test_add_func("/hub-client/fingerprint", test_fingerprint);
    g_test_add_func("/hub-client/pinned-pairing", test_pinned_pairing);
#endif
    return g_test_run();
}
