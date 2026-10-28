/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* Every icon-only control in the GTK views is given an accessible name (#1699).
 *
 * THIS IS A HEURISTIC, NOT A PROOF. The views need a display, and a screen reader cannot run
 * in CI, so this reads the C files in src/app as text: each `gtk_button_new_from_icon_name` and each
 * `gtk_menu_button_set_icon_name` must be followed, in the same function, by a call to
 * kr_a11y_name or kr_a11y_name_with_hint on that very variable. It cannot see a control built
 * some other way, and it does not check that a name is a good one. ACCESSIBILITY.md records
 * what a person with a screen reader found. */

#include <glib.h>
#include <string.h>

#include "kr-commands.h"

#define LOOKAHEAD_LINES 16

/* Lines (1-based) where an icon-only control is made and not named afterwards. `*seen` counts
 * the icon-only controls found, so a test can tell "all named" from "none looked at". */
static GArray *
unnamed_controls(const char *source, guint *seen)
{
    g_autoptr(GRegex) button =
        g_regex_new("(\\w+)\\s*=\\s*gtk_button_new_from_icon_name\\(", 0, 0, NULL);
    g_autoptr(GRegex) menu =
        g_regex_new("gtk_menu_button_set_icon_name\\(GTK_MENU_BUTTON\\((\\w+)\\)", 0, 0, NULL);
    g_autoptr(GRegex) anonymous = g_regex_new("[^=]\\s*gtk_button_new_from_icon_name\\(", 0, 0, NULL);
    g_auto(GStrv) lines = g_strsplit(source, "\n", -1);
    GArray *bad = g_array_new(FALSE, FALSE, sizeof(guint));
    guint total = g_strv_length(lines);
    for (guint i = 0; i < total; i++) {
        g_autofree char *variable = NULL;
        g_autoptr(GMatchInfo) as_button = NULL;
        g_autoptr(GMatchInfo) as_menu = NULL;
        if (g_regex_match(button, lines[i], 0, &as_button)) {
            variable = g_match_info_fetch(as_button, 1);
        } else if (g_regex_match(menu, lines[i], 0, &as_menu)) {
            variable = g_match_info_fetch(as_menu, 1);
        } else if (g_regex_match(anonymous, lines[i], 0, NULL)) {
            guint line = i + 1;
            (*seen)++;
            g_array_append_val(bad, line);
            continue;
        } else {
            continue;
        }
        (*seen)++;
        g_autofree char *named = g_strdup_printf("kr_a11y_name(%s,", variable);
        g_autofree char *hinted = g_strdup_printf("kr_a11y_name_with_hint(%s,", variable);
        gboolean ok = FALSE;
        for (guint j = i; j < total && j <= i + LOOKAHEAD_LINES && !ok; j++)
            ok = strstr(lines[j], named) != NULL || strstr(lines[j], hinted) != NULL;
        if (!ok) {
            guint line = i + 1;
            g_array_append_val(bad, line);
        }
    }
    return bad;
}

static void
test_the_checker_flags_an_unnamed_icon_button(void)
{
    guint seen = 0;
    g_autoptr(GArray) bad = unnamed_controls(
        "GtkWidget *b = gtk_button_new_from_icon_name(\"list-add-symbolic\");\n"
        "gtk_box_append(box, b);\n",
        &seen);
    g_assert_cmpuint(seen, ==, 1);
    g_assert_cmpuint(bad->len, ==, 1);
    g_assert_cmpuint(g_array_index(bad, guint, 0), ==, 1);
}

static void
test_the_checker_flags_an_unnamed_menu_button_and_an_unassigned_button(void)
{
    guint seen = 0;
    g_autoptr(GArray) bad = unnamed_controls(
        "gtk_menu_button_set_icon_name(GTK_MENU_BUTTON(m), \"open-menu-symbolic\");\n"
        "gtk_box_append(box, gtk_button_new_from_icon_name(\"x\"));\n",
        &seen);
    g_assert_cmpuint(seen, ==, 2);
    g_assert_cmpuint(bad->len, ==, 2);
}

static void
test_the_checker_accepts_a_named_control_and_wants_that_variables_name(void)
{
    guint seen = 0;
    g_autoptr(GArray) bad = unnamed_controls(
        "GtkWidget *a = gtk_button_new_from_icon_name(\"x\");\n"
        "kr_a11y_name(a, \"A\");\n"
        "GtkWidget *b = gtk_button_new_from_icon_name(\"y\");\n"
        "kr_a11y_name_with_hint(b, \"B\", \"hint\");\n"
        "GtkWidget *c = gtk_button_new_from_icon_name(\"z\");\n"
        "kr_a11y_name(a, \"named the wrong one\");\n",
        &seen);
    g_assert_cmpuint(seen, ==, 3);
    g_assert_cmpuint(bad->len, ==, 1);
    g_assert_cmpuint(g_array_index(bad, guint, 0), ==, 5);
}

static void
test_every_icon_only_control_in_the_views_is_named(void)
{
    const char *root = g_getenv("G_TEST_SRCDIR");
    g_assert_nonnull(root);
    g_autofree char *dir = g_build_filename(root, "..", "src", "app", NULL);
    g_autoptr(GDir) handle = g_dir_open(dir, 0, NULL);
    g_assert_nonnull(handle);
    guint seen = 0;
    GString *unnamed = g_string_new(NULL);
    for (const char *entry; (entry = g_dir_read_name(handle)) != NULL;) {
        if (!g_str_has_suffix(entry, ".c"))
            continue;
        g_autofree char *path = g_build_filename(dir, entry, NULL);
        g_autofree char *source = NULL;
        g_assert_true(g_file_get_contents(path, &source, NULL, NULL));
        g_autoptr(GArray) bad = unnamed_controls(source, &seen);
        for (guint i = 0; i < bad->len; i++)
            g_string_append_printf(unnamed, "%s:%u ", entry, g_array_index(bad, guint, i));
    }
    /* Looking at nothing would pass too: the views do have icon-only controls. */
    g_assert_cmpuint(seen, >=, 4);
    if (unnamed->len > 0)
        g_test_message("icon-only controls with no accessible name: %s", unnamed->str);
    g_assert_cmpuint(unnamed->len, ==, 0);
    g_string_free(unnamed, TRUE);
}

static void
test_every_command_the_menu_offers_has_a_label_a_screen_reader_can_read(void)
{
    gsize count = 0;
    const KrCommand *commands = kr_commands(&count);
    for (gsize i = 0; i < count; i++) {
        g_assert_true(g_utf8_validate(commands[i].label, -1, NULL));
        g_assert_true(g_ascii_isalpha(commands[i].label[0]) ||
                      g_utf8_get_char(commands[i].label) > 0x7f);
    }
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/accessible-names/flags-unnamed-button", test_the_checker_flags_an_unnamed_icon_button);
    g_test_add_func("/accessible-names/flags-menu-and-unassigned",
                    test_the_checker_flags_an_unnamed_menu_button_and_an_unassigned_button);
    g_test_add_func("/accessible-names/accepts-named",
                    test_the_checker_accepts_a_named_control_and_wants_that_variables_name);
    g_test_add_func("/accessible-names/views", test_every_icon_only_control_in_the_views_is_named);
    g_test_add_func("/accessible-names/command-labels",
                    test_every_command_the_menu_offers_has_a_label_a_screen_reader_can_read);
    return g_test_run();
}
