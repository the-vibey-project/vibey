/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-model: the hub's documents as C structs.
 *
 * Every document the hub returns is the one the matching `vibey ... --json` command prints
 * (docs/reference/hub-api.md, ADR-0068), so these parsers read the same keys the CLI
 * writes. A parser takes the raw bytes of one response body and returns either the model or
 * NULL with a KR_MODEL_ERROR set -- never a half-filled model. Unknown keys are ignored, so
 * a newer hub does not break an older desktop. */

#ifndef KR_MODEL_H
#define KR_MODEL_H

#include <glib.h>

G_BEGIN_DECLS

#define KR_MODEL_ERROR (kr_model_error_quark())
GQuark kr_model_error_quark(void);

typedef enum {
    KR_MODEL_ERROR_PARSE, /* not JSON at all */
    KR_MODEL_ERROR_SHAPE, /* JSON, but not the document this route returns */
} KrModelError;

/* GET /api/v1/projects -- `vibey projects --json`, a top-level array. */
typedef struct {
    char *project_id;
    char *name;
    char *phase;
    char *repo_path;
    gint64 cycle;
    gint64 max_cycles;
    gint64 open_gates;
    gint64 created_at; /* Unix seconds; 0 when absent */
} KrProject;

/* GET /api/v1/gates -- `vibey gates --json`, {"gates": [...]}. */
typedef struct {
    char *gate_id;
    char *project_id;
    char *project_name;
    char *job_id; /* NULL when the gate belongs to no job */
    char *kind;
    char *prompt;
    char **options; /* NULL-terminated; never NULL itself */
    char *default_answer; /* NULL when there is none */
    char *answer_with;    /* the exact `vibey answer` command */
    gint64 raised_at;
    gint64 timeout_at; /* 0 when the gate never times out */
} KrGate;

/* GET /api/v1/lanes -- {"lanes": [...]}, the lanes on the hub's computer. */
typedef struct {
    char *id;
    char *engine;
    char *cwd;
    char *label;
    char *state;   /* running, quiet, finished */
    char *outcome; /* NULL while running */
    gint64 offset; /* the byte position a live view resumes after */
    double last_event_at;
} KrLane;

/* GET /api/v1/projects/{id}/budget -- `vibey budget show --json`. */
typedef struct {
    char *project_id;
    char *name;
    gint64 cycle;
    gboolean has_max_dollars;
    double max_dollars;
    gboolean has_max_turns;
    gint64 max_turns;
    double spent_dollars;
    gint64 spent_turns;
    gboolean exhausted;
} KrBudget;

/* One loop of GET /api/v1/loops -- `vibey loops --json`. */
typedef struct {
    char *loop;
    char *tier;
    gboolean is_default;
    gboolean declared_only;
    char **engine_ids; /* NULL-terminated */
} KrLoop;

typedef struct {
    char *default_loop;
    char **efforts;  /* TRIVIAL ... ULTRA, as the hub lists them */
    GPtrArray *loops; /* of KrLoop, owning */
} KrLoops;

/* GET /api/v1/doctor -- {"scope": ..., "checks": [{"name","mark","detail"}]}. */
typedef struct {
    char *name;
    char *mark; /* PASS, WARN, FAIL, INFO */
    char *detail;
} KrDoctorCheck;

typedef struct {
    char *scope;
    GPtrArray *checks; /* of KrDoctorCheck, owning */
} KrDoctor;

/* Each returns a GPtrArray that owns its elements (free it with g_ptr_array_unref). */
GPtrArray *kr_projects_parse(const char *json, gssize length, GError **error);
GPtrArray *kr_gates_parse(const char *json, gssize length, GError **error);
GPtrArray *kr_lanes_parse(const char *json, gssize length, GError **error);

KrBudget *kr_budget_parse(const char *json, gssize length, GError **error);
KrLoops *kr_loops_parse(const char *json, gssize length, GError **error);
KrDoctor *kr_doctor_parse(const char *json, gssize length, GError **error);

void kr_project_free(KrProject *project);
void kr_gate_free(KrGate *gate);
void kr_lane_free(KrLane *lane);
void kr_budget_free(KrBudget *budget);
void kr_loop_free(KrLoop *loop);
void kr_loops_free(KrLoops *loops);
void kr_doctor_check_free(KrDoctorCheck *check);
void kr_doctor_free(KrDoctor *doctor);

/* A gate whose answer can spend money: answering it needs the `spend` scope as well as
 * `answer` (hub-api.md, "Who may do what"). The UI says so before the person answers. */
gboolean kr_gate_spends(const KrGate *gate);

/* The worst mark among the checks: FAIL over WARN over anything else ("PASS").
 * The returned string is static. */
const char *kr_doctor_worst(const KrDoctor *doctor);

G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrBudget, kr_budget_free)
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrLoops, kr_loops_free)
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrDoctor, kr_doctor_free)

G_END_DECLS

#endif /* KR_MODEL_H */
