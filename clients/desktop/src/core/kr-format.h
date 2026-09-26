/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-format: how Krypton desktop says numbers, times and phases to a person.
 *
 * The interface of the formatting module (ADR-0016 in C: the header declares, the .c
 * implements). Pure: no I/O, no clock -- "now" is always passed in. Every function that
 * returns char * returns a newly allocated string the caller frees with g_free(). */

#ifndef KR_FORMAT_H
#define KR_FORMAT_H

#include <glib.h>

G_BEGIN_DECLS

/* The sign shown for a value that cannot be said: NaN, infinity, a missing cap. */
#define KR_FORMAT_UNKNOWN "—"

/* "$1,234.50"; "-$3.00" when negative; KR_FORMAT_UNKNOWN when not finite. */
char *kr_format_dollars(double dollars);

/* "0s", "42s", "4m 05s", "2h 03m", "3d 4h". Negative durations say "0s". */
char *kr_format_duration(gint64 seconds);

/* How long ago `then` was, as of `now` (both Unix seconds): "just now", "5 min ago",
 * "3 h ago", "2 d ago", or for the future "in 5 min". A `then` of 0 means unknown. */
char *kr_format_relative(gint64 then, gint64 now);

/* The phase names vibey prints (DESIGN, VISUAL_DESIGN, ...) in words: "Design",
 * "Visual design". Unknown names come back as given; NULL comes back as "Unknown".
 * The returned string is static: do not free it. */
const char *kr_format_phase(const char *phase);

/* "12 / 50 turns"; "12 turns" when there is no cap (cap <= 0). */
char *kr_format_turns(gint64 spent, gint64 cap);

/* A share of a cap in [0, 1] for a level bar: spent / cap, clamped. 0 when no cap. */
double kr_format_fraction(double spent, double cap);

G_END_DECLS

#endif /* KR_FORMAT_H */
