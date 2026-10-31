/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-commands: the one table the menu, the shortcuts dialog and the accelerators all read. */

#include <glib.h>

#include "kr-commands.h"

static void
test_every_command_has_an_action_a_label_and_a_group(void)
{
    gsize count = 0;
    const KrCommand *commands = kr_commands(&count);
    g_assert_cmpuint(count, >, 0);
    for (gsize i = 0; i < count; i++) {
        g_assert_nonnull(commands[i].action);
        g_assert_true(commands[i].action[0] != '\0');
        g_assert_true(commands[i].label[0] != '\0');
        g_assert_true(commands[i].group[0] != '\0');
        g_assert_nonnull(commands[i].accelerators);
    }
}

static void
test_an_action_is_named_once_and_a_key_belongs_to_one_command(void)
{
    gsize count = 0;
    const KrCommand *commands = kr_commands(&count);
    g_autoptr(GHashTable) actions = g_hash_table_new(g_str_hash, g_str_equal);
    g_autoptr(GHashTable) keys = g_hash_table_new(g_str_hash, g_str_equal);
    for (gsize i = 0; i < count; i++) {
        g_assert_true(g_hash_table_add(actions, (gpointer) commands[i].action));
        for (const char *const *key = commands[i].accelerators; *key != NULL; key++)
            g_assert_true(g_hash_table_add(keys, (gpointer) *key));
    }
}

static void
test_an_action_is_found_by_name_and_an_unknown_one_is_not(void)
{
    const KrCommand *quit = kr_command_find("quit");
    g_assert_nonnull(quit);
    g_assert_cmpstr(quit->label, ==, "Quit");
    g_assert_cmpstr(quit->accelerators[0], ==, "<Control>q");
    g_assert_null(kr_command_find("no-such-action"));
    g_assert_null(kr_command_find(NULL));
}

static void
test_the_settings_and_shortcut_keys_are_the_standard_ones(void)
{
    g_assert_cmpstr(kr_command_find("settings")->accelerators[0], ==, "<Control>comma");
    g_assert_cmpstr(kr_command_find("shortcuts")->accelerators[0], ==, "<Control>question");
    g_assert_cmpstr(kr_command_find("refresh")->accelerators[1], ==, "F5");
}

static void
test_the_groups_are_distinct_and_cover_every_command(void)
{
    const char *const *groups = kr_command_groups();
    g_assert_nonnull(groups);
    gsize n = 0;
    for (; groups[n] != NULL; n++)
        for (gsize j = 0; j < n; j++)
            g_assert_cmpstr(groups[j], !=, groups[n]);
    g_assert_cmpuint(n, >, 1);
    gsize count = 0;
    const KrCommand *commands = kr_commands(&count);
    for (gsize i = 0; i < count; i++) {
        gboolean found = FALSE;
        for (gsize j = 0; j < n; j++)
            found = found || g_strcmp0(groups[j], commands[i].group) == 0;
        g_assert_true(found);
    }
    /* The table is built once and handed out again. */
    g_assert_true(kr_command_groups() == groups);
}

static void
test_the_count_may_be_left_out(void)
{
    g_assert_nonnull(kr_commands(NULL));
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/commands/complete", test_every_command_has_an_action_a_label_and_a_group);
    g_test_add_func("/commands/unique", test_an_action_is_named_once_and_a_key_belongs_to_one_command);
    g_test_add_func("/commands/find", test_an_action_is_found_by_name_and_an_unknown_one_is_not);
    g_test_add_func("/commands/standard-keys", test_the_settings_and_shortcut_keys_are_the_standard_ones);
    g_test_add_func("/commands/groups", test_the_groups_are_distinct_and_cover_every_command);
    g_test_add_func("/commands/count-optional", test_the_count_may_be_left_out);
    return g_test_run();
}
