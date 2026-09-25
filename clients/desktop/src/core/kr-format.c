/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-format.h"

#include <math.h>
#include <string.h>

char *
kr_format_dollars(double dollars)
{
    if (!isfinite(dollars))
        return g_strdup(KR_FORMAT_UNKNOWN);

    gboolean negative = dollars < 0;
    /* Whole cents, rounded half away from zero. */
    gint64 cents = (gint64) llround(fabs(dollars) * 100.0);
    gint64 whole = cents / 100;
    gint64 rest = cents % 100;

    /* Group the whole dollars in threes. */
    g_autofree char *digits = g_strdup_printf("%" G_GINT64_FORMAT, whole);
    size_t len = strlen(digits);
    GString *grouped = g_string_new(negative ? "-$" : "$");
    for (size_t i = 0; i < len; i++) {
        if (i > 0 && (len - i) % 3 == 0)
            g_string_append_c(grouped, ',');
        g_string_append_c(grouped, digits[i]);
    }
    g_string_append_printf(grouped, ".%02" G_GINT64_FORMAT, rest);
    return g_string_free(grouped, FALSE);
}

char *
kr_format_duration(gint64 seconds)
{
    if (seconds < 60)
        return g_strdup_printf("%" G_GINT64_FORMAT "s", seconds < 0 ? 0 : seconds);
    if (seconds < 3600)
        return g_strdup_printf("%" G_GINT64_FORMAT "m %02" G_GINT64_FORMAT "s", seconds / 60,
                               seconds % 60);
    if (seconds < 86400)
        return g_strdup_printf("%" G_GINT64_FORMAT "h %02" G_GINT64_FORMAT "m", seconds / 3600,
                               (seconds % 3600) / 60);
    return g_strdup_printf("%" G_GINT64_FORMAT "d %" G_GINT64_FORMAT "h", seconds / 86400,
                           (seconds % 86400) / 3600);
}

char *
kr_format_relative(gint64 then, gint64 now)
{
    if (then == 0)
        return g_strdup(KR_FORMAT_UNKNOWN);

    gint64 delta = now - then;
    gboolean future = delta < 0;
    gint64 span = future ? -delta : delta;

    if (span < 45)
        return g_strdup("just now");

    g_autofree char *amount = NULL;
    if (span < 3600)
        amount = g_strdup_printf("%" G_GINT64_FORMAT " min", MAX(span / 60, 1));
    else if (span < 86400)
        amount = g_strdup_printf("%" G_GINT64_FORMAT " h", span / 3600);
    else
        amount = g_strdup_printf("%" G_GINT64_FORMAT " d", span / 86400);

    return future ? g_strdup_printf("in %s", amount) : g_strdup_printf("%s ago", amount);
}

typedef struct {
    const char *name;
    const char *words;
} PhaseName;

/* The phases the six-phase model names (CLAUDE.md), and the two ends. */
static const PhaseName PHASES[] = {
    {"INTAKE", "Intake"},
    {"DESIGN", "Design"},
    {"VISUAL_DESIGN", "Visual design"},
    {"BUILD", "Build"},
    {"REVIEW", "Review"},
    {"DEPLOY_DESIGN", "Deploy design"},
    {"DEPLOY_EXECUTE", "Deploy"},
    {"DEPLOY", "Deploy"},
    {"DEPLOY_REVIEW", "Deploy review"},
    {"DONE", "Done"},
};

const char *
kr_format_phase(const char *phase)
{
    if (phase == NULL)
        return "Unknown";
    for (size_t i = 0; i < G_N_ELEMENTS(PHASES); i++) {
        if (g_ascii_strcasecmp(PHASES[i].name, phase) == 0)
            return PHASES[i].words;
    }
    return phase;
}

char *
kr_format_turns(gint64 spent, gint64 cap)
{
    if (cap <= 0)
        return g_strdup_printf("%" G_GINT64_FORMAT " turns", spent);
    return g_strdup_printf("%" G_GINT64_FORMAT " / %" G_GINT64_FORMAT " turns", spent, cap);
}

double
kr_format_fraction(double spent, double cap)
{
    if (!(cap > 0) || !isfinite(spent))
        return 0.0;
    return CLAMP(spent / cap, 0.0, 1.0);
}
