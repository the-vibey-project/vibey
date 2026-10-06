/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-pairing.h"

#include <errno.h>
#include <fcntl.h>
#include <glib/gstdio.h>
#include <json-glib/json-glib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

G_DEFINE_QUARK(kr-pairing-error-quark, kr_pairing_error)

/* The most a kept credential may hold: a few hundred bytes in practice. */
#define CREDENTIAL_MAX 16384
#define CREDENTIAL_FILE "paired-hub.ini"
#define GROUP_HUB "hub"
#define GROUP_DEVICE "device"

/* Overwrites a secret before its memory is released (as kr-hub.c does for the token). */
static void
wipe(void *memory, size_t size)
{
    volatile unsigned char *byte = memory;
    while (size-- > 0)
        *byte++ = 0;
}

gboolean
kr_pairing_code_valid(const char *code)
{
    if (code == NULL || strlen(code) != KR_PAIRING_CODE_LENGTH)
        return FALSE;
    for (size_t i = 0; i < KR_PAIRING_CODE_LENGTH; i++) {
        if (!g_ascii_isdigit(code[i]))
            return FALSE;
    }
    return TRUE;
}

char *
kr_pairing_code_normalise(const char *typed)
{
    if (typed == NULL)
        return NULL;
    GString *kept = g_string_new(NULL);
    for (const char *c = typed; *c != '\0'; c++) {
        if (*c != ' ' && *c != '-')
            g_string_append_c(kept, *c);
    }
    char *code = g_string_free(kept, FALSE);
    if (!kr_pairing_code_valid(code)) {
        g_free(code);
        return NULL;
    }
    return code;
}

gboolean
kr_pairing_fingerprint_valid(const char *fingerprint)
{
    if (fingerprint == NULL || strlen(fingerprint) != KR_PAIRING_FINGERPRINT_LENGTH)
        return FALSE;
    for (size_t i = 0; i < KR_PAIRING_FINGERPRINT_LENGTH; i++) {
        if (!g_ascii_isxdigit(fingerprint[i]))
            return FALSE;
    }
    return TRUE;
}

void
kr_pairing_offer_free(KrPairingOffer *offer)
{
    if (offer == NULL)
        return;
    g_free(offer->host);
    g_free(offer->code);
    g_free(offer->fingerprint);
    g_free(offer);
}

static KrPairingOffer *
refuse(GError **error, const char *why)
{
    g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID, "not a krypton pairing code: %s",
                why);
    return NULL;
}

KrPairingOffer *
kr_pairing_offer_parse(const char *uri, GError **error)
{
    if (uri == NULL)
        return refuse(error, "nothing was read");
    g_autofree char *trimmed = g_strstrip(g_strdup(uri));
    g_autoptr(GUri) parsed = g_uri_parse(trimmed, G_URI_FLAGS_NONE, NULL);
    if (parsed == NULL || g_strcmp0(g_uri_get_scheme(parsed), KR_PAIRING_SCHEME) != 0)
        return refuse(error, "it is not a " KR_PAIRING_SCHEME ":// address");
    const char *host = g_uri_get_host(parsed);
    if (host == NULL || *host == '\0')
        return refuse(error, "it names no hub");
    gint port = g_uri_get_port(parsed);
    if (port <= 0 || port > 65535)
        return refuse(error, "it names no port");

    const char *query = g_uri_get_query(parsed);
    g_autoptr(GHashTable) params = query != NULL
                                       ? g_uri_parse_params(query, -1, "&", G_URI_PARAMS_NONE,
                                                            NULL)
                                       : NULL;
    const char *code = params ? g_hash_table_lookup(params, "code") : NULL;
    const char *fingerprint = params ? g_hash_table_lookup(params, "fp") : NULL;
    const char *version = params ? g_hash_table_lookup(params, "v") : NULL;
    if (version != NULL && !g_str_equal(version, "1"))
        return refuse(error, "it was made by a hub newer than this krypton");
    if (!kr_pairing_code_valid(code))
        return refuse(error, "its code is not six digits");
    gboolean unpinned = fingerprint == NULL || *fingerprint == '\0';
    if (unpinned && !kr_hub_host_is_loopback(host))
        return refuse(error, "it carries no certificate fingerprint for a hub on another computer");
    if (!unpinned && !kr_pairing_fingerprint_valid(fingerprint))
        return refuse(error, "its certificate fingerprint is not a SHA-256");

    KrPairingOffer *offer = g_new0(KrPairingOffer, 1);
    offer->host = g_strdup(host);
    offer->port = (guint16) port;
    offer->code = g_strdup(code);
    offer->fingerprint = unpinned ? NULL : g_ascii_strdown(fingerprint, -1);
    return offer;
}

char *
kr_pairing_fingerprint_display(const char *fingerprint)
{
    GString *out = g_string_new(NULL);
    for (size_t i = 0; fingerprint != NULL && fingerprint[i] != '\0'; i++) {
        if (i > 0 && i % 4 == 0)
            g_string_append_c(out, ' ');
        g_string_append_c(out, g_ascii_tolower(fingerprint[i]));
    }
    return g_string_free(out, FALSE);
}

KrHubEndpoint *
kr_pairing_target(const char *host, guint16 port, const char *fingerprint, GError **error)
{
    if (host == NULL || *host == '\0') {
        g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID, "no hub was chosen");
        return NULL;
    }
    if (fingerprint != NULL) {
        if (!kr_pairing_fingerprint_valid(fingerprint)) {
            g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_INVALID,
                        "the hub's certificate fingerprint is not a SHA-256");
            return NULL;
        }
        return kr_hub_endpoint_new_device("https", host, port, NULL, NULL, fingerprint);
    }
    if (!kr_hub_host_is_loopback(host)) {
        g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_UNPINNED,
                    "krypton cannot tell %s's certificate from anyone else's. Paste the "
                    "vibey-pair:// address the host shows beside its code: it carries the "
                    "fingerprint.",
                    host);
        return NULL;
    }
    return kr_hub_endpoint_new("http", host, port, NULL);
}

char *
kr_pairing_device_name(const char *host_name)
{
    GString *name = g_string_new("krypton on ");
    const char *from = host_name != NULL && *host_name != '\0' ? host_name : "this computer";
    for (const char *c = from; *c != '\0' && name->len < KR_PAIRING_NAME_MAX; c++) {
        if (g_ascii_isprint(*c))
            g_string_append_c(name, *c);
    }
    return g_string_free(name, FALSE);
}

char *
kr_pairing_claim_body(const char *code, const char *name)
{
    g_autoptr(JsonBuilder) builder = json_builder_new();
    json_builder_begin_object(builder);
    json_builder_set_member_name(builder, "code");
    json_builder_add_string_value(builder, code);
    json_builder_set_member_name(builder, "name");
    json_builder_add_string_value(builder, name);
    json_builder_end_object(builder);
    g_autoptr(JsonNode) root = json_builder_get_root(builder);
    return json_to_string(root, FALSE);
}

char *
kr_pairing_refusal_message(guint status, const char *detail)
{
    g_autofree char *said = detail != NULL && *detail != '\0'
                                ? g_strdup_printf(" (the hub said: %s)", detail)
                                : g_strdup("");
    switch (status) {
    case 403:
        return g_strdup_printf("The hub refused that code: it is wrong, already used, or more "
                               "than two minutes old. Ask the host for a new one "
                               "(vibey hub pair)%s.",
                               said);
    case 429:
        return g_strdup_printf("Too many pairing attempts from this computer. Wait a minute, "
                               "then try a fresh code%s.",
                               said);
    case 503:
        return g_strdup_printf("Pairing is not enabled on this hub%s.", said);
    default:
        return g_strdup_printf("The hub refused to pair (%u): %s%s", status,
                               kr_hub_status_text(status), said);
    }
}

const char *
kr_pairing_scope_description(const char *scope)
{
    static const struct {
        const char *scope;
        const char *description;
    } SCOPES[] = {
        {"view", "See projects, status, gates, budgets, the queue, loops, lanes and doctor"},
        {"answer", "Answer a gate that is not a spending decision"},
        {"spend", "Answer a gate whose answer spends money"},
        {"run", "Start, stop or wind down work"},
        {"bump", "Move a queued job to the front of its project's queue"},
        {"workflows", "Run vibey commands on the repository's GitHub-hosted runners"},
    };
    for (size_t i = 0; scope != NULL && i < G_N_ELEMENTS(SCOPES); i++) {
        if (g_str_equal(scope, SCOPES[i].scope))
            return SCOPES[i].description;
    }
    return NULL;
}

char *
kr_pairing_scopes_said(const char *const *scopes)
{
    if (scopes == NULL || scopes[0] == NULL)
        return g_strdup("nothing yet");
    GString *said = g_string_new(NULL);
    for (const char *const *scope = scopes; *scope != NULL; scope++) {
        const char *description = kr_pairing_scope_description(*scope);
        g_string_append_printf(said, "%s%s%s%s", said->len > 0 ? "\n" : "", *scope,
                               description != NULL ? ": " : "",
                               description != NULL ? description : "");
    }
    return g_string_free(said, FALSE);
}

/* ---- the key a pairing gives ---------------------------------------------------------- */

void
kr_device_credential_free(KrDeviceCredential *credential)
{
    if (credential == NULL)
        return;
    g_free(credential->scheme);
    g_free(credential->host);
    g_free(credential->fingerprint);
    g_free(credential->device_id);
    if (credential->key != NULL)
        wipe(credential->key, strlen(credential->key));
    g_free(credential->key);
    g_free(credential->name);
    g_strfreev(credential->scopes);
    g_free(credential);
}

static KrDeviceCredential *
response_refused(GError **error, const char *why)
{
    g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_RESPONSE,
                "the hub's answer is not a pairing: %s", why);
    return NULL;
}

static const char *
member_string(JsonObject *object, const char *name)
{
    JsonNode *node = json_object_get_member(object, name);
    if (node == NULL || json_node_get_value_type(node) != G_TYPE_STRING)
        return NULL;
    return json_node_get_string(node);
}

static gboolean
filled(const char *text)
{
    return text != NULL && *text != '\0';
}

KrDeviceCredential *
kr_device_credential_from_claim(const KrHubEndpoint *target, const char *name, const char *json,
                                gssize length, GError **error)
{
    g_autoptr(JsonParser) parser = json_parser_new();
    if (json == NULL || !json_parser_load_from_data(parser, json, length, NULL))
        return response_refused(error, "it is not JSON");
    JsonNode *root = json_parser_get_root(parser);
    if (!JSON_NODE_HOLDS_OBJECT(root))
        return response_refused(error, "it is not an object");
    JsonObject *object = json_node_get_object(root);
    const char *device_id = member_string(object, "device_id");
    const char *key = member_string(object, "key");
    const char *fingerprint = member_string(object, "fingerprint");
    if (!filled(device_id) || !filled(key))
        return response_refused(error, "it carries no device id and key");
    if (target->fingerprint != NULL &&
        (fingerprint == NULL || g_ascii_strcasecmp(fingerprint, target->fingerprint) != 0))
        return response_refused(error, "it names a certificate other than the pinned one");

    GPtrArray *scopes = g_ptr_array_new();
    JsonNode *listed = json_object_get_member(object, "scopes");
    if (listed != NULL && JSON_NODE_HOLDS_ARRAY(listed)) {
        JsonArray *array = json_node_get_array(listed);
        for (guint i = 0; i < json_array_get_length(array); i++) {
            JsonNode *scope = json_array_get_element(array, i);
            if (json_node_get_value_type(scope) == G_TYPE_STRING)
                g_ptr_array_add(scopes, g_strdup(json_node_get_string(scope)));
        }
    }
    g_ptr_array_add(scopes, NULL);

    KrDeviceCredential *credential = g_new0(KrDeviceCredential, 1);
    credential->scheme = g_strdup(target->scheme);
    credential->host = g_strdup(target->host);
    credential->port = target->port;
    credential->fingerprint = g_strdup(target->fingerprint);
    credential->device_id = g_strdup(device_id);
    credential->key = g_strdup(key);
    credential->name = g_strdup(name);
    credential->scopes = (char **) g_ptr_array_free(scopes, FALSE);
    return credential;
}

KrHubEndpoint *
kr_device_credential_endpoint(const KrDeviceCredential *credential)
{
    return kr_hub_endpoint_new_device(credential->scheme, credential->host, credential->port,
                                      credential->device_id, credential->key,
                                      credential->fingerprint);
}

gboolean
kr_device_credential_matches(const KrDeviceCredential *credential, const char *host,
                             guint16 port)
{
    guint16 wanted = port != 0 ? port : KR_HUB_DEFAULT_PORT;
    return host != NULL && g_ascii_strcasecmp(credential->host, host) == 0 &&
           credential->port == wanted;
}

char *
kr_device_credential_path(const char *settings_path)
{
    g_autofree char *directory = g_path_get_dirname(settings_path);
    return g_build_filename(directory, CREDENTIAL_FILE, NULL);
}

gboolean
kr_device_credential_save(const KrDeviceCredential *credential, const char *path,
                          GError **error)
{
    g_autoptr(GKeyFile) file = g_key_file_new();
    g_key_file_set_string(file, GROUP_HUB, "scheme", credential->scheme);
    g_key_file_set_string(file, GROUP_HUB, "host", credential->host);
    g_key_file_set_integer(file, GROUP_HUB, "port", credential->port);
    if (credential->fingerprint != NULL)
        g_key_file_set_string(file, GROUP_HUB, "fingerprint", credential->fingerprint);
    g_key_file_set_string(file, GROUP_DEVICE, "id", credential->device_id);
    g_key_file_set_string(file, GROUP_DEVICE, "key", credential->key);
    g_key_file_set_string(file, GROUP_DEVICE, "name", credential->name);
    g_key_file_set_string_list(file, GROUP_DEVICE, "scopes",
                               (const char *const *) credential->scopes,
                               g_strv_length(credential->scopes));

    g_autofree char *directory = g_path_get_dirname(path);
    if (g_mkdir_with_parents(directory, 0700) != 0) {
        g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_STORE,
                    "cannot create %s to keep this device's key: %s", directory,
                    g_strerror(errno));
        return FALSE;
    }
    gsize length = 0;
    char *data = g_key_file_to_data(file, &length, NULL);
    g_autoptr(GError) failure = NULL;
    gboolean saved = g_file_set_contents_full(path, data, (gssize) length,
                                              G_FILE_SET_CONTENTS_CONSISTENT, 0600, &failure);
    wipe(data, length);
    g_free(data);
    if (!saved)
        g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_STORE,
                    "cannot keep this device's key: %s", failure->message);
    return saved;
}

static void
store_refused(GError **error, const char *path, const char *why)
{
    g_set_error(error, KR_PAIRING_ERROR, KR_PAIRING_ERROR_STORE, "the paired hub's key %s %s",
                path, why);
}

/* The whole file, read from a descriptor that was checked: owner-only, regular, bounded.
 * The checks are made on the open descriptor, so the file cannot be swapped between check
 * and read (as kr_hub_read_token). */
static char *
read_owned(const char *path, gsize *length, GError **error)
{
    int fd = g_open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC, 0);
    if (fd < 0) {
        int saved = errno;
        if (saved == ELOOP)
            store_refused(error, path, "is a symlink");
        else
            g_set_error(error, G_FILE_ERROR, g_file_error_from_errno(saved), "%s: %s", path,
                        g_strerror(saved));
        return NULL;
    }
    struct stat info;
    const char *why = NULL;
    if (fstat(fd, &info) != 0 || !S_ISREG(info.st_mode))
        why = "is not a regular file";
    else if ((info.st_mode & (S_IRWXG | S_IRWXO)) != 0)
        why = "can be read by others: it must be mode 0600";
    else if (info.st_size > CREDENTIAL_MAX)
        why = "is larger than a key file can be";
    if (why != NULL) {
        close(fd);
        store_refused(error, path, why);
        return NULL;
    }
    char *buffer = g_malloc((gsize) info.st_size + 1);
    gsize got = 0;
    ssize_t n = 0;
    while (got < (gsize) info.st_size &&
           (n = read(fd, buffer + got, (gsize) info.st_size - got)) > 0)
        got += (gsize) n;
    close(fd);
    buffer[got] = '\0';
    *length = got;
    return buffer;
}

KrDeviceCredential *
kr_device_credential_load(const char *path, GError **error)
{
    gsize length = 0;
    char *data = read_owned(path, &length, error);
    if (data == NULL)
        return NULL;
    g_autoptr(GKeyFile) file = g_key_file_new();
    gboolean parsed = g_key_file_load_from_data(file, data, length, G_KEY_FILE_NONE, NULL);
    wipe(data, length);
    g_free(data);
    if (!parsed) {
        store_refused(error, path, "is not a key file");
        return NULL;
    }

    g_autoptr(KrDeviceCredential) credential = g_new0(KrDeviceCredential, 1);
    credential->scheme = g_key_file_get_string(file, GROUP_HUB, "scheme", NULL);
    credential->host = g_key_file_get_string(file, GROUP_HUB, "host", NULL);
    gint port = g_key_file_get_integer(file, GROUP_HUB, "port", NULL);
    credential->fingerprint = g_key_file_get_string(file, GROUP_HUB, "fingerprint", NULL);
    credential->device_id = g_key_file_get_string(file, GROUP_DEVICE, "id", NULL);
    credential->key = g_key_file_get_string(file, GROUP_DEVICE, "key", NULL);
    credential->name = g_key_file_get_string(file, GROUP_DEVICE, "name", NULL);
    credential->scopes = g_key_file_get_string_list(file, GROUP_DEVICE, "scopes", NULL, NULL);
    if (credential->scopes == NULL)
        credential->scopes = g_new0(char *, 1);

    gboolean https = g_strcmp0(credential->scheme, "https") == 0;
    gboolean http = g_strcmp0(credential->scheme, "http") == 0;
    const char *why = NULL;
    if ((!https && !http) || !filled(credential->host) || port <= 0 || port > 65535 ||
        !filled(credential->device_id) || !filled(credential->key))
        why = "is incomplete";
    else if (https && !kr_pairing_fingerprint_valid(credential->fingerprint))
        why = "pins no certificate for its https hub";
    else if (http && (credential->fingerprint != NULL || !kr_hub_host_is_loopback(credential->host)))
        why = "names plain http for a hub on another computer";
    if (why != NULL) {
        store_refused(error, path, why);
        return NULL;
    }
    credential->port = (guint16) port;
    return g_steal_pointer(&credential);
}
