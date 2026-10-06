/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-workflows: a vibey command run on the repository's GitHub-hosted runners.
 *
 * What `vibey -w <command>` does on the command line (ADR-0085), krypton does through the
 * hub (docs/reference/hub-api.json, the `workflows` routes):
 *
 *   - POST /api/v1/workflows/runs with {"argv": ["status", "--json"]} -- the command line
 *     without `vibey` or `-w`, 1 to 200 words -- is answered 202 with the run's first state;
 *   - GET /api/v1/workflows/runs/{request_id} says where it is since:
 *
 *         {"request_id", "state": "queued|running|done|failed", "url", "exit_code",
 *          "stdout", "stderr", "detail"}
 *
 *     `url` is the GitHub run once the forge shows it; `exit_code`, `stdout` and `stderr`
 *     are set when it is `done`; `detail` says why it `failed` (the runner, not the
 *     command, failed).
 *
 * The device needs the `workflows` scope, and the scopes of what the command itself does:
 * the command acts with whatever the runner's database is, so `workflows` alone never lets
 * a device do what its other scopes do not. Some commands (`migrate`, `budget set`) the hub
 * never runs, whatever the device holds.
 *
 * This is the pure half: the typed command line split into words, the request body, the
 * answer read into a KrWorkflowRun, and every refusal said in words. No I/O, no clock. The
 * transport, and the poller that follows a run to its end, are kr-workflows-client.h. */

#ifndef KR_WORKFLOWS_H
#define KR_WORKFLOWS_H

#include <glib.h>

G_BEGIN_DECLS

/* The scope a paired device needs to run anything on the workflows. */
#define KR_WORKFLOWS_SCOPE "workflows"
/* The most words a command line sent to the workflows may hold (WorkflowRunBody). */
#define KR_WORKFLOWS_MAX_WORDS 200
/* How often a run is asked after, and how long krypton follows it before it stops. */
#define KR_WORKFLOWS_POLL_SECONDS 10
#define KR_WORKFLOWS_LIMIT_SECONDS (60 * 60)

#define KR_WORKFLOWS_ERROR (kr_workflows_error_quark())
GQuark kr_workflows_error_quark(void);

typedef enum {
    KR_WORKFLOWS_ERROR_COMMAND,     /* the command line cannot be sent as it stands */
    KR_WORKFLOWS_ERROR_RESPONSE,    /* the hub answered with something that is not a run */
    KR_WORKFLOWS_ERROR_REFUSED,     /* the hub refused: the message says why, and what to do */
    KR_WORKFLOWS_ERROR_UNREACHABLE, /* no hub answered */
    KR_WORKFLOWS_ERROR_FINGERPRINT, /* the hub's certificate is not the one pinned at pairing */
    KR_WORKFLOWS_ERROR_TIMEOUT,     /* still not finished when krypton stopped following it */
} KrWorkflowsError;

typedef enum {
    KR_WORKFLOW_QUEUED,  /* dispatched; GitHub has not shown or started its run yet */
    KR_WORKFLOW_RUNNING, /* on a runner */
    KR_WORKFLOW_DONE,    /* the command ran: its exit code and output are in the run */
    KR_WORKFLOW_FAILED,  /* the run ended without a report: `detail` says why */
} KrWorkflowState;

typedef struct {
    char *request_id;
    KrWorkflowState state;
    char *url;              /* the GitHub run, or NULL until GitHub shows it */
    gboolean has_exit_code; /* set when the command ran */
    gint64 exit_code;
    char *output; /* what the command printed (stdout), or NULL */
    char *errors; /* what it printed to stderr, or NULL */
    char *detail; /* why the run failed, or NULL */
} KrWorkflowRun;

void kr_workflow_run_free(KrWorkflowRun *run);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrWorkflowRun, kr_workflow_run_free)
KrWorkflowRun *kr_workflow_run_copy(const KrWorkflowRun *run);

/* The words of a typed command line. Words are split on whitespace; a double-quoted
 * stretch keeps its spaces ("a b" is one word, --title="a b" is `--title=a b`, "" is an
 * empty word), and inside one \" is a quote and \\ a backslash. A leading `vibey`, and a
 * `-w` or `--workflows` among the options before the command, are dropped: they are how the
 * command is sent, not part of it. NULL with KR_WORKFLOWS_ERROR_COMMAND for nothing to run,
 * an unclosed quote, or more than KR_WORKFLOWS_MAX_WORDS words. */
char **kr_workflows_split(const char *line, GError **error);

/* {"argv": [...]}: the body POST /api/v1/workflows/runs reads. NULL with
 * KR_WORKFLOWS_ERROR_COMMAND for no words or more than KR_WORKFLOWS_MAX_WORDS. */
char *kr_workflows_run_body(const char *const *argv, GError **error);

/* The hub's answer to either route. NULL with KR_WORKFLOWS_ERROR_RESPONSE when it is not
 * JSON, not an object, has no request_id, or names a state krypton does not know. */
KrWorkflowRun *kr_workflow_run_parse(const char *json, gssize length, GError **error);

/* Whether the run has come to an end: done or failed. */
gboolean kr_workflow_run_finished(const KrWorkflowRun *run);

/* The state as the hub names it: "queued", "running", "done", "failed". Static. */
const char *kr_workflow_state_name(KrWorkflowState state);

/* Where the run is, in words for a status row: "Queued: waiting for a GitHub runner",
 * "Done: exit code 0", "Failed: <detail>", ... */
char *kr_workflow_run_summary(const KrWorkflowRun *run);

/* A refusal of either route in words a person can act on; `detail` is the hub's own
 * ({"detail": "..."}), or NULL. A 403 names the `workflows` scope and the reserved
 * commands, a 503 says the hub has the workflows switched off. */
char *kr_workflows_refusal_message(guint status, const char *detail);

/* What is said when krypton stops following a run after `limit_seconds`: it is still
 * going, and where to follow it (its GitHub run, or its request id until it has one). */
char *kr_workflows_timeout_message(const KrWorkflowRun *last, guint limit_seconds);

/* Whether a paired device's scopes let it run commands on the workflows at all. */
gboolean kr_workflows_scope_held(const char *const *scopes);

G_END_DECLS

#endif /* KR_WORKFLOWS_H */
