/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-hub-engine.h"

#include <string.h>

#define EXIT_NOT_RUNNING 3

G_DEFINE_QUARK(kr-hub-engine-error-quark, kr_hub_engine_error)

struct KrHubEngine {
    char *executable;
    char *directory;
    char *search_home;
    const char *const *fallbacks;
};

void
kr_hub_engine_report_free(KrHubEngineReport *report)
{
    if (report == NULL)
        return;
    g_free(report->message);
    g_free(report);
}

static KrHubEngineReport *
report_new(gboolean running, char *message)
{
    KrHubEngineReport *report = g_new0(KrHubEngineReport, 1);
    report->running = running;
    report->message = message;
    return report;
}

KrHubEngine *
kr_hub_engine_new(const char *executable, const char *directory)
{
    KrHubEngine *engine = g_new0(KrHubEngine, 1);
    engine->executable = g_strdup(executable);
    engine->directory = g_strdup(directory != NULL ? directory : g_get_home_dir());
    engine->search_home = g_strdup(g_get_home_dir());
    return engine;
}

void
kr_hub_engine_free(KrHubEngine *engine)
{
    if (engine == NULL)
        return;
    g_free(engine->executable);
    g_free(engine->directory);
    g_free(engine->search_home);
    g_free(engine);
}

static gboolean
is_program(const char *path)
{
    return g_file_test(path, G_FILE_TEST_IS_EXECUTABLE) && !g_file_test(path, G_FILE_TEST_IS_DIR);
}

void
kr_hub_engine_set_search(KrHubEngine *engine, const char *home, const char *const *fallbacks)
{
    g_free(engine->search_home);
    engine->search_home = g_strdup(home != NULL ? home : g_get_home_dir());
    engine->fallbacks = fallbacks;
}

char *
kr_hub_engine_locate(const char *home, const char *const *fallbacks)
{
    static const char *const defaults[] = {"/opt/homebrew/bin/vibey", "/usr/local/bin/vibey", NULL};
    char *found = g_find_program_in_path("vibey");
    if (found != NULL)
        return found;
    g_autofree char *local = g_build_filename(home, ".local", "bin", "vibey", NULL);
    if (is_program(local))
        return g_steal_pointer(&local);
    for (const char *const *path = fallbacks != NULL ? fallbacks : defaults; *path != NULL; path++) {
        if (is_program(*path))
            return g_strdup(*path);
    }
    return NULL;
}

/* One `vibey hub <verb>`. FALSE with `error` when it could not be run; otherwise the exit
 * status, and stdout and stderr (trimmed), are filled in. */
static gboolean
run_hub(KrHubEngine *engine, const char *verb, GCancellable *cancellable, int *status, char **out,
        char **err, GError **error)
{
    g_autofree char *executable = engine->executable != NULL
                                      ? g_strdup(engine->executable)
                                      : kr_hub_engine_locate(engine->search_home, engine->fallbacks);
    if (executable == NULL) {
        g_set_error_literal(error, KR_HUB_ENGINE_ERROR, KR_HUB_ENGINE_ERROR_MISSING,
                            "krypton cannot find the vibey command to manage the hub. Install it "
                            "(pip install vibey-engine) and put it on your PATH.");
        return FALSE;
    }
    g_autoptr(GSubprocessLauncher) launcher = g_subprocess_launcher_new(
        G_SUBPROCESS_FLAGS_STDOUT_PIPE | G_SUBPROCESS_FLAGS_STDERR_PIPE);
    g_subprocess_launcher_set_cwd(launcher, engine->directory);
    g_autoptr(GError) spawn_error = NULL;
    g_autoptr(GSubprocess) process =
        g_subprocess_launcher_spawn(launcher, &spawn_error, executable, "hub", verb, NULL);
    if (process == NULL) {
        g_set_error(error, KR_HUB_ENGINE_ERROR, KR_HUB_ENGINE_ERROR_SPAWN,
                    "krypton could not run %s: %s", executable, spawn_error->message);
        return FALSE;
    }
    g_autoptr(GError) wait_error = NULL;
    if (!g_subprocess_communicate_utf8(process, NULL, cancellable, out, err, &wait_error)) {
        g_subprocess_force_exit(process);
        g_propagate_error(error, g_steal_pointer(&wait_error));
        return FALSE;
    }
    *status = g_subprocess_get_if_exited(process) ? g_subprocess_get_exit_status(process) : -1;
    g_strstrip(*out);
    g_strstrip(*err);
    return TRUE;
}

/* The words for a `vibey hub` that said no. */
static void
set_failure(GError **error, const char *verb, int status, const char *detail)
{
    if (strstr(detail, "No such command") != NULL) {
        g_set_error_literal(error, KR_HUB_ENGINE_ERROR, KR_HUB_ENGINE_ERROR_TOO_OLD,
                            "This vibey is too old to manage the hub. Upgrade it: pip install -U "
                            "vibey-engine");
        return;
    }
    g_set_error(error, KR_HUB_ENGINE_ERROR, KR_HUB_ENGINE_ERROR_FAILED,
                "`vibey hub %s` failed (exit %d)%s%s", verb, status, *detail != '\0' ? ": " : ".",
                detail);
}

static KrHubEngineReport *
status_report(KrHubEngine *engine, GCancellable *cancellable, GError **error)
{
    int status = 0;
    g_autofree char *out = NULL;
    g_autofree char *err = NULL;
    if (!run_hub(engine, "status", cancellable, &status, &out, &err, error))
        return NULL;
    if (status == 0)
        return report_new(TRUE, g_strdup_printf("The hub is running at %s.", out));
    if (status == EXIT_NOT_RUNNING)
        return report_new(FALSE, g_strdup("No hub is running on this computer."));
    set_failure(error, "status", status, err);
    return NULL;
}

/* start and stop share a shape: exit 0 is done, and stdout says how. */
static KrHubEngineReport *
verb_report(KrHubEngine *engine, const char *verb, gboolean running_after, const char *fallback,
            GCancellable *cancellable, GError **error)
{
    int status = 0;
    g_autofree char *out = NULL;
    g_autofree char *err = NULL;
    if (!run_hub(engine, verb, cancellable, &status, &out, &err, error))
        return NULL;
    if (status != 0) {
        set_failure(error, verb, status, err);
        return NULL;
    }
    /* `start` first says "hub is not running" when it begins: the sentence that matters is the
     * last line. */
    const char *last = strrchr(out, '\n');
    last = last != NULL ? last + 1 : out;
    return report_new(running_after, g_strdup(*last != '\0' ? last : fallback));
}

KrHubEngineReport *
kr_hub_engine_run(KrHubEngine *engine, KrHubEngineAction action, GCancellable *cancellable,
                  GError **error)
{
    switch (action) {
    case KR_HUB_ENGINE_STATUS:
        return status_report(engine, cancellable, error);
    case KR_HUB_ENGINE_START:
        return verb_report(engine, "start", TRUE, "The hub is running.", cancellable, error);
    case KR_HUB_ENGINE_STOP:
        return verb_report(engine, "stop", FALSE, "The hub is stopped.", cancellable, error);
    case KR_HUB_ENGINE_ENSURE:
    default: {
        KrHubEngineReport *report = status_report(engine, cancellable, error);
        if (report == NULL || report->running)
            return report;
        kr_hub_engine_report_free(report);
        return verb_report(engine, "start", TRUE, "The hub is running.", cancellable, error);
    }
    }
}

typedef struct {
    KrHubEngine *engine; /* the job's own copy */
    KrHubEngineAction action;
} Job;

static void
job_free(Job *job)
{
    kr_hub_engine_free(job->engine);
    g_free(job);
}

static void
run_in_thread(GTask *task, gpointer source, gpointer task_data, GCancellable *cancellable)
{
    (void) source;
    Job *job = task_data;
    GError *error = NULL;
    KrHubEngineReport *report = kr_hub_engine_run(job->engine, job->action, cancellable, &error);
    if (report == NULL)
        g_task_return_error(task, error);
    else
        g_task_return_pointer(task, report, (GDestroyNotify) kr_hub_engine_report_free);
}

void
kr_hub_engine_run_async(KrHubEngine *engine, KrHubEngineAction action, GCancellable *cancellable,
                        GAsyncReadyCallback callback, gpointer data)
{
    GTask *task = g_task_new(NULL, cancellable, callback, data);
    Job *job = g_new0(Job, 1);
    job->engine = kr_hub_engine_new(engine->executable, engine->directory);
    kr_hub_engine_set_search(job->engine, engine->search_home, engine->fallbacks);
    job->action = action;
    g_task_set_task_data(task, job, (GDestroyNotify) job_free);
    g_task_run_in_thread(task, run_in_thread);
    g_object_unref(task);
}

KrHubEngineReport *
kr_hub_engine_run_finish(GAsyncResult *result, GError **error)
{
    return g_task_propagate_pointer(G_TASK(result), error);
}

char *
kr_hub_engine_offline_text(const char *host, guint16 port, gboolean autostart)
{
    if (host != NULL)
        return g_strdup_printf("No hub answers at %s:%u. It is on another computer: start it "
                               "there with `vibey hub start`.",
                               host, port);
    return g_strdup(autostart ? "No hub answers on this computer. krypton starts it for you; "
                                "choose Start the hub to try again."
                              : "No hub answers on this computer. Choose Start the hub, or "
                                "turn on starting it automatically in Settings.");
}

char *
kr_hub_engine_no_token_text(gboolean autostart)
{
    return g_strdup(autostart ? "No hub has run on this computer yet. krypton is starting it."
                              : "No hub has run on this computer yet. Choose Start the hub.");
}
