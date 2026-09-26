/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-pairing.h"

#define FP "0123456789ABCDEF0123456789abcdef0123456789abcdef0123456789abcdef"

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
    g_assert_cmpstr(offer->fingerprint, ==,
                    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef");
    kr_pairing_offer_free(NULL);
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
}

static void
test_display(void)
{
    g_autofree char *grouped = kr_pairing_fingerprint_display("ABCD1234ef");
    g_assert_cmpstr(grouped, ==, "abcd 1234 ef");
    g_autofree char *none = kr_pairing_fingerprint_display(NULL);
    g_assert_cmpstr(none, ==, "");
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/pairing/code", test_code);
    g_test_add_func("/pairing/offer", test_offer);
    g_test_add_func("/pairing/refusals", test_refusals);
    g_test_add_func("/pairing/display", test_display);
    return g_test_run();
}
