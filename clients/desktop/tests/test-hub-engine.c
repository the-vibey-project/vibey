/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-hub-engine: start, stop and status of the one hub, through a script that stands in for
 * `vibey` so no test ever starts a real hub. */
#include <glib/gstdio.h>
#include <string.h>

#include "kr-hub-engine.h"

/* The stand-in `vibey`. Its behaviour is chosen by marker files beside it. */
static const char FAKE[] =
    "#!/bin/sh\n"
    "dir=$(dirname \"$0\")\n"
    "echo \"$(pwd -P) $1 $2\" >> \"$dir/calls\"\n"
    "[ -f \"$dir/old\" ] && { echo \"Error: No such command 'hub'.\" >&2; exit 2; }\n"
    "[ -f \"$dir/crash\" ] && { echo boom >&2; exit 1; }\n"
    "[ -f \"$dir/kill\" ] && kill -9 $$\n"
    "[ -f \"$dir/slow\" ] && sleep 30\n"
    "case \"$2\" in\n"
    "status) if [ -f \"$dir/running\" ]; then echo 'http://127.0.0.1:8765/api/v1 (pid 7)'; "
    "else exit 3; fi ;;\n"
    "start) touch \"$dir/running\"; [ -f \"$dir/quiet\" ] || echo 'hub is not running'; "
    "[ -f \"$dir/quiet\" ] || "
    "echo 'hub started: http://127.0.0.1:8765/api/v1 (pid 7)' ;;\n"
    "stop) rm -f \"$dir/running\"; [ -f \"$dir/quiet\" ] || echo 'hub stopped (pid 7)' ;;\n"
    "esac\n";

typedef struct {
    char *dir;
    char *vibey;
    KrHubEngine *engine;
} Fixture;

static Fixture *
fixture_new(void)
{
    Fixture *fx = g_new0(Fixture, 1);
    fx->dir = g_dir_make_tmp("krypton-hub-engine-XXXXXX", NULL);
    fx->vibey = g_build_filename(fx->dir, "vibey", NULL);
    g_assert_true(g_file_set_contents(fx->vibey, FAKE, -1, NULL));
    g_assert_cmpint(g_chmod(fx->vibey, 0700), ==, 0);
    fx->engine = kr_hub_engine_new(fx->vibey, fx->dir);
    return fx;
}

static void
mark(Fixture *fx, const char *name, gboolean on)
{
    g_autofree char *path = g_build_filename(fx->dir, name, NULL);
    if (on)
        g_assert_true(g_file_set_contents(path, "", 0, NULL));
    else
        g_unlink(path);
}

static char *
calls(Fixture *fx)
{
    g_autofree char *path = g_build_filename(fx->dir, "calls", NULL);
    char *text = NULL;
    if (!g_file_get_contents(path, &text, NULL, NULL))
        return g_strdup("");
    return text;
}

static void
fixture_free(Fixture *fx)
{
    const char *names[] = {"vibey", "calls", "running", "old", "crash", "kill", "slow", "quiet"};
    for (guint i = 0; i < G_N_ELEMENTS(names); i++)
        mark(fx, names[i], FALSE);
    g_rmdir(fx->dir);
    kr_hub_engine_free(fx->engine);
    g_free(fx->vibey);
    g_free(fx->dir);
    g_free(fx);
}

static KrHubEngineReport *
run(Fixture *fx, KrHubEngineAction action)
{
    g_autoptr(GError) error = NULL;
    KrHubEngineReport *report = kr_hub_engine_run(fx->engine, action, NULL, &error);
    g_assert_no_error(error);
    g_assert_nonnull(report);
    return report;
}

static void
test_status_says_whether_a_hub_runs(void)
{
    Fixture *fx = fixture_new();
    g_autoptr(KrHubEngineReport) none = run(fx, KR_HUB_ENGINE_STATUS);
    g_assert_false(none->running);
    g_assert_cmpstr(none->message, ==, "No hub is running on this computer.");

    mark(fx, "running", TRUE);
    g_autoptr(KrHubEngineReport) up = run(fx, KR_HUB_ENGINE_STATUS);
    g_assert_true(up->running);
    g_assert_cmpstr(up->message, ==, "The hub is running at http://127.0.0.1:8765/api/v1 (pid 7).");
    fixture_free(fx);
}

static void
test_start_and_stop_follow_the_cli(void)
{
    Fixture *fx = fixture_new();
    g_autoptr(KrHubEngineReport) started = run(fx, KR_HUB_ENGINE_START);
    g_assert_true(started->running);
    g_assert_cmpstr(started->message, ==, "hub started: http://127.0.0.1:8765/api/v1 (pid 7)");
    g_autoptr(KrHubEngineReport) up = run(fx, KR_HUB_ENGINE_STATUS);
    g_assert_true(up->running);

    g_autoptr(KrHubEngineReport) stopped = run(fx, KR_HUB_ENGINE_STOP);
    g_assert_false(stopped->running);
    g_assert_cmpstr(stopped->message, ==, "hub stopped (pid 7)");
    g_autoptr(KrHubEngineReport) down = run(fx, KR_HUB_ENGINE_STATUS);
    g_assert_false(down->running);
    fixture_free(fx);
}

static void
test_a_quiet_cli_still_gets_a_sentence(void)
{
    Fixture *fx = fixture_new();
    mark(fx, "quiet", TRUE);
    g_autoptr(KrHubEngineReport) started = run(fx, KR_HUB_ENGINE_START);
    g_assert_cmpstr(started->message, ==, "The hub is running.");
    g_autoptr(KrHubEngineReport) stopped = run(fx, KR_HUB_ENGINE_STOP);
    g_assert_cmpstr(stopped->message, ==, "The hub is stopped.");
    fixture_free(fx);
}

static void
test_ensure_starts_a_hub_only_when_none_runs(void)
{
    Fixture *fx = fixture_new();
    g_autoptr(KrHubEngineReport) first = run(fx, KR_HUB_ENGINE_ENSURE);
    g_assert_true(first->running);
    g_autofree char *after_first = calls(fx);
    g_assert_nonnull(strstr(after_first, "hub status"));
    g_assert_nonnull(strstr(after_first, "hub start"));

    g_autoptr(KrHubEngineReport) second = run(fx, KR_HUB_ENGINE_ENSURE);
    g_assert_true(second->running);
    g_autofree char *after_second = calls(fx);
    /* The second ensure asked, and did not start a second hub: one start in all. */
    gchar **lines = g_strsplit(after_second, "\n", -1);
    guint starts = 0;
    for (guint i = 0; lines[i] != NULL; i++)
        if (g_str_has_suffix(lines[i], "hub start"))
            starts++;
    g_assert_cmpuint(starts, ==, 1);
    g_strfreev(lines);
    fixture_free(fx);
}

static void
test_it_runs_from_the_directory_it_was_given(void)
{
    Fixture *fx = fixture_new();
    g_autoptr(KrHubEngineReport) report = run(fx, KR_HUB_ENGINE_STATUS);
    g_autofree char *text = calls(fx);
    g_autofree char *leaf = g_path_get_basename(fx->dir);
    g_assert_nonnull(strstr(text, leaf));

    /* With no directory it is the user's home, never the process's own. */
    g_autoptr(KrHubEngine) home = kr_hub_engine_new(fx->vibey, NULL);
    g_autoptr(GError) error = NULL;
    g_autoptr(KrHubEngineReport) again = kr_hub_engine_run(home, KR_HUB_ENGINE_STATUS, NULL, &error);
    g_assert_no_error(error);
    g_autofree char *after = calls(fx);
    g_autofree char *home_leaf = g_path_get_basename(g_get_home_dir());
    g_assert_nonnull(strstr(after, home_leaf));
    fixture_free(fx);
}

static void
expect_failure(Fixture *fx, KrHubEngineAction action, KrHubEngineError code, const char *text)
{
    g_autoptr(GError) error = NULL;
    KrHubEngineReport *report = kr_hub_engine_run(fx->engine, action, NULL, &error);
    g_assert_null(report);
    g_assert_error(error, KR_HUB_ENGINE_ERROR, (int) code);
    g_assert_nonnull(strstr(error->message, text));
}

static void
test_failures_name_the_problem(void)
{
    Fixture *fx = fixture_new();
    mark(fx, "old", TRUE);
    expect_failure(fx, KR_HUB_ENGINE_STATUS, KR_HUB_ENGINE_ERROR_TOO_OLD, "too old");
    expect_failure(fx, KR_HUB_ENGINE_START, KR_HUB_ENGINE_ERROR_TOO_OLD, "pip install -U");
    mark(fx, "old", FALSE);

    mark(fx, "crash", TRUE);
    expect_failure(fx, KR_HUB_ENGINE_STATUS, KR_HUB_ENGINE_ERROR_FAILED, "boom");
    expect_failure(fx, KR_HUB_ENGINE_START, KR_HUB_ENGINE_ERROR_FAILED, "`vibey hub start` failed (exit 1): boom");
    expect_failure(fx, KR_HUB_ENGINE_STOP, KR_HUB_ENGINE_ERROR_FAILED, "`vibey hub stop`");
    /* ensure never starts a hub it could not even ask after. */
    expect_failure(fx, KR_HUB_ENGINE_ENSURE, KR_HUB_ENGINE_ERROR_FAILED, "`vibey hub status`");
    mark(fx, "crash", FALSE);

    mark(fx, "kill", TRUE);
    expect_failure(fx, KR_HUB_ENGINE_STATUS, KR_HUB_ENGINE_ERROR_FAILED, "(exit -1).");
    fixture_free(fx);
}

static void
test_a_vibey_that_cannot_run_is_a_spawn_error(void)
{
    g_autoptr(KrHubEngine) engine = kr_hub_engine_new("/nonexistent/krypton/vibey", NULL);
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_hub_engine_run(engine, KR_HUB_ENGINE_STATUS, NULL, &error));
    g_assert_error(error, KR_HUB_ENGINE_ERROR, KR_HUB_ENGINE_ERROR_SPAWN);
}

typedef struct {
    GMainLoop *loop;
    KrHubEngineReport *report;
    GError *error;
} Waiting;

static void
on_done(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Waiting *waiting = data;
    waiting->report = kr_hub_engine_run_finish(result, &waiting->error);
    g_main_loop_quit(waiting->loop);
}

static const char *const none[] = {NULL};

static void
test_locating_vibey(void)
{
    g_autofree char *dir = g_dir_make_tmp("krypton-hub-locate-XXXXXX", NULL);
    g_autofree char *bin = g_build_filename(dir, ".local", "bin", NULL);
    g_assert_cmpint(g_mkdir_with_parents(bin, 0700), ==, 0);
    g_autofree char *vibey = g_build_filename(bin, "vibey", NULL);
    g_autofree char *empty = g_build_filename(dir, "empty", NULL);
    g_assert_cmpint(g_mkdir_with_parents(empty, 0700), ==, 0);

    g_autofree char *saved = g_strdup(g_getenv("PATH"));
    g_setenv("PATH", empty, TRUE);

    /* A directory of that name is not an executable. */
    g_assert_cmpint(g_mkdir(vibey, 0700), ==, 0);
    g_autofree char *dir_only = kr_hub_engine_locate(dir, none);
    g_assert_true(dir_only == NULL || !g_str_has_prefix(dir_only, dir));
    g_rmdir(vibey);

    g_assert_true(g_file_set_contents(vibey, FAKE, -1, NULL));
    g_assert_cmpint(g_chmod(vibey, 0700), ==, 0);
    g_autofree char *local = kr_hub_engine_locate(dir, none);
    g_assert_cmpstr(local, ==, vibey);

    /* PATH wins when it has one. */
    g_autofree char *on_path = g_build_filename(empty, "vibey", NULL);
    g_assert_true(g_file_set_contents(on_path, FAKE, -1, NULL));
    g_assert_cmpint(g_chmod(on_path, 0700), ==, 0);
    g_autofree char *found = kr_hub_engine_locate(dir, none);
    g_assert_cmpstr(found, ==, on_path);

    /* The fallbacks come last: with nothing on PATH and nothing under home, the first that is
     * a program wins. */
    g_setenv("PATH", "/nonexistent-krypton-path", TRUE);
    const char *const extra[] = {"/nonexistent/vibey", on_path, NULL};
    g_autofree char *fallback = kr_hub_engine_locate("/nonexistent-home", extra);
    g_assert_cmpstr(fallback, ==, on_path);

    if (saved != NULL)
        g_setenv("PATH", saved, TRUE);
    g_unlink(on_path);
    g_unlink(vibey);
    g_rmdir(empty);
    g_rmdir(bin);
    g_autofree char *dot_local = g_build_filename(dir, ".local", NULL);
    g_rmdir(dot_local);
    g_rmdir(dir);
}

static void
test_no_vibey_at_all_is_said_plainly(void)
{
    g_autofree char *dir = g_dir_make_tmp("krypton-hub-none-XXXXXX", NULL);
    g_autofree char *saved = g_strdup(g_getenv("PATH"));
    g_setenv("PATH", dir, TRUE);
    g_autofree char *located = kr_hub_engine_locate(dir, none);
    g_assert_null(located);
    /* The defaults are tried too; only their existence on this machine varies. */
    g_autofree char *with_defaults = kr_hub_engine_locate(dir, NULL);
    g_assert_true(with_defaults == NULL || g_str_has_suffix(with_defaults, "/vibey"));

    /* An engine with no vibey of its own looks where it is told, and says plainly when there
     * is none. (Told to look nowhere real, so this never runs a vibey of the machine's own.) */
    g_autoptr(KrHubEngine) engine = kr_hub_engine_new(NULL, NULL);
    kr_hub_engine_set_search(engine, dir, none);
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_hub_engine_run(engine, KR_HUB_ENGINE_STATUS, NULL, &error));
    g_assert_error(error, KR_HUB_ENGINE_ERROR, KR_HUB_ENGINE_ERROR_MISSING);
    g_assert_nonnull(strstr(error->message, "pip install vibey-engine"));

    /* ...and the same lookup finds one that is there, and runs it, from an async job too. */
    g_autofree char *bin = g_build_filename(dir, ".local", "bin", NULL);
    g_assert_cmpint(g_mkdir_with_parents(bin, 0700), ==, 0);
    g_autofree char *vibey = g_build_filename(bin, "vibey", NULL);
    g_assert_true(g_file_set_contents(vibey, FAKE, -1, NULL));
    g_assert_cmpint(g_chmod(vibey, 0700), ==, 0);
    Waiting waiting = {.loop = g_main_loop_new(NULL, FALSE)};
    kr_hub_engine_run_async(engine, KR_HUB_ENGINE_STATUS, NULL, on_done, &waiting);
    g_main_loop_run(waiting.loop);
    g_assert_no_error(waiting.error);
    g_assert_false(waiting.report->running);
    kr_hub_engine_report_free(waiting.report);
    g_main_loop_unref(waiting.loop);
    g_unlink(vibey);
    g_autofree char *calls_file = g_build_filename(bin, "calls", NULL);
    g_unlink(calls_file);
    g_rmdir(bin);
    g_autofree char *dot_local = g_build_filename(dir, ".local", NULL);
    g_rmdir(dot_local);
    if (saved != NULL)
        g_setenv("PATH", saved, TRUE);
    g_rmdir(dir);
}

static void
test_async_does_not_block_and_reports(void)
{
    Fixture *fx = fixture_new();
    Waiting waiting = {.loop = g_main_loop_new(NULL, FALSE)};
    kr_hub_engine_run_async(fx->engine, KR_HUB_ENGINE_ENSURE, NULL, on_done, &waiting);
    g_main_loop_run(waiting.loop);
    g_assert_no_error(waiting.error);
    g_assert_true(waiting.report->running);
    kr_hub_engine_report_free(waiting.report);

    waiting.report = NULL;
    mark(fx, "crash", TRUE);
    kr_hub_engine_run_async(fx->engine, KR_HUB_ENGINE_STOP, NULL, on_done, &waiting);
    g_main_loop_run(waiting.loop);
    g_assert_null(waiting.report);
    g_assert_error(waiting.error, KR_HUB_ENGINE_ERROR, KR_HUB_ENGINE_ERROR_FAILED);
    g_clear_error(&waiting.error);
    g_main_loop_unref(waiting.loop);
    fixture_free(fx);
}

static gboolean
cancel_now(gpointer data)
{
    g_cancellable_cancel(data);
    return G_SOURCE_REMOVE;
}

static void
test_cancelling_ends_a_slow_hub_command(void)
{
    Fixture *fx = fixture_new();
    mark(fx, "slow", TRUE);
    g_autoptr(GCancellable) cancel = g_cancellable_new();
    Waiting waiting = {.loop = g_main_loop_new(NULL, FALSE)};
    kr_hub_engine_run_async(fx->engine, KR_HUB_ENGINE_START, cancel, on_done, &waiting);
    g_timeout_add(200, cancel_now, cancel);
    g_main_loop_run(waiting.loop);
    g_assert_null(waiting.report);
    g_assert_error(waiting.error, G_IO_ERROR, G_IO_ERROR_CANCELLED);
    g_clear_error(&waiting.error);
    g_main_loop_unref(waiting.loop);
    fixture_free(fx);
}

static void
test_the_banner_says_what_krypton_does_and_what_a_person_can(void)
{
    g_autofree char *auto_on = kr_hub_engine_offline_text(NULL, 0, TRUE);
    g_assert_nonnull(strstr(auto_on, "krypton starts it for you"));
    g_assert_nonnull(strstr(auto_on, "Start the hub"));
    g_autofree char *auto_off = kr_hub_engine_offline_text(NULL, 0, FALSE);
    g_assert_nonnull(strstr(auto_off, "automatically in Settings"));
    g_autofree char *elsewhere = kr_hub_engine_offline_text("studio.local", 8765, TRUE);
    g_assert_nonnull(strstr(elsewhere, "studio.local:8765"));
    g_assert_nonnull(strstr(elsewhere, "vibey hub start"));
    g_assert_null(strstr(elsewhere, "krypton starts it"));

    g_autofree char *waiting = kr_hub_engine_no_token_text(TRUE);
    g_assert_nonnull(strstr(waiting, "krypton is starting it"));
    g_autofree char *manual = kr_hub_engine_no_token_text(FALSE);
    g_assert_nonnull(strstr(manual, "Start the hub"));
}

/* The text of the function named `name` in main.c, from its definition to the closing brace. */
static char *
function_body(const char *source, const char *name)
{
    g_autofree char *needle = g_strdup_printf("\n%s(", name);
    const char *start = strstr(source, needle);
    g_assert_nonnull(start);
    const char *end = strstr(start, "\n}\n");
    g_assert_nonnull(end);
    return g_strndup(start, (gsize) (end - start));
}

/* Ruling 2 (#1186): closing a UI never stops the hub. The GTK layer cannot be run here, so the
 * paths krypton leaves by -- quitting, the application's shutdown, a window closing -- are read
 * and must not name the stop action. Stop is reachable only from its own action. */
static void
test_no_way_out_of_krypton_stops_the_hub(void)
{
    g_autofree char *path = g_build_filename(g_getenv("G_TEST_SRCDIR"), "..", "src", "app", "main.c", NULL);
    g_autofree char *source = NULL;
    g_assert_true(g_file_get_contents(path, &source, NULL, NULL));
    const char *leaving[] = {"action_quit", "on_shutdown", "stop_tray"};
    for (guint i = 0; i < G_N_ELEMENTS(leaving); i++) {
        g_autofree char *body = function_body(source, leaving[i]);
        g_assert_null(strstr(body, "KR_HUB_ENGINE_STOP"));
        g_assert_null(strstr(body, "stop-hub"));
        g_assert_null(strstr(body, "kr_app_hub_stop"));
    }
    g_autofree char *window_path = g_build_filename(g_getenv("G_TEST_SRCDIR"), "..", "src", "app", "kr-window.c", NULL);
    g_autofree char *window = NULL;
    g_assert_true(g_file_get_contents(window_path, &window, NULL, NULL));
    g_autofree char *closing = function_body(window, "on_close_request");
    g_assert_null(strstr(closing, "kr_app_hub_stop"));
    /* And stop is wired to exactly one thing: its own action. */
    g_assert_nonnull(strstr(source, "action_stop_hub"));
}

static void
test_freeing_nothing_is_fine(void)
{
    kr_hub_engine_report_free(NULL);
    kr_hub_engine_free(NULL);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/hub-engine/status", test_status_says_whether_a_hub_runs);
    g_test_add_func("/hub-engine/start-stop", test_start_and_stop_follow_the_cli);
    g_test_add_func("/hub-engine/quiet", test_a_quiet_cli_still_gets_a_sentence);
    g_test_add_func("/hub-engine/ensure", test_ensure_starts_a_hub_only_when_none_runs);
    g_test_add_func("/hub-engine/directory", test_it_runs_from_the_directory_it_was_given);
    g_test_add_func("/hub-engine/failures", test_failures_name_the_problem);
    g_test_add_func("/hub-engine/spawn", test_a_vibey_that_cannot_run_is_a_spawn_error);
    g_test_add_func("/hub-engine/locate", test_locating_vibey);
    g_test_add_func("/hub-engine/missing", test_no_vibey_at_all_is_said_plainly);
    g_test_add_func("/hub-engine/async", test_async_does_not_block_and_reports);
    g_test_add_func("/hub-engine/cancel", test_cancelling_ends_a_slow_hub_command);
    g_test_add_func("/hub-engine/banner", test_the_banner_says_what_krypton_does_and_what_a_person_can);
    g_test_add_func("/hub-engine/quit-never-stops", test_no_way_out_of_krypton_stops_the_hub);
    g_test_add_func("/hub-engine/free", test_freeing_nothing_is_fine);
    return g_test_run();
}
