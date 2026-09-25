/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-model.h"

/* The documents below are the shapes the CLI's presenters write (src/vibey/cli/projects.py,
 * gates.py, budget.py, serve.py) and the hub returns unchanged. */

static const char PROJECTS[] =
    "[{\"project_id\": \"p-1\", \"name\": \"greeter\", \"phase\": \"BUILD\", \"cycle\": 2,"
    "  \"max_cycles\": 5, \"repo_path\": \"/src/greeter\","
    "  \"created_at\": \"2026-09-25T12:00:00+00:00\", \"open_gates\": 1, \"extra\": true},"
    " {\"project_id\": \"p-2\", \"name\": \"paper\", \"phase\": null, \"cycle\": 1.0}]";

static void
test_projects(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(GPtrArray) projects = kr_projects_parse(PROJECTS, -1, &error);
    g_assert_no_error(error);
    g_assert_cmpuint(projects->len, ==, 2);
    const KrProject *first = g_ptr_array_index(projects, 0);
    g_assert_cmpstr(first->project_id, ==, "p-1");
    g_assert_cmpstr(first->name, ==, "greeter");
    g_assert_cmpstr(first->phase, ==, "BUILD");
    g_assert_cmpstr(first->repo_path, ==, "/src/greeter");
    g_assert_cmpint(first->cycle, ==, 2);
    g_assert_cmpint(first->max_cycles, ==, 5);
    g_assert_cmpint(first->open_gates, ==, 1);
    g_assert_cmpint(first->created_at, ==, 1790337600);
    const KrProject *second = g_ptr_array_index(projects, 1);
    g_assert_null(second->phase);
    g_assert_cmpint(second->cycle, ==, 1);
    g_assert_cmpint(second->created_at, ==, 0);
}

static void
refuses(GPtrArray *(*parse)(const char *, gssize, GError **), const char *json, gint code)
{
    g_autoptr(GError) error = NULL;
    GPtrArray *out = parse(json, -1, &error);
    g_assert_null(out);
    g_assert_error(error, KR_MODEL_ERROR, code);
}

static void
test_refusals(void)
{
    refuses(kr_projects_parse, "not json", KR_MODEL_ERROR_PARSE);
    refuses(kr_projects_parse, "", KR_MODEL_ERROR_PARSE);
    refuses(kr_projects_parse, NULL, KR_MODEL_ERROR_PARSE);
    refuses(kr_projects_parse, "{}", KR_MODEL_ERROR_SHAPE);
    refuses(kr_projects_parse, "[1]", KR_MODEL_ERROR_SHAPE);
    refuses(kr_projects_parse, "[{\"name\": \"x\"}]", KR_MODEL_ERROR_SHAPE);
    refuses(kr_gates_parse, "[]", KR_MODEL_ERROR_SHAPE);
    refuses(kr_gates_parse, "{\"gates\": 3}", KR_MODEL_ERROR_SHAPE);
    refuses(kr_gates_parse, "{\"gates\": [{\"gate_id\": \"g\"}]}", KR_MODEL_ERROR_SHAPE);
    refuses(kr_lanes_parse, "{\"lanes\": [{\"engine\": \"x\"}]}", KR_MODEL_ERROR_SHAPE);
}

static const char GATES[] =
    "{\"gates\": [{\"gate_id\": \"g-1\", \"project_id\": \"p-1\", \"project_name\": \"greeter\","
    "  \"job_id\": null, \"kind\": \"approval\", \"prompt\": \"Accept the review?\","
    "  \"options\": [\"accept\", \"changes\", 3, {\"a\": 1}], \"default_answer\": \"accept\","
    "  \"raised_at\": \"2026-09-25T12:00:00+00:00\", \"timeout_at\": null,"
    "  \"answer_with\": \"vibey answer g-1 --verdict accept\"},"
    " {\"gate_id\": \"g-2\", \"kind\": \"budget_exhausted\", \"job_id\": \"j-9\","
    "  \"default_answer\": {\"max_dollars\": 5}, \"timeout_at\": \"not a time\"}]}";

static void
test_gates(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(GPtrArray) gates = kr_gates_parse(GATES, -1, &error);
    g_assert_no_error(error);
    g_assert_cmpuint(gates->len, ==, 2);
    const KrGate *first = g_ptr_array_index(gates, 0);
    g_assert_cmpstr(first->gate_id, ==, "g-1");
    g_assert_cmpstr(first->project_name, ==, "greeter");
    g_assert_null(first->job_id);
    g_assert_cmpstr(first->prompt, ==, "Accept the review?");
    g_assert_cmpuint(g_strv_length(first->options), ==, 4);
    g_assert_cmpstr(first->options[0], ==, "accept");
    g_assert_cmpstr(first->options[2], ==, "3");
    g_assert_cmpstr(first->options[3], ==, "{\"a\":1}");
    g_assert_cmpstr(first->default_answer, ==, "accept");
    g_assert_cmpint(first->raised_at, ==, 1790337600);
    g_assert_cmpint(first->timeout_at, ==, 0);
    g_assert_false(kr_gate_spends(first));

    const KrGate *second = g_ptr_array_index(gates, 1);
    g_assert_cmpstr(second->job_id, ==, "j-9");
    g_assert_cmpstr(second->default_answer, ==, "{\"max_dollars\":5}");
    g_assert_cmpuint(g_strv_length(second->options), ==, 0);
    g_assert_true(kr_gate_spends(second));

    KrGate deploy = {.kind = "deploy_acceptance"};
    g_assert_true(kr_gate_spends(&deploy));
    KrGate unknown = {.kind = NULL};
    g_assert_false(kr_gate_spends(&unknown));
    g_assert_false(kr_gate_spends(NULL));
}

static const char LANES[] =
    "{\"lanes\": [{\"id\": \"run-1\", \"engine\": \"gptossloop\", \"cwd\": \"/w\","
    "  \"events_path\": \"/w/.qwenloop/runs/run-1/events.jsonl\", \"label\": \"w · gptossloop\","
    "  \"state\": \"running\", \"outcome\": null, \"offset\": 2048, \"last_event_at\": 1790337600.5},"
    " {\"id\": \"run-2\", \"state\": \"finished\", \"outcome\": \"completed\", \"offset\": \"x\"}]}";

static void
test_lanes(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(GPtrArray) lanes = kr_lanes_parse(LANES, -1, &error);
    g_assert_no_error(error);
    g_assert_cmpuint(lanes->len, ==, 2);
    const KrLane *first = g_ptr_array_index(lanes, 0);
    g_assert_cmpstr(first->engine, ==, "gptossloop");
    g_assert_cmpstr(first->label, ==, "w · gptossloop");
    g_assert_null(first->outcome);
    g_assert_cmpint(first->offset, ==, 2048);
    g_assert_cmpfloat(first->last_event_at, ==, 1790337600.5);
    const KrLane *second = g_ptr_array_index(lanes, 1);
    g_assert_cmpstr(second->outcome, ==, "completed");
    g_assert_cmpint(second->offset, ==, 0);
}

static void
test_budget(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrBudget) budget = kr_budget_parse(
        "{\"project_id\": \"p-1\", \"name\": \"greeter\", \"cycle\": 2,"
        " \"caps\": {\"max_cycle_dollars\": 25.5, \"max_cycle_turns\": null},"
        " \"spend\": {\"dollars\": 3.25, \"turns\": 40}, \"exhausted\": true, \"history\": []}",
        -1, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(budget->project_id, ==, "p-1");
    g_assert_cmpstr(budget->name, ==, "greeter");
    g_assert_cmpint(budget->cycle, ==, 2);
    g_assert_true(budget->has_max_dollars);
    g_assert_cmpfloat(budget->max_dollars, ==, 25.5);
    g_assert_false(budget->has_max_turns);
    g_assert_cmpfloat(budget->spent_dollars, ==, 3.25);
    g_assert_cmpint(budget->spent_turns, ==, 40);
    g_assert_true(budget->exhausted);

    g_autoptr(KrBudget) bare = kr_budget_parse("{\"project_id\": \"p\"}", -1, &error);
    g_assert_no_error(error);
    g_assert_false(bare->has_max_dollars);
    g_assert_false(bare->exhausted);

    g_assert_null(kr_budget_parse("[]", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_SHAPE);
    g_clear_error(&error);
    g_assert_null(kr_budget_parse("{\"name\": \"x\"}", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_SHAPE);
    g_clear_error(&error);
    g_assert_null(kr_budget_parse("{", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_PARSE);
}

static void
test_loops_golden(void)
{
    g_autofree char *text = NULL;
    gsize length = 0;
    g_autoptr(GError) error = NULL;
    g_assert_true(g_file_get_contents(KR_LOOPS_GOLDEN, &text, &length, &error));
    g_autoptr(KrLoops) loops = kr_loops_parse(text, (gssize) length, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(loops->default_loop, ==, "sovereignloop");
    g_assert_true(g_strv_contains((const char *const *) loops->efforts, "ULTRA"));
    g_assert_cmpuint(loops->loops->len, >=, 2);
    const KrLoop *first = g_ptr_array_index(loops->loops, 0);
    g_assert_cmpstr(first->loop, ==, "sovereignloop");
    g_assert_cmpstr(first->tier, ==, "local");
    g_assert_true(first->is_default);
    g_assert_false(first->declared_only);
    g_assert_true(g_strv_contains((const char *const *) first->engine_ids, "gptossloop"));
}

static void
test_loops_refusals(void)
{
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_loops_parse("{\"loops\": [{\"tier\": \"local\"}]}", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_SHAPE);
    g_clear_error(&error);
    g_assert_null(kr_loops_parse("{\"loops\": [7]}", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_SHAPE);
    g_clear_error(&error);
    g_assert_null(kr_loops_parse("nope", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_PARSE);
    g_clear_error(&error);
    g_autoptr(KrLoops) odd = kr_loops_parse(
        "{\"loops\": [{\"loop\": \"paidloop\", \"engines\": [3, {\"engine_id\": 4},"
        " {\"engine_id\": \"claudeloop\"}]}]}",
        -1, &error);
    g_assert_no_error(error);
    const KrLoop *loop = g_ptr_array_index(odd->loops, 0);
    g_assert_cmpuint(g_strv_length(loop->engine_ids), ==, 1);
    g_assert_null(odd->default_loop);
}

static void
test_doctor(void)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrDoctor) doctor = kr_doctor_parse(
        "{\"scope\": \"hub\", \"checks\": [{\"name\": \"database\", \"mark\": \"PASS\","
        " \"detail\": \"the database answers\"}, {\"name\": \"hub-exposure\", \"mark\": \"WARN\"}]}",
        -1, &error);
    g_assert_no_error(error);
    g_assert_cmpstr(doctor->scope, ==, "hub");
    g_assert_cmpuint(doctor->checks->len, ==, 2);
    const KrDoctorCheck *check = g_ptr_array_index(doctor->checks, 0);
    g_assert_cmpstr(check->detail, ==, "the database answers");
    g_assert_cmpstr(kr_doctor_worst(doctor), ==, "WARN");

    g_autoptr(KrDoctor) failing = kr_doctor_parse(
        "{\"checks\": [{\"name\": \"a\", \"mark\": \"WARN\"}, {\"name\": \"b\", \"mark\": \"fail\"}]}",
        -1, &error);
    g_assert_no_error(error);
    g_assert_null(failing->scope);
    g_assert_cmpstr(kr_doctor_worst(failing), ==, "FAIL");

    g_autoptr(KrDoctor) clean = kr_doctor_parse("{\"checks\": []}", -1, &error);
    g_assert_cmpstr(kr_doctor_worst(clean), ==, "PASS");
    g_assert_cmpstr(kr_doctor_worst(NULL), ==, "PASS");

    g_assert_null(kr_doctor_parse("{\"checks\": [{\"name\": \"a\"}]}", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_SHAPE);
    g_clear_error(&error);
    g_assert_null(kr_doctor_parse("{\"checks\": [1]}", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_SHAPE);
    g_clear_error(&error);
    g_assert_null(kr_doctor_parse("[", -1, &error));
    g_assert_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_PARSE);
}

static void
test_free_null(void)
{
    kr_project_free(NULL);
    kr_gate_free(NULL);
    kr_lane_free(NULL);
    kr_budget_free(NULL);
    kr_loop_free(NULL);
    kr_loops_free(NULL);
    kr_doctor_check_free(NULL);
    kr_doctor_free(NULL);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/model/projects", test_projects);
    g_test_add_func("/model/refusals", test_refusals);
    g_test_add_func("/model/gates", test_gates);
    g_test_add_func("/model/lanes", test_lanes);
    g_test_add_func("/model/budget", test_budget);
    g_test_add_func("/model/loops-golden", test_loops_golden);
    g_test_add_func("/model/loops-refusals", test_loops_refusals);
    g_test_add_func("/model/doctor", test_doctor);
    g_test_add_func("/model/free-null", test_free_null);
    return g_test_run();
}
