/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include <glib/gstdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "kr-pairing.h"

#define FP "0123456789ABCDEF0123456789abcdef0123456789abcdef0123456789abcdef"
#define FP_LOWER "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

static void
test_code(void)
{
    g_assert_true(kr_pairing_code_valid("123456"));
    g_assert_false(kr_pairing_code_valid("12345"));
    g_assert_false(kr_pairing_code_valid("1234567"));
    g_assert_false(kr_pairing_code_valid("12a456"));
    g_assert_false(kr_pairing_code_valid(NULL));

    g_autofree char *spaced = kr_pairing_code_normalise("123 456");
    g_assert_cmpstr(spaced, ==, "123456");
    g_autofree char *dashed = kr_pairing_code_normalise("12-34-56");
    g_assert_cmpstr(dashed, ==, "123456");
    g_assert_null(kr_pairing_code_normalise("123 45"));
    g_assert_null(kr_pairing_code_normalise(NULL));

    g_assert_true(kr_pairing_fingerprint_valid(FP));
    g_assert_false(kr_pairing_fingerprint_valid("abc"));
    g_assert_false(kr_pairing_fingerprint_valid(NULL));
}

static void
test_offer(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrPairingOffer) offer =
        kr_pairing_offer_parse("vibey-pair://studio.local:8765?code=123456&fp=" FP, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(offer->host, ==, "studio.local");
    g_assert_cmpuint(offer->port, ==, 8765);
    g_assert_cmpstr(offer->code, ==, "123456");
    g_assert_cmpstr(offer->fingerprint, ==, FP_LOWER);
    kr_pairing_offer_free(NULL);

    /* The URI exactly as the hub writes it (HubPairingPolicy.uri): fp first, then v=1. */
    g_autoptr(KrPairingOffer) hubs = kr_pairing_offer_parse(
        "  vibey-pair://192.168.1.20:8765?fp=" FP_LOWER "&code=000042&v=1\n", &error);
    g_assert_no_error(error);
    g_assert_cmpstr(hubs->host, ==, "192.168.1.20");
    g_assert_cmpstr(hubs->code, ==, "000042");

    /* A hub on loopback serves no TLS, so it has no fingerprint to give. */
    g_autoptr(KrPairingOffer) loopback =
        kr_pairing_offer_parse("vibey-pair://127.0.0.1:8765?fp=&code=123456&v=1", &error);
    g_assert_no_error(error);
    g_assert_null(loopback->fingerprint);
    g_autoptr(KrPairingOffer) v6 =
        kr_pairing_offer_parse("vibey-pair://[::1]:8765?code=123456", &error);
    g_assert_no_error(error);
    g_assert_cmpstr(v6->host, ==, "::1");
    g_assert_null(v6->fingerprint);
}

static void
refused(const char *uri)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrPairingOffer) offer = kr_pairing_offer_parse(uri, &error);
    g_assert_null(offer);
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID);
}

static void
test_refusals(void)
{
    refused(NULL);
    refused("not a uri");
    refused("https://studio.local:8765?code=123456&fp=" FP);
    refused("vibey-pair://:8765?code=123456&fp=" FP);
    refused("vibey-pair://studio.local?code=123456&fp=" FP);
    refused("vibey-pair://studio.local:8765");
    refused("vibey-pair://studio.local:8765?code=12345&fp=" FP);
    refused("vibey-pair://studio.local:8765?code=123456&fp=abc");
    refused("vibey-pair://studio.local:8765?code=123456&fp="
            "zz23456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef");
    /* A hub elsewhere must name its certificate; a newer hub's format is not guessed at. */
    refused("vibey-pair://studio.local:8765?code=123456");
    refused("vibey-pair://studio.local:8765?code=123456&fp=");
    refused("vibey-pair://studio.local:8765?code=123456&fp=" FP "&v=2");
}

static void
test_display(void)
{
    g_autofree char *grouped = kr_pairing_fingerprint_display("ABCD1234ef");
    g_assert_cmpstr(grouped, ==, "abcd 1234 ef");
    g_autofree char *none = kr_pairing_fingerprint_display(NULL);
    g_assert_cmpstr(none, ==, "");
}

static void
test_target(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrHubEndpoint) pinned = kr_pairing_target("studio.local", 8765, FP, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(pinned->scheme, ==, "https");
    g_assert_cmpstr(pinned->fingerprint, ==, FP_LOWER);
    g_assert_null(pinned->token);
    g_assert_null(pinned->device_id);

    g_autoptr(KrHubEndpoint) local = kr_pairing_target("127.0.0.1", 0, NULL, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(local->scheme, ==, "http");
    g_assert_cmpuint(local->port, ==, KR_HUB_DEFAULT_PORT);
    g_assert_null(local->fingerprint);

    g_assert_null(kr_pairing_target("studio.local", 8765, NULL, &error));
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_UNPINNED);
    g_assert_nonnull(strstr(error->message, "vibey-pair://"));
    g_clear_error(&error);
    g_assert_null(kr_pairing_target("studio.local", 8765, "abc", &error));
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID);
    g_clear_error(&error);
    g_assert_null(kr_pairing_target(NULL, 8765, FP, &error));
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID);
    g_clear_error(&error);
    g_assert_null(kr_pairing_target("", 8765, FP, &error));
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID);
}

static void
test_name_and_body(void)
{
    g_autofree char *name = kr_pairing_device_name("studio");
    g_assert_cmpstr(name, ==, "krypton on studio");
    g_autofree char *nameless = kr_pairing_device_name(NULL);
    g_assert_cmpstr(nameless, ==, "krypton on this computer");
    g_autofree char *empty = kr_pairing_device_name("");
    g_assert_cmpstr(empty, ==, "krypton on this computer");
    g_autofree char *odd = kr_pairing_device_name("a\tb\x01"
                                                  "c");
    g_assert_cmpstr(odd, ==, "krypton on abc");
    g_autofree char *long_host = g_strnfill(200, 'x');
    g_autofree char *capped = kr_pairing_device_name(long_host);
    g_assert_cmpuint(strlen(capped), ==, KR_PAIRING_NAME_MAX);

    g_autofree char *body = kr_pairing_claim_body("123456", "krypton on \"q\"");
    g_assert_cmpstr(body, ==, "{\"code\":\"123456\",\"name\":\"krypton on \\\"q\\\"\"}");
}

static void
test_refusal_messages(void)
{
    g_autofree char *wrong =
        kr_pairing_refusal_message(403, "that code is not one this hub is offering");
    g_assert_nonnull(strstr(wrong, "wrong, already used"));
    g_assert_nonnull(strstr(wrong, "(the hub said: that code is not one this hub is offering)"));
    g_autofree char *off = kr_pairing_refusal_message(503, "pairing is not enabled on this hub");
    g_assert_true(g_str_has_prefix(off, "Pairing is not enabled on this hub"));
    g_autofree char *busy = kr_pairing_refusal_message(429, NULL);
    g_assert_nonnull(strstr(busy, "Too many pairing attempts"));
    g_assert_null(strstr(busy, "the hub said"));
    g_autofree char *other = kr_pairing_refusal_message(421, "");
    g_assert_nonnull(strstr(other, "(421)"));
    g_assert_nonnull(strstr(other, "[hub] names"));
}

/* ---- the key ------------------------------------------------------------------------- */

#define ANSWER                                                                                     \
    "{\"device_id\": \"d1\", \"key\": \"k3y\", \"scopes\": [\"answer\", \"read\", 7], "            \
    "\"fingerprint\": \"" FP "\"}"

static KrDeviceCredential *
claimed(const KrHubEndpoint *target, const char *json, GError **error)
{
    return kr_device_credential_from_claim(target, "krypton on studio", json, -1, error);
}

static void
not_a_pairing(const KrHubEndpoint *target, const char *json)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrDeviceCredential) credential = claimed(target, json, &error);
    g_assert_null(credential);
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_RESPONSE);
}

static void
test_scope_descriptions(void)
{
    g_assert_cmpstr(kr_pairing_scope_description("workflows"), ==,
                    "Run vibey commands on the repository's GitHub-hosted runners");
    for (const char *const *scope = (const char *const[]){"view", "answer", "spend", "run",
                                                          "bump", NULL};
         *scope != NULL; scope++)
        g_assert_nonnull(kr_pairing_scope_description(*scope));
    g_assert_null(kr_pairing_scope_description("admin"));
    g_assert_null(kr_pairing_scope_description(NULL));

    g_autofree char *said =
        kr_pairing_scopes_said((const char *const[]){"view", "workflows", "admin", NULL});
    g_assert_cmpstr(said, ==,
                    "view: See projects, status, gates, budgets, the queue, loops, lanes and "
                    "doctor\n"
                    "workflows: Run vibey commands on the repository's GitHub-hosted runners\n"
                    "admin");
    g_autofree char *none = kr_pairing_scopes_said((const char *const[]){NULL});
    g_assert_cmpstr(none, ==, "nothing yet");
    g_autofree char *missing = kr_pairing_scopes_said(NULL);
    g_assert_cmpstr(missing, ==, "nothing yet");
}

static void
test_from_claim(void)
{
    g_autoptr(KrHubEndpoint) target = kr_pairing_target("studio.local", 8765, FP, NULL);
    g_autoptr(GError) error = NULL;
    g_autoptr(KrDeviceCredential) credential = claimed(target, ANSWER, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(credential->scheme, ==, "https");
    g_assert_cmpstr(credential->host, ==, "studio.local");
    g_assert_cmpuint(credential->port, ==, 8765);
    g_assert_cmpstr(credential->fingerprint, ==, FP_LOWER);
    g_assert_cmpstr(credential->device_id, ==, "d1");
    g_assert_cmpstr(credential->key, ==, "k3y");
    g_assert_cmpstr(credential->name, ==, "krypton on studio");
    g_assert_cmpuint(g_strv_length(credential->scopes), ==, 2);
    g_assert_cmpstr(credential->scopes[0], ==, "answer");

    g_autoptr(KrHubEndpoint) endpoint = kr_device_credential_endpoint(credential);
    g_assert_cmpstr(endpoint->device_id, ==, "d1");
    g_assert_cmpstr(endpoint->token, ==, "k3y");
    g_assert_cmpstr(endpoint->fingerprint, ==, FP_LOWER);
    g_assert_true(kr_device_credential_matches(credential, "STUDIO.local", 8765));
    g_assert_false(kr_device_credential_matches(credential, "studio.local", 9000));
    g_assert_false(kr_device_credential_matches(credential, NULL, 8765));
    g_assert_false(kr_device_credential_matches(credential, "other", 8765));

    /* A loopback hub answers with an empty fingerprint and nothing is pinned. */
    g_autoptr(KrHubEndpoint) local = kr_pairing_target("127.0.0.1", 0, NULL, NULL);
    g_autoptr(KrDeviceCredential) plain =
        claimed(local, "{\"device_id\": \"d2\", \"key\": \"k\", \"fingerprint\": \"\"}", &error);
    g_assert_no_error(error);
    g_assert_null(plain->fingerprint);
    g_assert_cmpuint(g_strv_length(plain->scopes), ==, 0);
    g_assert_true(kr_device_credential_matches(plain, "127.0.0.1", 0));

    not_a_pairing(target, NULL);
    not_a_pairing(target, "nope");
    not_a_pairing(target, "[]");
    not_a_pairing(target, "{\"key\": \"k\", \"fingerprint\": \"" FP "\"}");
    not_a_pairing(target, "{\"device_id\": \"d\", \"key\": \"\", \"fingerprint\": \"" FP "\"}");
    not_a_pairing(target, "{\"device_id\": 1, \"key\": \"k\"}");
    not_a_pairing(target, "{\"device_id\": \"d\", \"key\": \"k\"}");
    not_a_pairing(target, "{\"device_id\": \"d\", \"key\": \"k\", \"fingerprint\": \"ff\"}");
    kr_device_credential_free(NULL);
}

static char *
put(const char *dir, const char *name, const char *content, int mode)
{
    char *path = g_build_filename(dir, name, NULL);
    g_assert_true(g_file_set_contents(path, content, -1, NULL));
    g_assert_cmpint(g_chmod(path, mode), ==, 0);
    return path;
}

static void
kept_refused(const char *path)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrDeviceCredential) credential = kr_device_credential_load(path, &error);
    g_assert_null(credential);
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_STORE);
}

#define KEPT(hub) "[hub]\n" hub "\n[device]\nid=d1\nkey=k3y\nname=krypton\n"

static void
test_store(void)
{
    g_autofree char *dir = g_dir_make_tmp("krypton-pairing-XXXXXX", NULL);
    g_autofree char *settings = g_build_filename(dir, "krypton", "settings.ini", NULL);
    g_autofree char *path = kr_device_credential_path(settings);
    g_assert_true(g_str_has_suffix(path, "/krypton/paired-hub.ini"));

    g_autoptr(KrHubEndpoint) target = kr_pairing_target("studio.local", 8765, FP, NULL);
    g_autoptr(KrDeviceCredential) credential = claimed(target, ANSWER, NULL);
    g_autoptr(GError) error = NULL;
    g_assert_true(kr_device_credential_save(credential, path, &error));
    g_assert_no_error(error);

    /* Owner-only, in an owner-only directory: the way the hub keeps its own keys. */
    GStatBuf info;
    g_assert_cmpint(g_stat(path, &info), ==, 0);
    g_assert_cmpint(info.st_mode & 0777, ==, 0600);
    g_autofree char *parent = g_path_get_dirname(path);
    g_assert_cmpint(g_stat(parent, &info), ==, 0);
    g_assert_cmpint(info.st_mode & 0777, ==, 0700);

    g_autoptr(KrDeviceCredential) kept = kr_device_credential_load(path, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(kept->scheme, ==, "https");
    g_assert_cmpstr(kept->host, ==, "studio.local");
    g_assert_cmpuint(kept->port, ==, 8765);
    g_assert_cmpstr(kept->fingerprint, ==, FP_LOWER);
    g_assert_cmpstr(kept->device_id, ==, "d1");
    g_assert_cmpstr(kept->key, ==, "k3y");
    g_assert_cmpstr(kept->name, ==, "krypton on studio");
    g_assert_cmpstrv(kept->scopes, ((const char *const[]){"answer", "read", NULL}));

    /* Saving again replaces it, still owner-only. */
    g_assert_true(kr_device_credential_save(credential, path, NULL));

    /* A loopback pairing keeps no fingerprint, and an absent scope list reads as none. */
    g_autofree char *local =
        put(dir, "local.ini", KEPT("scheme=http\nhost=127.0.0.1\nport=8765"), 0600);
    g_autoptr(KrDeviceCredential) plain = kr_device_credential_load(local, &error);
    g_assert_no_error(error);
    g_assert_null(plain->fingerprint);
    g_assert_cmpuint(g_strv_length(plain->scopes), ==, 0);

    g_autofree char *missing = g_build_filename(dir, "missing.ini", NULL);
    g_autoptr(KrDeviceCredential) none = kr_device_credential_load(missing, &error);
    g_assert_null(none);
    g_assert_error(error, G_FILE_ERROR, G_FILE_ERROR_NOENT);
    g_clear_error(&error);

    g_autofree char *link = g_build_filename(dir, "link.ini", NULL);
    g_assert_cmpint(symlink(path, link), ==, 0);
    kept_refused(link);
    kept_refused(dir);
    g_autofree char *shared = put(dir, "shared.ini", "[hub]\n", 0640);
    kept_refused(shared);
    g_autofree char *huge_text = g_strnfill(20000, '#');
    g_autofree char *huge = put(dir, "huge.ini", huge_text, 0600);
    kept_refused(huge);
    g_autofree char *garbage = put(dir, "garbage.ini", "not = [a key file", 0600);
    kept_refused(garbage);
    g_autofree char *partial = put(dir, "partial.ini", "[hub]\nscheme=https\n", 0600);
    kept_refused(partial);
    g_autofree char *ftp =
        put(dir, "ftp.ini", KEPT("scheme=ftp\nhost=h\nport=1\nfingerprint=" FP), 0600);
    kept_refused(ftp);
    g_autofree char *port =
        put(dir, "port.ini", KEPT("scheme=https\nhost=h\nport=70000\nfingerprint=" FP), 0600);
    kept_refused(port);
    g_autofree char *unpinned = put(dir, "unpinned.ini", KEPT("scheme=https\nhost=h\nport=1"), 0600);
    kept_refused(unpinned);
    g_autofree char *remote =
        put(dir, "remote.ini", KEPT("scheme=http\nhost=studio.local\nport=1"), 0600);
    kept_refused(remote);
    g_autofree char *plain_pin = put(
        dir, "plain-pin.ini", KEPT("scheme=http\nhost=127.0.0.1\nport=1\nfingerprint=" FP), 0600);
    kept_refused(plain_pin);

    /* Nowhere to keep it: the directory it would go in is a file. */
    g_autofree char *blocked = g_build_filename(shared, "paired-hub.ini", NULL);
    g_assert_false(kr_device_credential_save(credential, blocked, &error));
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_STORE);
    g_clear_error(&error);
    /* A directory where the file would go cannot be replaced by it. */
    g_autofree char *occupied_dir = g_build_filename(dir, "occupied", NULL);
    g_autofree char *occupied = g_build_filename(occupied_dir, "paired-hub.ini", NULL);
    g_assert_cmpint(g_mkdir_with_parents(occupied, 0700), ==, 0);
    g_assert_false(kr_device_credential_save(credential, occupied, &error));
    g_assert_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_STORE);

    g_rmdir(occupied);
    g_rmdir(occupied_dir);
    for (const char *const *name =
             (const char *const[]){"link.ini", "shared.ini", "huge.ini", "garbage.ini",
                                   "partial.ini", "ftp.ini", "port.ini", "unpinned.ini",
                                   "remote.ini", "plain-pin.ini", "local.ini", NULL};
         *name != NULL; name++) {
        g_autofree char *file = g_build_filename(dir, *name, NULL);
        g_unlink(file);
    }
    g_unlink(path);
    g_rmdir(parent);
    g_rmdir(dir);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/pairing/code", test_code);
    g_test_add_func("/pairing/offer", test_offer);
    g_test_add_func("/pairing/refusals", test_refusals);
    g_test_add_func("/pairing/display", test_display);
    g_test_add_func("/pairing/target", test_target);
    g_test_add_func("/pairing/name-and-body", test_name_and_body);
    g_test_add_func("/pairing/refusal-messages", test_refusal_messages);
    g_test_add_func("/pairing/scope-descriptions", test_scope_descriptions);
    g_test_add_func("/pairing/from-claim", test_from_claim);
    g_test_add_func("/pairing/store", test_store);
    return g_test_run();
}
