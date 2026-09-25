/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include <glib/gstdio.h>

#include "kr-settings.h"

static void
test_channels(void)
{
    g_assert_cmpstr(kr_channel_app_id(KR_CHANNEL_STABLE), ==, "io.github.the_vibey_project.Krypton");
    g_assert_cmpstr(kr_channel_app_id(KR_CHANNEL_NIGHTLY), ==,
                    "io.github.the_vibey_project.Krypton.Nightly");
    g_assert_cmpstr(kr_channel_display_name(KR_CHANNEL_STABLE), ==, "Krypton");
    g_assert_cmpstr(kr_channel_display_name(KR_CHANNEL_NIGHTLY), ==, "Krypton Nightly");
    g_assert_cmpstr(kr_channel_dir_name(KR_CHANNEL_STABLE), ==, "krypton");
    g_assert_cmpstr(kr_channel_dir_name(KR_CHANNEL_NIGHTLY), ==, "krypton-nightly");
    g_assert_cmpint(kr_channel_from_string("NIGHTLY"), ==, KR_CHANNEL_NIGHTLY);
    g_assert_cmpint(kr_channel_from_string("stable"), ==, KR_CHANNEL_STABLE);
    g_assert_cmpint(kr_channel_from_string("beta"), ==, KR_CHANNEL_STABLE);
    g_assert_cmpint(kr_channel_from_string(NULL), ==, KR_CHANNEL_STABLE);
}

static void
test_theme(void)
{
    g_assert_cmpstr(kr_theme_mode_to_string(VIBEY_THEME_MODE_SYSTEM), ==, "system");
    g_assert_cmpstr(kr_theme_mode_to_string(VIBEY_THEME_MODE_LIGHT), ==, "light");
    g_assert_cmpstr(kr_theme_mode_to_string(VIBEY_THEME_MODE_DARK), ==, "dark");
    g_assert_cmpstr(kr_theme_mode_to_string((VibeyThemeMode) 42), ==, "system");
    g_assert_cmpint(kr_theme_mode_from_string("Light"), ==, VIBEY_THEME_MODE_LIGHT);
    g_assert_cmpint(kr_theme_mode_from_string("DARK"), ==, VIBEY_THEME_MODE_DARK);
    g_assert_cmpint(kr_theme_mode_from_string("sepia"), ==, VIBEY_THEME_MODE_SYSTEM);
    g_assert_cmpint(kr_theme_mode_from_string(NULL), ==, VIBEY_THEME_MODE_SYSTEM);
}

static void
test_round_trip(void)
{
    g_autofree char *dir = g_dir_make_tmp("krypton-settings-XXXXXX", NULL);
    g_autofree char *path = kr_settings_path(KR_CHANNEL_NIGHTLY, dir);
    g_autofree char *want = g_build_filename(dir, "krypton-nightly", "settings.ini", NULL);
    g_assert_cmpstr(path, ==, want);

    g_autoptr(KrSettings) defaults = kr_settings_load(path);
    g_assert_cmpint(defaults->theme, ==, VIBEY_THEME_MODE_SYSTEM);
    g_assert_null(defaults->hub_host);
    g_assert_true(defaults->notifications);
    g_assert_true(defaults->sounds);

    KrSettings *settings = kr_settings_new_default();
    settings->theme = VIBEY_THEME_MODE_DARK;
    settings->hub_host = g_strdup("studio.local");
    settings->hub_port = 9000;
    settings->sounds = FALSE;
    g_autoptr(GError) error = NULL;
    g_assert_true(kr_settings_save(settings, path, &error));
    g_assert_no_error(error);
    kr_settings_free(settings);

    g_autoptr(KrSettings) back = kr_settings_load(path);
    g_assert_cmpint(back->theme, ==, VIBEY_THEME_MODE_DARK);
    g_assert_cmpstr(back->hub_host, ==, "studio.local");
    g_assert_cmpuint(back->hub_port, ==, 9000);
    g_assert_true(back->notifications);
    g_assert_false(back->sounds);

    /* A hand-edited file with nonsense in it gives the defaults for the nonsense. */
    g_assert_true(g_file_set_contents(path,
                                      "[look]\ntheme=sepia\n[hub]\nhost=\nport=70000\n"
                                      "[alerts]\nnotifications=maybe\n",
                                      -1, NULL));
    g_autoptr(KrSettings) odd = kr_settings_load(path);
    g_assert_cmpint(odd->theme, ==, VIBEY_THEME_MODE_SYSTEM);
    g_assert_null(odd->hub_host);
    g_assert_cmpuint(odd->hub_port, ==, 0);
    g_assert_true(odd->notifications);

    g_autoptr(KrSettings) none = kr_settings_load(NULL);
    g_assert_cmpint(none->theme, ==, VIBEY_THEME_MODE_SYSTEM);

    /* A directory that cannot be made is an error, not a crash. */
    g_autofree char *blocker = g_build_filename(dir, "blocker", NULL);
    g_assert_true(g_file_set_contents(blocker, "", -1, NULL));
    g_autofree char *under = g_build_filename(blocker, "x", "settings.ini", NULL);
    g_autoptr(KrSettings) fresh = kr_settings_new_default();
    g_autoptr(GError) failed = NULL;
    g_assert_false(kr_settings_save(fresh, under, &failed));
    g_assert_nonnull(failed);

    g_unlink(path);
    g_unlink(blocker);
    g_autofree char *sub = g_path_get_dirname(path);
    g_rmdir(sub);
    g_rmdir(dir);
    kr_settings_free(NULL);

    g_autofree char *default_path = kr_settings_path(KR_CHANNEL_STABLE, NULL);
    g_assert_true(g_str_has_suffix(default_path, "krypton/settings.ini"));
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/settings/channels", test_channels);
    g_test_add_func("/settings/theme", test_theme);
    g_test_add_func("/settings/round-trip", test_round_trip);
    return g_test_run();
}
