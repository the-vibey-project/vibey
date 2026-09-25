/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-answer.h"

static void
builds(const char *kind, const char *value, const char *want)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *got = kr_answer_build(kind, value, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(got, ==, want);
}

static void
refuses(const char *kind, const char *value, gint code)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *got = kr_answer_build(kind, value, &error);
    g_assert_null(got);
    g_assert_error(error, KR_ANSWER_ERROR, code);
}

static void
test_shapes(void)
{
    const char *key = "unset";
    g_assert_cmpint(kr_answer_shape("question", &key), ==, KR_ANSWER_DEFAULTS);
    g_assert_null(key);
    g_assert_cmpint(kr_answer_shape("approval", NULL), ==, KR_ANSWER_VERDICT);
    g_assert_cmpint(kr_answer_shape("deploy_acceptance", NULL), ==, KR_ANSWER_CHOICE);
    g_assert_cmpint(kr_answer_shape("budget_exhausted", &key), ==, KR_ANSWER_GRANT);
    g_assert_cmpstr(key, ==, "max_dollars");
    g_assert_cmpint(kr_answer_shape("attempts_exhausted", &key), ==, KR_ANSWER_GRANT);
    g_assert_cmpstr(key, ==, "max_attempts");
    g_assert_cmpint(kr_answer_shape("verify_repair_exhausted", &key), ==, KR_ANSWER_GRANT);
    g_assert_cmpstr(key, ==, "max_rounds");
    g_assert_cmpint(kr_answer_shape("ultra_needs_cap", NULL), ==, KR_ANSWER_ANY);
    g_assert_cmpint(kr_answer_shape("handoff_gate_failed", &key), ==, KR_ANSWER_FREE_FORM);
    g_assert_null(key);
    g_assert_cmpint(kr_answer_shape(NULL, NULL), ==, KR_ANSWER_FREE_FORM);
}

static void
test_build(void)
{
    builds("approval", "accept", "{\"verdict\":\"accept\"}");
    builds("deploy_interview", "yes \"quoted\"", "{\"choice\":\"yes \\\"quoted\\\"\"}");
    builds("budget_exhausted", "25", "{\"max_dollars\":25}");
    builds("budget_exhausted", "12.5", "{\"max_dollars\":12.5}");
    builds("attempts_exhausted", "0", "{\"max_attempts\":0}");
    builds("engine_misconfigured", NULL, "{}");
    builds("too_many_wind_downs", " {\"why\": \"fixed\"} ", "{\"why\":\"fixed\"}");

    refuses("question", NULL, KR_ANSWER_ERROR_UNSUPPORTED);
    refuses("approval", NULL, KR_ANSWER_ERROR_INVALID);
    refuses("choice", "", KR_ANSWER_ERROR_INVALID);
    refuses("budget_exhausted", NULL, KR_ANSWER_ERROR_INVALID);
    refuses("budget_exhausted", "N", KR_ANSWER_ERROR_INVALID);
    refuses("budget_exhausted", "5x", KR_ANSWER_ERROR_INVALID);
    refuses("budget_exhausted", "-1", KR_ANSWER_ERROR_INVALID);
    refuses("budget_exhausted", "inf", KR_ANSWER_ERROR_INVALID);
    refuses("some_new_kind", "<json>", KR_ANSWER_ERROR_INVALID);
    refuses("some_new_kind", "[1]", KR_ANSWER_ERROR_INVALID);
    refuses("some_new_kind", NULL, KR_ANSWER_ERROR_INVALID);
}

static void
test_body(void)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *body = kr_answer_body("{\"verdict\":\"accept\"}", "r-1", &error);
    g_assert_no_error(error);
    g_assert_cmpstr(body, ==, "{\"answer\":{\"verdict\":\"accept\"},\"request_id\":\"r-1\"}");

    g_assert_null(kr_answer_body("nope", "r-1", &error));
    g_assert_error(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID);
    g_clear_error(&error);
    g_assert_null(kr_answer_body(NULL, "r-1", &error));
    g_assert_error(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID);
    g_clear_error(&error);
    g_assert_null(kr_answer_body("{}", "", &error));
    g_assert_error(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID);
    g_clear_error(&error);
    g_assert_null(kr_answer_body("{}", NULL, &error));
    g_assert_error(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID);
}

static void
test_request_id(void)
{
    g_autofree char *first = kr_answer_request_id();
    g_autofree char *second = kr_answer_request_id();
    g_assert_true(g_uuid_string_is_valid(first));
    g_assert_cmpstr(first, !=, second);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/answer/shapes", test_shapes);
    g_test_add_func("/answer/build", test_build);
    g_test_add_func("/answer/body", test_body);
    g_test_add_func("/answer/request-id", test_request_id);
    return g_test_run();
}
