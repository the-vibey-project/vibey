/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-answer: the body that answers a gate.
 *
 * POST /api/v1/gates/{gate_id}/answer takes {"answer": {...}, "request_id": "..."}, where
 * `answer` is what `vibey answer --raw` takes. Which answer a gate reads depends on its kind,
 * and the table is src/vibey/cli/gate_answers.py (ANSWER_RULES); this module mirrors it so
 * the desktop offers the same controls the CLI prints in `answer_with`. A kind it does not
 * know is answered free-form, exactly as the CLI's fallback does. */

#ifndef KR_ANSWER_H
#define KR_ANSWER_H

#include <glib.h>

G_BEGIN_DECLS

#define KR_ANSWER_ERROR (kr_answer_error_quark())
GQuark kr_answer_error_quark(void);

typedef enum {
    KR_ANSWER_ERROR_INVALID,     /* the value is not an answer this gate reads */
    KR_ANSWER_ERROR_UNSUPPORTED, /* this kind is answered in the CLI's interview */
} KrAnswerError;

typedef enum {
    KR_ANSWER_DEFAULTS,  /* the DESIGN interview: `vibey answer --defaults` */
    KR_ANSWER_VERDICT,   /* {"verdict": <one of the options>} */
    KR_ANSWER_CHOICE,    /* {"choice": <one of the options>} */
    KR_ANSWER_GRANT,     /* {"<key>": <a new bound, a non-negative number>} */
    KR_ANSWER_ANY,       /* {} -- any answer retries */
    KR_ANSWER_FREE_FORM, /* a JSON object the person writes */
} KrAnswerShape;

/* The shape a gate of `kind` reads. For KR_ANSWER_GRANT, *grant_key (if not NULL) is set to
 * the static key the grant names ("max_dollars", "max_attempts", "max_rounds"). */
KrAnswerShape kr_answer_shape(const char *kind, const char **grant_key);

/* The `answer` object for a gate of `kind`, as compact JSON. `value` is the option chosen
 * (VERDICT, CHOICE), the new bound (GRANT), the object text (FREE_FORM), or ignored (ANY).
 * NULL with KR_ANSWER_ERROR set when the value does not fit. */
char *kr_answer_build(const char *kind, const char *value, GError **error);

/* The full request body: {"answer": <answer>, "request_id": "<request_id>"}. The same
 * request_id with the same answer is a no-op on the hub, so a retry is safe. */
char *kr_answer_body(const char *answer_json, const char *request_id, GError **error);

/* A fresh request id (a random UUID) for one person's one answer. */
char *kr_answer_request_id(void);

G_END_DECLS

#endif /* KR_ANSWER_H */
