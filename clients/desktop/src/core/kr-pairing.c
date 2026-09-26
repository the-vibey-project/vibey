/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-pairing.h"

#include <string.h>

G_DEFINE_QUARK(kr-pairing-error-quark, kr_pairing_error)

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

static gboolean
fingerprint_valid(const char *fingerprint)
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
    g_autoptr(GUri) parsed = g_uri_parse(uri, G_URI_FLAGS_NONE, NULL);
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
    if (!kr_pairing_code_valid(code))
        return refuse(error, "its code is not six digits");
    if (!fingerprint_valid(fingerprint))
        return refuse(error, "its certificate fingerprint is not a SHA-256");

    KrPairingOffer *offer = g_new0(KrPairingOffer, 1);
    offer->host = g_strdup(host);
    offer->port = (guint16) port;
    offer->code = g_strdup(code);
    offer->fingerprint = g_ascii_strdown(fingerprint, -1);
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
