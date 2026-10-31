/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-hub-engine: starts, stops and asks after the one vibey hub on this computer (#1186).
 *
 * There is one hub per user, and closing krypton never stops it. The three actions are the
 * CLI's own -- `vibey hub status | start | stop` (src/vibey/cli/hub_engine.py) -- run through
 * GSubprocess with an argument vector (never a shell), from the user's home directory so a
 * vibey.toml in some project folder cannot redirect them. The executable is injectable, so the
 * tests run a script instead of the real engine.
 *
 * Exit codes are the CLI's: status 0 = running (stdout names where), 3 = not running (not an
 * error); start and stop 0 = done. A missing `vibey`, or one old enough to lack `hub`, is an
 * error that names the problem. Nothing here blocks the main loop: the _async forms run the
 * subprocess in a worker thread. */

#ifndef KR_HUB_ENGINE_H
#define KR_HUB_ENGINE_H

#include <gio/gio.h>

G_BEGIN_DECLS

#define KR_HUB_ENGINE_ERROR (kr_hub_engine_error_quark())
GQuark kr_hub_engine_error_quark(void);

typedef enum {
    KR_HUB_ENGINE_ERROR_MISSING, /* no `vibey` to run */
    KR_HUB_ENGINE_ERROR_TOO_OLD, /* `vibey` has no `hub` command */
    KR_HUB_ENGINE_ERROR_FAILED,  /* `vibey hub ...` ran and said no */
    KR_HUB_ENGINE_ERROR_SPAWN,   /* `vibey` could not be run at all */
} KrHubEngineError;

typedef enum {
    KR_HUB_ENGINE_STATUS,
    KR_HUB_ENGINE_START,
    KR_HUB_ENGINE_STOP,
    KR_HUB_ENGINE_ENSURE, /* status, then start only when none runs */
} KrHubEngineAction;

typedef struct {
    gboolean running; /* whether a hub runs now, after the action */
    char *message;    /* one sentence for a status line or a toast */
} KrHubEngineReport;

void kr_hub_engine_report_free(KrHubEngineReport *report);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrHubEngineReport, kr_hub_engine_report_free)

typedef struct KrHubEngine KrHubEngine;

/* `executable`: the vibey to run, or NULL to look for one (kr_hub_engine_locate). `directory`:
 * where to run it, or NULL for the user's home directory. */
KrHubEngine *kr_hub_engine_new(const char *executable, const char *directory);
void kr_hub_engine_free(KrHubEngine *engine);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrHubEngine, kr_hub_engine_free)

/* Where an engine with no executable of its own looks: `home` (NULL: the user's) and the
 * `fallbacks` of kr_hub_engine_locate, which must outlive the engine. For tests. */
void kr_hub_engine_set_search(KrHubEngine *engine, const char *home, const char *const *fallbacks);

/* `vibey` on PATH, then where GUI launches (which have a short PATH) usually miss it:
 * `home`/.local/bin, then `fallbacks` (a NULL-terminated list of full paths; NULL for the
 * defaults, /opt/homebrew/bin/vibey and /usr/local/bin/vibey). NULL when there is none. */
char *kr_hub_engine_locate(const char *home, const char *const *fallbacks);

/* Runs the action and waits (the tests, and the worker thread below). NULL with `error` set
 * on failure. */
KrHubEngineReport *kr_hub_engine_run(KrHubEngine *engine, KrHubEngineAction action,
                                     GCancellable *cancellable, GError **error);

/* The job takes its own copy of the engine, so it may be freed at once (krypton quitting). */
void kr_hub_engine_run_async(KrHubEngine *engine, KrHubEngineAction action,
                             GCancellable *cancellable, GAsyncReadyCallback callback,
                             gpointer data);
KrHubEngineReport *kr_hub_engine_run_finish(GAsyncResult *result, GError **error);

/* What the connection banner says when no hub answers, so a person is told what krypton is
 * doing about it and what they can do, never just to run a command. `host` is the hub
 * krypton is pointed at (NULL: this computer's). */
char *kr_hub_engine_offline_text(const char *host, guint16 port, gboolean autostart);
/* The same, when this computer has no hub token yet (no hub has ever run here). */
char *kr_hub_engine_no_token_text(gboolean autostart);

G_END_DECLS

#endif /* KR_HUB_ENGINE_H */
