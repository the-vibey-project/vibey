/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The pure half of running a command on the workflows: the typed command line split into
 * words, the body the hub reads, its answers in every state, and its refusals in words. */
#include <string.h>

#include "kr-workflows.h"

static void
split_is(const char *line, const char *const *want)
{
    g_autoptr(GError) error = NULL;
    g_auto(GStrv) words = kr_workflows_split(line, &error);
    g_assert_no_error(error);
    g_assert_cmpstrv(words, want);
}

static void
split_refused(const char *line, const char *says)
{
    g_autoptr(GError) error = NULL;
    g_auto(GStrv) words = kr_workflows_split(line, &error);
    g_assert_null(words);
    g_assert_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_COMMAND);
    if (strstr(error->message, says) == NULL)
        g_error("\"%s\" does not say \"%s\"", error->message, says);
}

static void
test_split(void)
{
    split_is("status --json", (const char *const[]){"status", "--json", NULL});
    split_is("  status \t --json\n", (const char *const[]){"status", "--json", NULL});
    /* Double quotes keep their spaces, inside a word or as one. */
    split_is("answer g-1 \"yes, ship it\"",
             (const char *const[]){"answer", "g-1", "yes, ship it", NULL});
    split_is("new --title=\"a b\" x", (const char *const[]){"new", "--title=a b", "x", NULL});
    split_is("say \"\" end", (const char *const[]){"say", "", "end", NULL});
    split_is("a\"b c\"d", (const char *const[]){"ab cd", NULL});
    /* Inside quotes, \" is a quote and \\ a backslash; any other backslash is itself. */
    split_is("say \"a \\\"b\\\" \\\\ \\n\"", (const char *const[]){"say", "a \"b\" \\ \\n", NULL});
    split_is("path C:\\dir", (const char *const[]){"path", "C:\\dir", NULL});
    /* How the command is sent is not part of it. */
    split_is("vibey status", (const char *const[]){"status", NULL});
    split_is("vibey -w status", (const char *const[]){"status", NULL});
    split_is("--workflows --log-level debug status",
             (const char *const[]){"--log-level", "debug", "status", NULL});
    split_is("-w --version", (const char *const[]){"--version", NULL});
    /* After the command, -w is the command's own. */
    split_is("ledger show -w", (const char *const[]){"ledger", "show", "-w", NULL});
    split_is("-- -w", (const char *const[]){"--", "-w", NULL});
    split_is("- -w", (const char *const[]){"-", "-w", NULL});
    split_is("status vibey", (const char *const[]){"status", "vibey", NULL});

    split_refused("", "Type a vibey command");
    split_refused(NULL, "Type a vibey command");
    split_refused("   ", "Type a vibey command");
    split_refused("vibey -w", "Type a vibey command");
    split_refused("answer \"open", "not closed");

    g_autoptr(GString) many = g_string_new("status");
    for (int i = 1; i < KR_WORKFLOWS_MAX_WORDS; i++)
        g_string_append(many, " x");
    g_autoptr(GError) error = NULL;
    g_auto(GStrv) most = kr_workflows_split(many->str, &error);
    g_assert_no_error(error);
    g_assert_cmpuint(g_strv_length(most), ==, KR_WORKFLOWS_MAX_WORDS);
    g_string_append(many, " x");
    split_refused(many->str, "at most 200 words; this one has 201");
}

static void
test_body(void)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *body =
        kr_workflows_run_body((const char *const[]){"status", "--json", NULL}, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(body, ==, "{\"argv\":[\"status\",\"--json\"]}");

    /* Every word goes as a JSON string, escaped; an empty word is still a word. */
    g_autofree char *quoted =
        kr_workflows_run_body((const char *const[]){"say", "a \"b\"\\", "", NULL}, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(quoted, ==, "{\"argv\":[\"say\",\"a \\\"b\\\"\\\\\",\"\"]}");

    g_autofree char *none = kr_workflows_run_body((const char *const[]){NULL}, &error);
    g_assert_null(none);
    g_assert_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_COMMAND);
    g_clear_error(&error);
    g_autofree char *missing = kr_workflows_run_body(NULL, &error);
    g_assert_null(missing);
    g_assert_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_COMMAND);
    g_clear_error(&error);

    g_autoptr(GPtrArray) words = g_ptr_array_new();
    for (int i = 0; i <= KR_WORKFLOWS_MAX_WORDS; i++)
        g_ptr_array_add(words, (gpointer) "x");
    g_ptr_array_add(words, NULL);
    g_autofree char *long_body = kr_workflows_run_body((const char *const *) words->pdata, &error);
    g_assert_null(long_body);
    g_assert_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_COMMAND);
}

static KrWorkflowRun *
parse(const char *json)
{
    g_autoptr(GError) error = NULL;
    KrWorkflowRun *run = kr_workflow_run_parse(json, -1, &error);
    g_assert_no_error(error);
    g_assert_nonnull(run);
    return run;
}

static void
parse_refused(const char *json, const char *says)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrWorkflowRun) run = kr_workflow_run_parse(json, -1, &error);
    g_assert_null(run);
    g_assert_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_RESPONSE);
    if (strstr(error->message, says) == NULL)
        g_error("\"%s\" does not say \"%s\"", error->message, says);
}

static void
test_parse_states(void)
{
    /* The 202 the POST answers with, exactly as the hub writes it (RemoteStatus.as_dict). */
    g_autoptr(KrWorkflowRun) queued = parse(
        "{\"request_id\": \"r-12345678\", \"state\": \"queued\", \"url\": \"\", "
        "\"exit_code\": null, \"stdout\": \"\", \"stderr\": \"\", \"detail\": \"\"}");
    g_assert_cmpstr(queued->request_id, ==, "r-12345678");
    g_assert_cmpint(queued->state, ==, KR_WORKFLOW_QUEUED);
    g_assert_null(queued->url);
    g_assert_false(queued->has_exit_code);
    g_assert_null(queued->output);
    g_assert_null(queued->errors);
    g_assert_null(queued->detail);
    g_assert_false(kr_workflow_run_finished(queued));

    g_autoptr(KrWorkflowRun) running = parse(
        "{\"request_id\": \"r-12345678\", \"state\": \"running\", "
        "\"url\": \"https://github.com/o/r/actions/runs/7\", \"exit_code\": null}");
    g_assert_cmpint(running->state, ==, KR_WORKFLOW_RUNNING);
    g_assert_cmpstr(running->url, ==, "https://github.com/o/r/actions/runs/7");
    g_assert_false(kr_workflow_run_finished(running));

    g_autoptr(KrWorkflowRun) done = parse(
        "{\"request_id\": \"r-12345678\", \"state\": \"done\", "
        "\"url\": \"https://github.com/o/r/actions/runs/7\", \"exit_code\": 3, "
        "\"stdout\": \"{\\\"ok\\\": true}\\n\", \"stderr\": \"warning\\n\", \"detail\": \"\"}");
    g_assert_cmpint(done->state, ==, KR_WORKFLOW_DONE);
    g_assert_true(done->has_exit_code);
    g_assert_cmpint(done->exit_code, ==, 3);
    g_assert_cmpstr(done->output, ==, "{\"ok\": true}\n");
    g_assert_cmpstr(done->errors, ==, "warning\n");
    g_assert_true(kr_workflow_run_finished(done));

    g_autoptr(KrWorkflowRun) failed = parse(
        "{\"request_id\": \"r-12345678\", \"state\": \"failed\", \"url\": \"\", "
        "\"exit_code\": null, \"detail\": \"the run was cancelled\"}");
    g_assert_cmpint(failed->state, ==, KR_WORKFLOW_FAILED);
    g_assert_cmpstr(failed->detail, ==, "the run was cancelled");
    g_assert_true(kr_workflow_run_finished(failed));

    /* Fields of the wrong kind say nothing rather than something wrong. */
    g_autoptr(KrWorkflowRun) odd = parse("{\"request_id\": \"r\", \"state\": \"done\", "
                                         "\"exit_code\": \"0\", \"url\": 7, \"stdout\": [1]}");
    g_assert_false(odd->has_exit_code);
    g_assert_null(odd->url);
    g_assert_null(odd->output);

    /* A copy is its own. */
    g_autoptr(KrWorkflowRun) copy = kr_workflow_run_copy(done);
    g_assert_true(copy->output != done->output);
    g_assert_cmpstr(copy->output, ==, done->output);
    g_assert_cmpstr(copy->url, ==, done->url);
    g_assert_cmpint(copy->exit_code, ==, 3);
    kr_workflow_run_free(NULL);
}

static void
test_parse_refused(void)
{
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_workflow_run_parse(NULL, 0, &error));
    g_assert_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_RESPONSE);
    parse_refused("not json", "not JSON");
    parse_refused("[]", "not an object");
    parse_refused("", ""); /* json-glib reads an empty body as no document, or as not JSON */
    /* An error body is not a run. */
    parse_refused("{\"detail\": \"workflows are not enabled on this hub\"}", "no request_id");
    parse_refused("{\"request_id\": \"\", \"state\": \"queued\"}", "no request_id");
    parse_refused("{\"request_id\": \"r\"}", "no state");
    parse_refused("{\"request_id\": \"r\", \"state\": \"lost\"}", "no state");
    parse_refused("{\"request_id\": \"r\", \"state\": 1}", "no state");
}

static void
summary_is(const char *json, const char *want)
{
    g_autoptr(KrWorkflowRun) run = parse(json);
    g_autofree char *summary = kr_workflow_run_summary(run);
    g_assert_cmpstr(summary, ==, want);
}

static void
test_summary(void)
{
    summary_is("{\"request_id\": \"r\", \"state\": \"queued\"}",
               "Queued: waiting for a GitHub runner");
    summary_is("{\"request_id\": \"r\", \"state\": \"running\"}", "Running on a GitHub runner");
    summary_is("{\"request_id\": \"r\", \"state\": \"done\", \"exit_code\": 0}",
               "Done: exit code 0");
    summary_is("{\"request_id\": \"r\", \"state\": \"done\"}", "Done");
    summary_is("{\"request_id\": \"r\", \"state\": \"failed\", \"detail\": \"no runner\"}",
               "Failed: no runner");
    summary_is("{\"request_id\": \"r\", \"state\": \"failed\"}",
               "Failed: the run ended without a report");

    g_assert_cmpstr(kr_workflow_state_name(KR_WORKFLOW_QUEUED), ==, "queued");
    g_assert_cmpstr(kr_workflow_state_name(KR_WORKFLOW_RUNNING), ==, "running");
    g_assert_cmpstr(kr_workflow_state_name(KR_WORKFLOW_DONE), ==, "done");
    g_assert_cmpstr(kr_workflow_state_name(KR_WORKFLOW_FAILED), ==, "failed");
    g_assert_cmpstr(kr_workflow_state_name((KrWorkflowState) 9), ==, "unknown");
}

static void
refusal_says(guint status, const char *detail, const char *says)
{
    g_autofree char *message = kr_workflows_refusal_message(status, detail);
    if (strstr(message, says) == NULL)
        g_error("%u: \"%s\" does not say \"%s\"", status, message, says);
}

static void
test_refusals(void)
{
    refusal_says(401, NULL, "does not know this device");
    refusal_says(403, "krypton on x may not run commands on the workflows",
                 "(the hub said: krypton on x may not run commands on the workflows)");
    refusal_says(403, NULL, "It needs the workflows scope");
    refusal_says(403, NULL, "vibey hub pair --scope view --scope workflows");
    refusal_says(403, "`migrate` reaches migrations, which the hub never offers",
                 "migrate, budget set");
    refusal_says(422, NULL, "could not take that command line");
    refusal_says(429, "", "Too many requests. Wait a moment");
    refusal_says(502, "GitHub said 404", "GitHub refused the run, or could not be read "
                                         "(the hub said: GitHub said 404)");
    refusal_says(503, "workflows are not enabled on this hub",
                 "Running vibey on GitHub is not enabled on this hub");
    refusal_says(503, NULL, "VIBEY_WORKFLOWS_*");
    refusal_says(404, NULL, "The hub refused it (404)");
    refusal_says(500, "boom", "failed while answering. (the hub said: boom)");
}

static void
test_timeout(void)
{
    g_autoptr(KrWorkflowRun) running =
        parse("{\"request_id\": \"r-1\", \"state\": \"running\", \"url\": \"https://gh/r/7\"}");
    g_autofree char *at_url = kr_workflows_timeout_message(running, KR_WORKFLOWS_LIMIT_SECONDS);
    g_assert_cmpstr(at_url, ==,
                    "krypton stopped following it after 60 minutes; it is still running at "
                    "https://gh/r/7");

    g_autoptr(KrWorkflowRun) queued = parse("{\"request_id\": \"r-1\", \"state\": \"queued\"}");
    g_autofree char *no_url = kr_workflows_timeout_message(queued, 60);
    g_assert_cmpstr(no_url, ==,
                    "krypton stopped following it after 1 minute; it is still queued, and "
                    "GitHub has not shown its run yet. Its request id is r-1.");
    g_autofree char *seconds = kr_workflows_timeout_message(NULL, 90);
    g_assert_cmpstr(seconds, ==, "krypton stopped following it after 90 seconds.");
    g_autofree char *one = kr_workflows_timeout_message(NULL, 1);
    g_assert_cmpstr(one, ==, "krypton stopped following it after 1 second.");
}

static void
test_scope(void)
{
    g_assert_true(kr_workflows_scope_held((const char *const[]){"view", "workflows", NULL}));
    g_assert_false(kr_workflows_scope_held((const char *const[]){"view", "run", NULL}));
    g_assert_false(kr_workflows_scope_held(NULL));
    g_assert_cmpstr(KR_WORKFLOWS_SCOPE, ==, "workflows");
}

/* A run's link reaches the system's URI handler, so only https is kept (security review
 * of ADR-0085): javascript:, file: or a custom scheme from a hub reads as no link at all. */
static void
test_only_an_https_link_is_kept(void)
{
    const char *refused[] = {"javascript:alert(1)", "file:///etc/passwd", "intent://x#Intent;end",
                             "http://github.com/o/r/actions/runs/7", "not a url"};
    for (gsize i = 0; i < G_N_ELEMENTS(refused); i++) {
        g_autofree char *json = g_strdup_printf(
            "{\"request_id\": \"r-12345678\", \"state\": \"running\", \"url\": \"%s\"}",
            refused[i]);
        g_autoptr(KrWorkflowRun) run = parse(json);
        g_assert_null(run->url);
    }
    g_autoptr(KrWorkflowRun) kept = parse(
        "{\"request_id\": \"r-12345678\", \"state\": \"running\", "
        "\"url\": \"HTTPS://github.com/o/r/actions/runs/7\"}");
    g_assert_cmpstr(kept->url, ==, "HTTPS://github.com/o/r/actions/runs/7");
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/workflows/split", test_split);
    g_test_add_func("/workflows/body", test_body);
    g_test_add_func("/workflows/parse-states", test_parse_states);
    g_test_add_func("/workflows/only-https-links", test_only_an_https_link_is_kept);
    g_test_add_func("/workflows/parse-refused", test_parse_refused);
    g_test_add_func("/workflows/summary", test_summary);
    g_test_add_func("/workflows/refusals", test_refusals);
    g_test_add_func("/workflows/timeout", test_timeout);
    g_test_add_func("/workflows/scope", test_scope);
    return g_test_run();
}
