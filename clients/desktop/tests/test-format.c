/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include <math.h>

#include "kr-format.h"

static void
expect(char *got, const char *want)
{
    g_assert_cmpstr(got, ==, want);
    g_free(got);
}

static void
test_dollars(void)
{
    expect(kr_format_dollars(0), "$0.00");
    expect(kr_format_dollars(3), "$3.00");
    expect(kr_format_dollars(1234.5), "$1,234.50");
    expect(kr_format_dollars(1234567.891), "$1,234,567.89");
    expect(kr_format_dollars(999.999), "$1,000.00");
    expect(kr_format_dollars(-3), "-$3.00");
    expect(kr_format_dollars(NAN), KR_FORMAT_UNKNOWN);
    expect(kr_format_dollars(INFINITY), KR_FORMAT_UNKNOWN);
}

static void
test_duration(void)
{
    expect(kr_format_duration(-5), "0s");
    expect(kr_format_duration(0), "0s");
    expect(kr_format_duration(42), "42s");
    expect(kr_format_duration(245), "4m 05s");
    expect(kr_format_duration(2 * 3600 + 3 * 60 + 9), "2h 03m");
    expect(kr_format_duration(3 * 86400 + 4 * 3600 + 59), "3d 4h");
}

static void
test_relative(void)
{
    const gint64 now = 1790000000;
    expect(kr_format_relative(0, now), KR_FORMAT_UNKNOWN);
    expect(kr_format_relative(now - 10, now), "just now");
    expect(kr_format_relative(now - 50, now), "1 min ago");
    expect(kr_format_relative(now - 5 * 60, now), "5 min ago");
    expect(kr_format_relative(now - 3 * 3600, now), "3 h ago");
    expect(kr_format_relative(now - 2 * 86400, now), "2 d ago");
    expect(kr_format_relative(now + 5 * 60, now), "in 5 min");
}

static void
test_phase(void)
{
    g_assert_cmpstr(kr_format_phase("DESIGN"), ==, "Design");
    g_assert_cmpstr(kr_format_phase("visual_design"), ==, "Visual design");
    g_assert_cmpstr(kr_format_phase("DEPLOY_EXECUTE"), ==, "Deploy");
    g_assert_cmpstr(kr_format_phase("DONE"), ==, "Done");
    g_assert_cmpstr(kr_format_phase("SOMETHING_NEW"), ==, "SOMETHING_NEW");
    g_assert_cmpstr(kr_format_phase(NULL), ==, "Unknown");
}

static void
test_turns_and_fraction(void)
{
    expect(kr_format_turns(12, 50), "12 / 50 turns");
    expect(kr_format_turns(12, 0), "12 turns");
    g_assert_cmpfloat(kr_format_fraction(5, 10), ==, 0.5);
    g_assert_cmpfloat(kr_format_fraction(15, 10), ==, 1.0);
    g_assert_cmpfloat(kr_format_fraction(-1, 10), ==, 0.0);
    g_assert_cmpfloat(kr_format_fraction(5, 0), ==, 0.0);
    g_assert_cmpfloat(kr_format_fraction(NAN, 10), ==, 0.0);
    g_assert_cmpfloat(kr_format_fraction(5, NAN), ==, 0.0);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/format/dollars", test_dollars);
    g_test_add_func("/format/duration", test_duration);
    g_test_add_func("/format/relative", test_relative);
    g_test_add_func("/format/phase", test_phase);
    g_test_add_func("/format/turns-and-fraction", test_turns_and_fraction);
    return g_test_run();
}
