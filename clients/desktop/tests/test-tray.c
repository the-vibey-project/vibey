/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-tray: what the tray item says and offers is decided here, not in the platform shims. */

#include <glib.h>

#include "kr-tray.h"

static void
open_gates(KrState *state, guint count)
{
    GString *json = g_string_new("{\"gates\": [");
    for (guint i = 0; i < count; i++)
        g_string_append_printf(json, "%s{\"gate_id\": \"g%u\", \"kind\": \"approval\"}",
                               i > 0 ? "," : "", i);
    g_string_append(json, "]}");
    g_autoptr(GError) error = NULL;
    GPtrArray *gates = kr_gates_parse(json->str, -1, &error);
    g_assert_no_error(error);
    g_ptr_array_unref(kr_state_set_gates(state, gates));
    g_string_free(json, TRUE);
}

static const char *
action_at(const KrTrayModel *model, guint index)
{
    return ((const KrTrayEntry *) g_ptr_array_index(model->entries, index))->action;
}

static void
test_a_quiet_state_offers_open_start_and_quit(void)
{
    KrState *state = kr_state_new();
    g_autoptr(KrTrayModel) model = kr_tray_model_new(state, "krypton");
    g_assert_false(model->attention);
    g_assert_cmpstr(model->tooltip, ==, "krypton: all quiet");
    g_assert_cmpuint(model->entries->len, ==, 3);
    g_assert_cmpstr(action_at(model, 0), ==, "open");
    g_assert_cmpstr(action_at(model, 1), ==, "start-project");
    g_assert_cmpstr(action_at(model, 2), ==, "quit");
    kr_state_free(state);
}

static void
test_a_waiting_gate_asks_to_be_noticed_and_to_be_answered(void)
{
    KrState *state = kr_state_new();
    open_gates(state, 1);
    g_autoptr(KrTrayModel) one = kr_tray_model_new(state, "krypton");
    g_assert_true(one->attention);
    g_assert_cmpstr(one->tooltip, ==, "krypton: 1 gate needs you");
    g_assert_cmpuint(one->entries->len, ==, 4);
    g_assert_cmpstr(action_at(one, 1), ==, "show-gates");
    g_assert_cmpstr(((KrTrayEntry *) g_ptr_array_index(one->entries, 1))->label, ==,
                    "Answer 1 waiting gate");

    open_gates(state, 3);
    g_autoptr(KrTrayModel) three = kr_tray_model_new(state, "krypton");
    g_assert_cmpstr(three->tooltip, ==, "krypton: 3 gates need you");
    g_assert_cmpstr(((KrTrayEntry *) g_ptr_array_index(three->entries, 1))->label, ==,
                    "Answer 3 waiting gates");
    g_assert_false(kr_tray_model_equal(one, three));
    kr_state_free(state);
}

static void
test_a_silent_hub_is_said_before_any_count(void)
{
    KrState *state = kr_state_new();
    open_gates(state, 2);
    kr_state_set_connection(state, KR_CONNECTION_OFFLINE, "No hub answers.");
    g_autoptr(KrTrayModel) offline = kr_tray_model_new(state, "krypton nightly");
    g_assert_cmpstr(offline->tooltip, ==, "krypton nightly: no hub answers");
    /* The counts are stale while the hub is silent: the item does not shout about them. */
    g_assert_false(offline->attention);
    /* ...and offers the one thing that helps: starting the hub, which outlives krypton. */
    g_assert_cmpuint(offline->entries->len, ==, 4);
    g_assert_cmpstr(action_at(offline, 2), ==, "start-hub");
    g_assert_cmpstr(((KrTrayEntry *) g_ptr_array_index(offline->entries, 2))->label, ==,
                    "Start the hub");

    kr_state_set_connection(state, KR_CONNECTION_REFUSED, "Refused.");
    g_autoptr(KrTrayModel) refused = kr_tray_model_new(state, "krypton nightly");
    g_assert_cmpstr(refused->tooltip, ==, offline->tooltip);
    /* A refusal is not a silent hub: starting one would not help. */
    g_assert_cmpuint(refused->entries->len, ==, 3);
    g_assert_false(kr_tray_model_equal(offline, refused));
    kr_state_free(state);
}

static void
test_a_running_hub_can_be_stopped_from_the_tray_and_quit_does_not_do_it(void)
{
    KrState *state = kr_state_new();
    kr_state_set_connection(state, KR_CONNECTION_ONLINE, NULL);
    g_autoptr(KrTrayModel) model = kr_tray_model_new(state, "krypton");
    g_assert_cmpuint(model->entries->len, ==, 4);
    g_assert_cmpstr(action_at(model, 2), ==, "stop-hub");
    g_assert_cmpstr(action_at(model, 3), ==, "quit");
    kr_state_free(state);
}

static void
test_running_lanes_are_counted_when_nothing_waits(void)
{
    KrState *state = kr_state_new();
    g_autoptr(GError) error = NULL;
    kr_state_set_lanes(
        state, kr_lanes_parse("{\"lanes\": [{\"id\": \"a\", \"state\": \"running\"},"
                              " {\"id\": \"b\", \"state\": \"running\"},"
                              " {\"id\": \"c\", \"state\": \"finished\"}]}",
                              -1, &error));
    g_assert_no_error(error);
    g_autoptr(KrTrayModel) model = kr_tray_model_new(state, "krypton");
    g_assert_cmpstr(model->tooltip, ==, "krypton: 2 lanes running");
    kr_state_free(state);
}

static void
test_equal_models_draw_the_same(void)
{
    KrState *state = kr_state_new();
    g_autoptr(KrTrayModel) a = kr_tray_model_new(state, "krypton");
    g_autoptr(KrTrayModel) b = kr_tray_model_new(state, "krypton");
    g_assert_true(kr_tray_model_equal(a, b));
    g_autoptr(KrTrayModel) renamed = kr_tray_model_new(state, "krypton nightly");
    g_assert_false(kr_tray_model_equal(a, renamed));

    /* Same length and tooltip, different action: still different. */
    g_autoptr(KrTrayModel) other = kr_tray_model_new(state, "krypton");
    KrTrayEntry *entry = g_ptr_array_index(other->entries, 2);
    g_free(entry->action);
    entry->action = g_strdup("refresh");
    g_assert_false(kr_tray_model_equal(a, other));
    g_free(entry->action);
    entry->action = g_strdup("quit");
    g_free(entry->label);
    entry->label = g_strdup("Leave");
    g_assert_false(kr_tray_model_equal(a, other));
    kr_state_free(state);
}

static void
test_a_copy_stands_alone(void)
{
    KrState *state = kr_state_new();
    open_gates(state, 2);
    KrTrayModel *model = kr_tray_model_new(state, "krypton");
    KrTrayModel *copy = kr_tray_model_copy(model);
    g_assert_true(kr_tray_model_equal(model, copy));
    kr_tray_model_free(model); /* the copy owns its own strings */
    g_assert_cmpstr(copy->tooltip, ==, "krypton: 2 gates need you");
    g_assert_cmpstr(action_at(copy, 1), ==, "show-gates");
    kr_tray_model_free(copy);
    kr_tray_model_free(NULL);
    kr_state_free(state);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/tray/quiet", test_a_quiet_state_offers_open_start_and_quit);
    g_test_add_func("/tray/gates", test_a_waiting_gate_asks_to_be_noticed_and_to_be_answered);
    g_test_add_func("/tray/silent-hub", test_a_silent_hub_is_said_before_any_count);
    g_test_add_func("/tray/running-hub", test_a_running_hub_can_be_stopped_from_the_tray_and_quit_does_not_do_it);
    g_test_add_func("/tray/lanes", test_running_lanes_are_counted_when_nothing_waits);
    g_test_add_func("/tray/copy", test_a_copy_stands_alone);
    g_test_add_func("/tray/equal", test_equal_models_draw_the_same);
    return g_test_run();
}
