/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-state: the one place Krypton desktop keeps what it knows.
 *
 * The views read from here and listen for changes; the hub client writes here. Each setter
 * takes ownership of what it is given and tells every listener which slice changed, so a
 * view redraws only what it shows. Gates carry one more duty: the state remembers which
 * gates it has already seen, so a gate raised while the window is closed is announced once
 * (a notification), never on every refresh. */

#ifndef KR_STATE_H
#define KR_STATE_H

#include <glib.h>

#include "kr-model.h"

G_BEGIN_DECLS

typedef enum {
    KR_STATE_PROJECTS,
    KR_STATE_GATES,
    KR_STATE_LANES,
    KR_STATE_LOOPS,
    KR_STATE_DOCTOR,
    KR_STATE_BUDGET,
    KR_STATE_SELECTION,
    KR_STATE_CONNECTION,
} KrStateSlice;

typedef enum {
    KR_CONNECTION_UNKNOWN,  /* not asked yet */
    KR_CONNECTION_ONLINE,   /* the hub answered */
    KR_CONNECTION_REFUSED,  /* the hub answered with a refusal (see message) */
    KR_CONNECTION_OFFLINE,  /* nothing answered */
} KrConnection;

typedef struct _KrState KrState;
typedef void (*KrStateListener)(KrState *state, KrStateSlice slice, gpointer user_data);

KrState *kr_state_new(void);
void kr_state_free(KrState *state);

/* Listeners are called in the order added. The id removes one again. */
guint kr_state_listen(KrState *state, KrStateListener listener, gpointer user_data);
void kr_state_unlisten(KrState *state, guint id);

void kr_state_set_projects(KrState *state, GPtrArray *projects);
GPtrArray *kr_state_projects(KrState *state); /* borrowed; never NULL */

/* Stores the open gates and returns the ones not seen before, in the hub's order (a new
 * array of borrowed pointers; free the array, not its elements). The first call only
 * learns what is open: it returns an empty array, so starting Krypton does not announce
 * every gate that was already waiting. */
GPtrArray *kr_state_set_gates(KrState *state, GPtrArray *gates);
GPtrArray *kr_state_gates(KrState *state);
/* The open gates of one project (borrowed pointers in a new array). */
GPtrArray *kr_state_gates_for(KrState *state, const char *project_id);

void kr_state_set_lanes(KrState *state, GPtrArray *lanes);
GPtrArray *kr_state_lanes(KrState *state);
/* How many lanes are running now. */
guint kr_state_running_lanes(KrState *state);

void kr_state_set_loops(KrState *state, KrLoops *loops);
const KrLoops *kr_state_loops(KrState *state); /* NULL until known */

void kr_state_set_doctor(KrState *state, KrDoctor *doctor);
const KrDoctor *kr_state_doctor(KrState *state);

void kr_state_set_budget(KrState *state, KrBudget *budget);
const KrBudget *kr_state_budget(KrState *state, const char *project_id);

/* The project the person is looking at. Selecting one that is not known is allowed (it may
 * arrive with the next refresh). NULL clears the selection. */
void kr_state_select_project(KrState *state, const char *project_id);
const char *kr_state_selected_project(KrState *state);
/* The selected project's record, or NULL. */
const KrProject *kr_state_selected(KrState *state);

void kr_state_set_connection(KrState *state, KrConnection connection, const char *message);
KrConnection kr_state_connection(KrState *state);
const char *kr_state_connection_message(KrState *state);

G_END_DECLS

#endif /* KR_STATE_H */
