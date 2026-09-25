/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-state.h"

static void
heard(KrState *state, KrStateSlice slice, gpointer data)
{
    (void) state;
    GArray *slices = data;
    g_array_append_val(slices, slice);
}

static GPtrArray *
gates_doc(const char *json)
{
    g_autoptr(GError) error = NULL;
    GPtrArray *gates = kr_gates_parse(json, -1, &error);
    g_assert_no_error(error);
    return gates;
}

static void
test_gates_are_announced_once(void)
{
    KrState *state = kr_state_new();
    g_autoptr(GPtrArray) first = kr_state_set_gates(
        state, gates_doc("{\"gates\": [{\"gate_id\": \"a\", \"kind\": \"approval\","
                         " \"project_id\": \"p\"}]}"));
    g_assert_cmpuint(first->len, ==, 0); /* what was already open is not news */

    g_autoptr(GPtrArray) second = kr_state_set_gates(
        state, gates_doc("{\"gates\": [{\"gate_id\": \"a\", \"kind\": \"approval\","
                         " \"project_id\": \"p\"}, {\"gate_id\": \"b\", \"kind\": \"choice\","
                         " \"project_id\": \"q\"}]}"));
    g_assert_cmpuint(second->len, ==, 1);
    g_assert_cmpstr(((KrGate *) g_ptr_array_index(second, 0))->gate_id, ==, "b");

    g_autoptr(GPtrArray) third = kr_state_set_gates(
        state, gates_doc("{\"gates\": [{\"gate_id\": \"b\", \"kind\": \"choice\"}]}"));
    g_assert_cmpuint(third->len, ==, 0);
    g_assert_cmpuint(kr_state_gates(state)->len, ==, 1);

    g_autoptr(GPtrArray) cleared = kr_state_set_gates(state, NULL);
    g_assert_cmpuint(cleared->len, ==, 0);
    g_assert_cmpuint(kr_state_gates(state)->len, ==, 0);
    kr_state_free(state);
}

static void
test_slices_and_selection(void)
{
    KrState *state = kr_state_new();
    GArray *slices = g_array_new(FALSE, FALSE, sizeof(KrStateSlice));
    guint id = kr_state_listen(state, heard, slices);

    g_autoptr(GError) error = NULL;
    kr_state_set_projects(
        state, kr_projects_parse("[{\"project_id\": \"p\", \"name\": \"greeter\"},"
                                 " {\"project_id\": \"q\", \"name\": \"paper\"}]",
                                 -1, &error));
    g_assert_cmpuint(kr_state_projects(state)->len, ==, 2);
    g_assert_null(kr_state_selected(state));

    kr_state_select_project(state, "q");
    kr_state_select_project(state, "q"); /* no change, no call */
    g_assert_cmpstr(kr_state_selected_project(state), ==, "q");
    g_assert_cmpstr(kr_state_selected(state)->name, ==, "paper");
    kr_state_select_project(state, "gone");
    g_assert_null(kr_state_selected(state));
    kr_state_select_project(state, NULL);
    g_assert_null(kr_state_selected_project(state));

    g_autoptr(GPtrArray) news = kr_state_set_gates(
        state, gates_doc("{\"gates\": [{\"gate_id\": \"a\", \"kind\": \"x\", \"project_id\": \"p\"},"
                         " {\"gate_id\": \"b\", \"kind\": \"x\", \"project_id\": \"q\"}]}"));
    g_autoptr(GPtrArray) for_p = kr_state_gates_for(state, "p");
    g_assert_cmpuint(for_p->len, ==, 1);

    kr_state_set_lanes(state,
                       kr_lanes_parse("{\"lanes\": [{\"id\": \"1\", \"state\": \"running\"},"
                                      " {\"id\": \"2\", \"state\": \"finished\"}]}",
                                      -1, &error));
    g_assert_cmpuint(kr_state_lanes(state)->len, ==, 2);
    g_assert_cmpuint(kr_state_running_lanes(state), ==, 1);

    g_assert_null(kr_state_loops(state));
    kr_state_set_loops(state, kr_loops_parse("{\"loops\": []}", -1, &error));
    g_assert_nonnull(kr_state_loops(state));
    kr_state_set_loops(state, kr_loops_parse("{\"loops\": []}", -1, &error));

    g_assert_null(kr_state_doctor(state));
    kr_state_set_doctor(state, kr_doctor_parse("{\"checks\": []}", -1, &error));
    g_assert_nonnull(kr_state_doctor(state));

    kr_state_set_budget(state, kr_budget_parse("{\"project_id\": \"p\", \"cycle\": 3}", -1, &error));
    kr_state_set_budget(state, NULL);
    g_assert_cmpint(kr_state_budget(state, "p")->cycle, ==, 3);
    g_assert_null(kr_state_budget(state, "q"));
    g_assert_null(kr_state_budget(state, NULL));

    g_assert_cmpint(kr_state_connection(state), ==, KR_CONNECTION_UNKNOWN);
    kr_state_set_connection(state, KR_CONNECTION_REFUSED, "401");
    kr_state_set_connection(state, KR_CONNECTION_REFUSED, "401"); /* no change */
    g_assert_cmpint(kr_state_connection(state), ==, KR_CONNECTION_REFUSED);
    g_assert_cmpstr(kr_state_connection_message(state), ==, "401");

    const KrStateSlice want[] = {KR_STATE_PROJECTS, KR_STATE_SELECTION, KR_STATE_SELECTION,
                                 KR_STATE_SELECTION, KR_STATE_GATES,     KR_STATE_LANES,
                                 KR_STATE_LOOPS,     KR_STATE_LOOPS,     KR_STATE_DOCTOR,
                                 KR_STATE_BUDGET,    KR_STATE_CONNECTION};
    g_assert_cmpuint(slices->len, ==, G_N_ELEMENTS(want));
    for (guint i = 0; i < slices->len; i++)
        g_assert_cmpint(g_array_index(slices, KrStateSlice, i), ==, want[i]);

    kr_state_unlisten(state, 12345); /* unknown: nothing happens */
    kr_state_unlisten(state, id);
    kr_state_set_projects(state, NULL);
    g_assert_cmpuint(slices->len, ==, G_N_ELEMENTS(want));
    g_assert_cmpuint(kr_state_projects(state)->len, ==, 0);

    g_array_unref(slices);
    kr_state_free(state);
    kr_state_free(NULL);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/state/gates-announced-once", test_gates_are_announced_once);
    g_test_add_func("/state/slices-and-selection", test_slices_and_selection);
    return g_test_run();
}
