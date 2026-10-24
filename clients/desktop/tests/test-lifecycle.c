/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-lifecycle: the rules a name and a reason follow, the bodies the four routes take, and the
 * words before an unwind. The names and limits mirror hub_service.py (PROJECT_NAME,
 * MAX_INTAKE, MAX_REASON): a name the desktop lets through and the hub refuses is a bug here. */

#include <glib.h>
#include <string.h>

#include "kr-lifecycle.h"

static void
test_names_the_hub_accepts(void)
{
    const char *good[] = {"greeter", "my-first-app", "a", "v1.2_final", "  padded  ", "9lives"};
    for (gsize i = 0; i < G_N_ELEMENTS(good); i++)
        g_assert_null(kr_lifecycle_name_problem(good[i]));
    g_autofree char *longest = g_strnfill(64, 'x');
    g_assert_null(kr_lifecycle_name_problem(longest));
}

static void
test_names_the_hub_refuses_say_why(void)
{
    g_assert_nonnull(strstr(kr_lifecycle_name_problem(NULL), "Give the project a name"));
    g_assert_nonnull(strstr(kr_lifecycle_name_problem("   "), "Give the project a name"));
    const char *bad[] = {"has space", "-flag", ".hidden", "_x", "a/b", "..", "über", "tab\there"};
    for (gsize i = 0; i < G_N_ELEMENTS(bad); i++)
        g_assert_nonnull(strstr(kr_lifecycle_name_problem(bad[i]), "letters, digits"));
    g_autofree char *too_long = g_strnfill(65, 'x');
    g_assert_nonnull(strstr(kr_lifecycle_name_problem(too_long), "at most 64"));
}

static void
test_the_start_body_is_a_name_and_an_intake_and_never_a_path(void)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *both = kr_lifecycle_start_body(" greeter ", "  a greeting page  ", &error);
    g_assert_no_error(error);
    g_assert_cmpstr(both, ==, "{\"name\":\"greeter\",\"intake\":\"a greeting page\"}");
    g_autofree char *bare = kr_lifecycle_start_body("greeter", "   ", &error);
    g_assert_cmpstr(bare, ==, "{\"name\":\"greeter\"}");
    g_autofree char *none = kr_lifecycle_start_body("greeter", NULL, &error);
    g_assert_cmpstr(none, ==, "{\"name\":\"greeter\"}");
    g_autofree char *quoted = kr_lifecycle_start_body("greeter", "say \"hi\"\nthen stop", &error);
    g_assert_cmpstr(quoted, ==, "{\"name\":\"greeter\",\"intake\":\"say \\\"hi\\\"\\nthen stop\"}");
    g_assert_null(strstr(both, "repo"));
}

static void
test_a_bad_start_is_refused_before_the_hub_is_asked(void)
{
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_lifecycle_start_body("has space", "x", &error));
    g_assert_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_INVALID);
    g_clear_error(&error);
    g_autofree char *huge = g_strnfill(KR_LIFECYCLE_MAX_INTAKE + 1, 'x');
    g_assert_null(kr_lifecycle_start_body("greeter", huge, &error));
    g_assert_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_INVALID);
    g_clear_error(&error);
    g_autofree char *exact = g_strnfill(KR_LIFECYCLE_MAX_INTAKE, 'x');
    g_autofree char *fine = kr_lifecycle_start_body("greeter", exact, &error);
    g_assert_no_error(error);
    g_assert_nonnull(fine);
}

static void
test_the_abandon_body_needs_a_reason(void)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *dry = kr_lifecycle_abandon_body("  not needed ", TRUE, &error);
    g_assert_cmpstr(dry, ==, "{\"reason\":\"not needed\",\"dry_run\":true}");
    g_autofree char *real = kr_lifecycle_abandon_body("not needed", FALSE, &error);
    g_assert_cmpstr(real, ==, "{\"reason\":\"not needed\",\"dry_run\":false}");
    g_assert_null(kr_lifecycle_abandon_body("", TRUE, &error));
    g_assert_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_INVALID);
    g_clear_error(&error);
    g_assert_null(kr_lifecycle_abandon_body(NULL, TRUE, &error));
    g_clear_error(&error);
    g_autofree char *huge = g_strnfill(KR_LIFECYCLE_MAX_REASON + 1, 'x');
    g_assert_null(kr_lifecycle_abandon_body(huge, TRUE, &error));
    g_clear_error(&error);
}

static void
test_a_created_project_is_read_from_the_hubs_document(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrCreated) full = kr_lifecycle_parse_created(
        "{\"project_id\":\"p9\",\"name\":\"greeter\",\"outcome\":\"design job j1\"}", &error);
    g_assert_no_error(error);
    g_assert_cmpstr(full->project_id, ==, "p9");
    g_assert_cmpstr(full->name, ==, "greeter");
    g_assert_cmpstr(full->outcome, ==, "design job j1");
    g_autoptr(KrCreated) sparse = kr_lifecycle_parse_created("{\"project_id\":\"p9\"}", &error);
    g_assert_cmpstr(sparse->name, ==, "p9");
    g_assert_cmpstr(sparse->outcome, ==, "");
    g_autoptr(KrCreated) odd = kr_lifecycle_parse_created(
        "{\"project_id\":\"p9\",\"name\":7,\"outcome\":[]}", &error);
    g_assert_cmpstr(odd->name, ==, "p9");
}

static void
test_what_is_not_a_project_is_refused(void)
{
    const char *bad[] = {"[]", "not json", "{}", "{\"project_id\":3}", NULL};
    for (gsize i = 0; i < G_N_ELEMENTS(bad); i++) {
        g_autoptr(GError) error = NULL;
        g_assert_null(kr_lifecycle_parse_created(bad[i], &error));
        g_assert_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_ANSWER);
    }
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_lifecycle_parse_report("{}", &error));
    g_assert_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_ANSWER);
    g_clear_error(&error);
    g_assert_null(kr_lifecycle_parse_report("[1]", &error));
    g_clear_error(&error);
    /* No GError to fill is allowed too. */
    g_assert_null(kr_lifecycle_parse_created("[]", NULL));
}

static void
test_an_unwind_report_is_counted_not_listed(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrAbandonReport) report = kr_lifecycle_parse_report(
        "{\"project_id\":\"p1\",\"name\":\"Greeter\",\"from\":\"build\",\"dry_run\":true,"
        "\"already_abandoned\":false,\"cancelled_jobs\":[{},{}],\"withdrawn_gates\":[{}]}",
        &error);
    g_assert_no_error(error);
    g_assert_cmpstr(report->name, ==, "Greeter");
    g_assert_cmpstr(report->from, ==, "build");
    g_assert_true(report->dry_run);
    g_assert_false(report->already_abandoned);
    g_assert_cmpuint(report->cancelled_jobs, ==, 2);
    g_assert_cmpuint(report->withdrawn_gates, ==, 1);
    g_autoptr(KrAbandonReport) sparse = kr_lifecycle_parse_report("{\"project_id\":\"p1\"}", &error);
    g_assert_cmpstr(sparse->name, ==, "p1");
    g_assert_cmpstr(sparse->from, ==, "");
    g_assert_cmpuint(sparse->cancelled_jobs, ==, 0);
    g_autoptr(KrAbandonReport) odd = kr_lifecycle_parse_report(
        "{\"project_id\":\"p1\",\"cancelled_jobs\":7,\"withdrawn_gates\":\"x\"}", &error);
    g_assert_cmpuint(odd->cancelled_jobs, ==, 0);
    g_assert_cmpuint(odd->withdrawn_gates, ==, 0);
}

static void
test_the_confirmation_says_what_would_be_cancelled_and_that_it_is_final(void)
{
    KrAbandonReport report = {.name = (char *) "Greeter", .from = (char *) "build",
                              .cancelled_jobs = 2, .withdrawn_gates = 1};
    g_autofree char *text = kr_lifecycle_confirm_text(&report);
    g_assert_nonnull(strstr(text, "\"Greeter\" is in build"));
    g_assert_nonnull(strstr(text, "cancels 2 queued or running jobs"));
    g_assert_nonnull(strstr(text, "withdraws 1 waiting question,"));
    g_assert_nonnull(strstr(text, "cannot be undone"));
    report.from = (char *) "";
    report.cancelled_jobs = 1;
    report.withdrawn_gates = 3;
    g_autofree char *plain = kr_lifecycle_confirm_text(&report);
    g_assert_null(strstr(plain, " is in "));
    g_assert_nonnull(strstr(plain, "cancels 1 queued or running job and"));
    g_assert_nonnull(strstr(plain, "withdraws 3 waiting questions"));
    report.already_abandoned = TRUE;
    g_autofree char *done = kr_lifecycle_confirm_text(&report);
    g_assert_cmpstr(done, ==, "\"Greeter\" is already unwound. Nothing changes.");
}

static void
test_a_work_routes_message_or_the_fallback(void)
{
    g_autofree char *said = kr_lifecycle_message("{\"message\":\"worker started\"}", "Started.");
    g_assert_cmpstr(said, ==, "worker started");
    g_autofree char *none = kr_lifecycle_message("{}", "Paused.");
    g_assert_cmpstr(none, ==, "Paused.");
    g_autofree char *empty = kr_lifecycle_message("{\"message\":\"\"}", "Paused.");
    g_assert_cmpstr(empty, ==, "Paused.");
    g_autofree char *junk = kr_lifecycle_message("nope", "Started.");
    g_assert_cmpstr(junk, ==, "Started.");
    g_autofree char *numeric = kr_lifecycle_message("{\"message\":3}", "Started.");
    g_assert_cmpstr(numeric, ==, "Started.");
    g_autofree char *absent = kr_lifecycle_message(NULL, "Started.");
    g_assert_cmpstr(absent, ==, "Started.");
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/lifecycle/names-accepted", test_names_the_hub_accepts);
    g_test_add_func("/lifecycle/names-refused", test_names_the_hub_refuses_say_why);
    g_test_add_func("/lifecycle/start-body", test_the_start_body_is_a_name_and_an_intake_and_never_a_path);
    g_test_add_func("/lifecycle/start-refused", test_a_bad_start_is_refused_before_the_hub_is_asked);
    g_test_add_func("/lifecycle/abandon-body", test_the_abandon_body_needs_a_reason);
    g_test_add_func("/lifecycle/created", test_a_created_project_is_read_from_the_hubs_document);
    g_test_add_func("/lifecycle/not-a-document", test_what_is_not_a_project_is_refused);
    g_test_add_func("/lifecycle/report", test_an_unwind_report_is_counted_not_listed);
    g_test_add_func("/lifecycle/confirm", test_the_confirmation_says_what_would_be_cancelled_and_that_it_is_final);
    g_test_add_func("/lifecycle/message", test_a_work_routes_message_or_the_fallback);
    return g_test_run();
}
