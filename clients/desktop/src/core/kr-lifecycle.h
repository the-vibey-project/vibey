/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-lifecycle: starting, pausing, resuming and unwinding a project from a device (ADR-0091).
 *
 * The pure half: the name a project may have, the bodies the four routes take, the documents
 * they answer with, and the words that stand between a person and an unwind. A device never
 * names a path; the host makes the folder, so there is none to build here. The transport is
 * kr-hub-client.h. */

#ifndef KR_LIFECYCLE_H
#define KR_LIFECYCLE_H

#include <glib.h>

G_BEGIN_DECLS

#define KR_LIFECYCLE_ERROR (kr_lifecycle_error_quark())
GQuark kr_lifecycle_error_quark(void);

typedef enum {
    KR_LIFECYCLE_ERROR_INVALID, /* what the person typed breaks a rule the hub also holds */
    KR_LIFECYCLE_ERROR_ANSWER,  /* the hub answered with something that is not the document */
} KrLifecycleError;

/* The most characters of "what to build" and of a reason the hub reads (hub_service.py). */
#define KR_LIFECYCLE_MAX_INTAKE 4000
#define KR_LIFECYCLE_MAX_REASON 500

/* Why `name` will not do, in words (static), or NULL when it will: letters, digits, dots,
 * dashes and underscores, starting with a letter or digit, at most 64. Said before the hub
 * is asked, so a typo costs no round trip. Surrounding spaces are not part of the name. */
const char *kr_lifecycle_name_problem(const char *name);

/* `POST /api/v1/projects`'s body: {"name": ..., "intake": ...} (intake left out when empty).
 * NULL with KR_LIFECYCLE_ERROR_INVALID when the name or the intake breaks a rule. */
char *kr_lifecycle_start_body(const char *name, const char *intake, GError **error);

/* `POST /api/v1/projects/{id}/abandon`'s body: {"reason": ..., "dry_run": ...}. NULL with
 * KR_LIFECYCLE_ERROR_INVALID when the reason is empty or too long. */
char *kr_lifecycle_abandon_body(const char *reason, gboolean dry_run, GError **error);

typedef struct {
    char *project_id;
    char *name;
    char *outcome; /* vibey's own line: "design job <id>" */
} KrCreated;

/* `vibey new --json`'s document, as the hub answers it. */
KrCreated *kr_lifecycle_parse_created(const char *json, GError **error);
void kr_created_free(KrCreated *created);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrCreated, kr_created_free)

typedef struct {
    char *name;
    char *from;
    gboolean already_abandoned;
    gboolean dry_run;
    guint cancelled_jobs;
    guint withdrawn_gates;
} KrAbandonReport;

/* `vibey abandon --json`'s document, its two lists reduced to counts. */
KrAbandonReport *kr_lifecycle_parse_report(const char *json, GError **error);
void kr_abandon_report_free(KrAbandonReport *report);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrAbandonReport, kr_abandon_report_free)

/* What the confirmation says before an unwind goes ahead: what it cancels, that it cannot be
 * undone, that the work on disk stays. For an already-unwound project, that nothing changes. */
char *kr_lifecycle_confirm_text(const KrAbandonReport *report);

/* The `message` a work route (start, pause) answers with; `fallback` (copied) when it sent
 * none or sent something that is not the document. */
char *kr_lifecycle_message(const char *json, const char *fallback);

G_END_DECLS

#endif /* KR_LIFECYCLE_H */
