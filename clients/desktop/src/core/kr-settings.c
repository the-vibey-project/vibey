/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-settings.h"

#include <errno.h>
#include <glib/gstdio.h>

#define GROUP_LOOK "look"
#define GROUP_HUB "hub"
#define GROUP_ALERTS "alerts"

const char *
kr_channel_app_id(KrChannel channel)
{
    return channel == KR_CHANNEL_NIGHTLY ? "io.github.the_vibey_project.Krypton.Nightly"
                                         : "io.github.the_vibey_project.Krypton";
}

const char *
kr_channel_display_name(KrChannel channel)
{
    return channel == KR_CHANNEL_NIGHTLY ? "Krypton Nightly" : "Krypton";
}

const char *
kr_channel_dir_name(KrChannel channel)
{
    return channel == KR_CHANNEL_NIGHTLY ? "krypton-nightly" : "krypton";
}

KrChannel
kr_channel_from_string(const char *text)
{
    return text != NULL && g_ascii_strcasecmp(text, "nightly") == 0 ? KR_CHANNEL_NIGHTLY
                                                                   : KR_CHANNEL_STABLE;
}

const char *
kr_theme_mode_to_string(VibeyThemeMode mode)
{
    switch (mode) {
    case VIBEY_THEME_MODE_LIGHT:
        return "light";
    case VIBEY_THEME_MODE_DARK:
        return "dark";
    case VIBEY_THEME_MODE_SYSTEM:
    default:
        return "system";
    }
}

VibeyThemeMode
kr_theme_mode_from_string(const char *text)
{
    if (text != NULL && g_ascii_strcasecmp(text, "light") == 0)
        return VIBEY_THEME_MODE_LIGHT;
    if (text != NULL && g_ascii_strcasecmp(text, "dark") == 0)
        return VIBEY_THEME_MODE_DARK;
    return VIBEY_THEME_MODE_DEFAULT;
}

KrSettings *
kr_settings_new_default(void)
{
    KrSettings *settings = g_new0(KrSettings, 1);
    settings->theme = VIBEY_THEME_MODE_DEFAULT;
    settings->hub_host = NULL;
    settings->hub_port = 0;
    settings->notifications = TRUE;
    settings->sounds = TRUE;
    return settings;
}

void
kr_settings_free(KrSettings *settings)
{
    if (settings == NULL)
        return;
    g_free(settings->hub_host);
    g_free(settings);
}

char *
kr_settings_path(KrChannel channel, const char *config_dir)
{
    return g_build_filename(config_dir != NULL ? config_dir : g_get_user_config_dir(),
                            kr_channel_dir_name(channel), "settings.ini", NULL);
}

static gboolean
read_bool(GKeyFile *file, const char *group, const char *key, gboolean otherwise)
{
    g_autoptr(GError) error = NULL;
    gboolean value = g_key_file_get_boolean(file, group, key, &error);
    return error != NULL ? otherwise : value;
}

KrSettings *
kr_settings_load(const char *path)
{
    KrSettings *settings = kr_settings_new_default();
    g_autoptr(GKeyFile) file = g_key_file_new();
    if (path == NULL || !g_key_file_load_from_file(file, path, G_KEY_FILE_NONE, NULL))
        return settings;

    g_autofree char *theme = g_key_file_get_string(file, GROUP_LOOK, "theme", NULL);
    settings->theme = kr_theme_mode_from_string(theme);

    g_autofree char *host = g_key_file_get_string(file, GROUP_HUB, "host", NULL);
    if (host != NULL && *host != '\0')
        settings->hub_host = g_steal_pointer(&host);
    gint port = g_key_file_get_integer(file, GROUP_HUB, "port", NULL);
    settings->hub_port = port > 0 && port <= 65535 ? (guint16) port : 0;

    settings->notifications = read_bool(file, GROUP_ALERTS, "notifications", TRUE);
    settings->sounds = read_bool(file, GROUP_ALERTS, "sounds", TRUE);
    return settings;
}

gboolean
kr_settings_save(const KrSettings *settings, const char *path, GError **error)
{
    g_autoptr(GKeyFile) file = g_key_file_new();
    g_key_file_set_string(file, GROUP_LOOK, "theme", kr_theme_mode_to_string(settings->theme));
    if (settings->hub_host != NULL)
        g_key_file_set_string(file, GROUP_HUB, "host", settings->hub_host);
    if (settings->hub_port != 0)
        g_key_file_set_integer(file, GROUP_HUB, "port", settings->hub_port);
    g_key_file_set_boolean(file, GROUP_ALERTS, "notifications", settings->notifications);
    g_key_file_set_boolean(file, GROUP_ALERTS, "sounds", settings->sounds);

    g_autofree char *directory = g_path_get_dirname(path);
    if (g_mkdir_with_parents(directory, 0700) != 0) {
        g_set_error(error, G_FILE_ERROR, g_file_error_from_errno(errno),
                    "cannot create %s", directory);
        return FALSE;
    }
    return g_key_file_save_to_file(file, path, error);
}
