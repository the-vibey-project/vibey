/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-pairing: reading what a hub shows a person when it offers to pair.
 *
 * Being on the same network proves nothing (SD-01, ADR-0068): a device pairs once, by
 * scanning the hub's QR code or typing its 6-digit code, and only then is trusted. The hub
 * side of pairing is its own change (ADR-0068, "Pairing and trust"); until it lands, this
 * module fixes the client's half of the contract and says so: a pairing offer is a URI
 *
 *     vibey-pair://<host>:<port>?code=<6 digits>&fp=<SHA-256 of the hub certificate, hex>
 *
 * and the code alone is six ASCII digits. The certificate fingerprint is what makes the
 * later encrypted connection trustworthy: Krypton pins it, and a hub that later shows a
 * different certificate is refused. PROVISIONAL until the hub's pairing change ratifies it. */

#ifndef KR_PAIRING_H
#define KR_PAIRING_H

#include <glib.h>

G_BEGIN_DECLS

#define KR_PAIRING_SCHEME "vibey-pair"
#define KR_PAIRING_CODE_LENGTH 6
#define KR_PAIRING_FINGERPRINT_LENGTH 64 /* SHA-256, as lowercase hex */

#define KR_PAIRING_ERROR (kr_pairing_error_quark())
GQuark kr_pairing_error_quark(void);

typedef enum {
    KR_PAIRING_ERROR_INVALID,
} KrPairingError;

typedef struct {
    char *host;
    guint16 port;
    char *code;        /* six digits */
    char *fingerprint; /* 64 lowercase hex characters */
} KrPairingOffer;

/* Exactly six ASCII digits, nothing around them. */
gboolean kr_pairing_code_valid(const char *code);

/* A code as typed: spaces and dashes a person adds ("123 456", "123-456") are dropped.
 * NULL when what remains is not a valid code. */
char *kr_pairing_code_normalise(const char *typed);

/* Reads the URI a hub's QR code carries. */
KrPairingOffer *kr_pairing_offer_parse(const char *uri, GError **error);
void kr_pairing_offer_free(KrPairingOffer *offer);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrPairingOffer, kr_pairing_offer_free)

/* The fingerprint grouped for a person to compare by eye: "ab12 cd34 ...". */
char *kr_pairing_fingerprint_display(const char *fingerprint);

G_END_DECLS

#endif /* KR_PAIRING_H */
