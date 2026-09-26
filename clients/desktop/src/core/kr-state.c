/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-state.h"

typedef struct {
    guint id;
    KrStateListener listener;
    gpointer user_data;
} Listener;

struct _KrState {
    GPtrArray *projects;
    GPtrArray *gates;
    GPtrArray *lanes;
    KrLoops *loops;
    KrDoctor *doctor;
    GHashTable *budgets;    /* project_id -> KrBudget */
    GHashTable *seen_gates; /* gate_id set */
    gboolean gates_known;
    char *selected;
    KrConnection connection;
    char *connection_message;
    GArray *listeners;
    guint next_listener;
};

static GPtrArray *
empty(GDestroyNotify free_one)
{
    return g_ptr_array_new_with_free_func(free_one);
}

KrState *
kr_state_new(void)
{
    KrState *state = g_new0(KrState, 1);
    state->projects = empty((GDestroyNotify) kr_project_free);
    state->gates = empty((GDestroyNotify) kr_gate_free);
    state->lanes = empty((GDestroyNotify) kr_lane_free);
    state->budgets = g_hash_table_new_full(g_str_hash, g_str_equal, g_free,
                                           (GDestroyNotify) kr_budget_free);
    state->seen_gates = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, NULL);
    state->listeners = g_array_new(FALSE, FALSE, sizeof(Listener));
    state->connection = KR_CONNECTION_UNKNOWN;
    return state;
}

void
kr_state_free(KrState *state)
{
    if (state == NULL)
        return;
    g_ptr_array_unref(state->projects);
    g_ptr_array_unref(state->gates);
    g_ptr_array_unref(state->lanes);
    kr_loops_free(state->loops);
    kr_doctor_free(state->doctor);
    g_hash_table_unref(state->budgets);
    g_hash_table_unref(state->seen_gates);
    g_free(state->selected);
    g_free(state->connection_message);
    g_array_unref(state->listeners);
    g_free(state);
}

guint
kr_state_listen(KrState *state, KrStateListener listener, gpointer user_data)
{
    Listener entry = {++state->next_listener, listener, user_data};
    g_array_append_val(state->listeners, entry);
    return entry.id;
}

void
kr_state_unlisten(KrState *state, guint id)
{
    for (guint i = 0; i < state->listeners->len; i++) {
        if (g_array_index(state->listeners, Listener, i).id == id) {
            g_array_remove_index(state->listeners, i);
            return;
        }
    }
}

static void
changed(KrState *state, KrStateSlice slice)
{
    for (guint i = 0; i < state->listeners->len; i++) {
        Listener *entry = &g_array_index(state->listeners, Listener, i);
        entry->listener(state, slice, entry->user_data);
    }
}

static void
replace(GPtrArray **slot, GPtrArray *with, GDestroyNotify free_one)
{
    g_ptr_array_unref(*slot);
    *slot = with != NULL ? with : empty(free_one);
}

void
kr_state_set_projects(KrState *state, GPtrArray *projects)
{
    replace(&state->projects, projects, (GDestroyNotify) kr_project_free);
    changed(state, KR_STATE_PROJECTS);
}

GPtrArray *
kr_state_projects(KrState *state)
{
    return state->projects;
}

GPtrArray *
kr_state_set_gates(KrState *state, GPtrArray *gates)
{
    replace(&state->gates, gates, (GDestroyNotify) kr_gate_free);
    GPtrArray *fresh = g_ptr_array_new();
    for (guint i = 0; i < state->gates->len; i++) {
        KrGate *gate = g_ptr_array_index(state->gates, i);
        if (g_hash_table_add(state->seen_gates, g_strdup(gate->gate_id)) && state->gates_known)
            g_ptr_array_add(fresh, gate);
    }
    state->gates_known = TRUE;
    changed(state, KR_STATE_GATES);
    return fresh;
}

GPtrArray *
kr_state_gates(KrState *state)
{
    return state->gates;
}

GPtrArray *
kr_state_gates_for(KrState *state, const char *project_id)
{
    GPtrArray *out = g_ptr_array_new();
    for (guint i = 0; i < state->gates->len; i++) {
        KrGate *gate = g_ptr_array_index(state->gates, i);
        if (g_strcmp0(gate->project_id, project_id) == 0)
            g_ptr_array_add(out, gate);
    }
    return out;
}

void
kr_state_set_lanes(KrState *state, GPtrArray *lanes)
{
    replace(&state->lanes, lanes, (GDestroyNotify) kr_lane_free);
    changed(state, KR_STATE_LANES);
}

GPtrArray *
kr_state_lanes(KrState *state)
{
    return state->lanes;
}

guint
kr_state_running_lanes(KrState *state)
{
    guint running = 0;
    for (guint i = 0; i < state->lanes->len; i++) {
        const KrLane *lane = g_ptr_array_index(state->lanes, i);
        if (g_strcmp0(lane->state, "running") == 0)
            running++;
    }
    return running;
}

void
kr_state_set_loops(KrState *state, KrLoops *loops)
{
    kr_loops_free(state->loops);
    state->loops = loops;
    changed(state, KR_STATE_LOOPS);
}

const KrLoops *
kr_state_loops(KrState *state)
{
    return state->loops;
}

void
kr_state_set_doctor(KrState *state, KrDoctor *doctor)
{
    kr_doctor_free(state->doctor);
    state->doctor = doctor;
    changed(state, KR_STATE_DOCTOR);
}

const KrDoctor *
kr_state_doctor(KrState *state)
{
    return state->doctor;
}

void
kr_state_set_budget(KrState *state, KrBudget *budget)
{
    if (budget == NULL)
        return;
    g_hash_table_replace(state->budgets, g_strdup(budget->project_id), budget);
    changed(state, KR_STATE_BUDGET);
}

const KrBudget *
kr_state_budget(KrState *state, const char *project_id)
{
    return project_id != NULL ? g_hash_table_lookup(state->budgets, project_id) : NULL;
}

void
kr_state_select_project(KrState *state, const char *project_id)
{
    if (g_strcmp0(state->selected, project_id) == 0)
        return;
    g_free(state->selected);
    state->selected = g_strdup(project_id);
    changed(state, KR_STATE_SELECTION);
}

const char *
kr_state_selected_project(KrState *state)
{
    return state->selected;
}

const KrProject *
kr_state_selected(KrState *state)
{
    for (guint i = 0; state->selected != NULL && i < state->projects->len; i++) {
        const KrProject *project = g_ptr_array_index(state->projects, i);
        if (g_str_equal(project->project_id, state->selected))
            return project;
    }
    return NULL;
}

void
kr_state_set_connection(KrState *state, KrConnection connection, const char *message)
{
    if (state->connection == connection && g_strcmp0(state->connection_message, message) == 0)
        return;
    state->connection = connection;
    g_free(state->connection_message);
    state->connection_message = g_strdup(message);
    changed(state, KR_STATE_CONNECTION);
}

KrConnection
kr_state_connection(KrState *state)
{
    return state->connection;
}

const char *
kr_state_connection_message(KrState *state)
{
    return state->connection_message;
}
