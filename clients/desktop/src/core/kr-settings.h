/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-settings: what Krypton desktop remembers per device, and which channel it is.
 *
 * Themes: every Krypton GUI offers Light, Dark and System, System by default, following the
 * operating system live (the Beauty Bar, ADR-0062; the enum is the design tokens' own,
 * design/dist/c/vibey_tokens.h, ADR-0066). Channels: stable (from main) is the default;
 * nightly (from develop) installs beside it under its own app id, name and data directory.
 *
 * Settings live in a key file under the user's config directory, one per channel, so the
 * two channels never share state. Loading never fails: a missing or unreadable file gives
 * the defaults. */

#ifndef KR_SETTINGS_H
#define KR_SETTINGS_H

#include <glib.h>

#include "vibey_tokens.h"

G_BEGIN_DECLS

typedef enum {
    KR_CHANNEL_STABLE = 0,
    KR_CHANNEL_NIGHTLY = 1,
} KrChannel;

/* "io.github.the_vibey_project.Krypton", "...Krypton.Nightly". Static. */
const char *kr_channel_app_id(KrChannel channel);
/* "Krypton", "Krypton Nightly". Static. */
const char *kr_channel_display_name(KrChannel channel);
/* The directory name for this channel's data: "krypton", "krypton-nightly". Static. */
const char *kr_channel_dir_name(KrChannel channel);
/* "stable" or "nightly" (any case) -> the channel; anything else is stable, the default. */
KrChannel kr_channel_from_string(const char *text);

/* "system", "light", "dark". Static. */
const char *kr_theme_mode_to_string(VibeyThemeMode mode);
/* Any case; anything else is VIBEY_THEME_MODE_DEFAULT (System). */
VibeyThemeMode kr_theme_mode_from_string(const char *text);

typedef struct {
    VibeyThemeMode theme;
    char *hub_host; /* the hub last used; NULL means this computer's */
    guint16 hub_port;
    gboolean notifications; /* on by default */
    gboolean sounds;        /* on by default */
} KrSettings;

KrSettings *kr_settings_new_default(void);
void kr_settings_free(KrSettings *settings);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrSettings, kr_settings_free)

/* Where this channel's settings file is under `config_dir` (NULL: g_get_user_config_dir). */
char *kr_settings_path(KrChannel channel, const char *config_dir);

/* Reads the file at `path`; the defaults for anything missing or malformed. */
KrSettings *kr_settings_load(const char *path);

/* Writes atomically, creating the directory (mode 0700) when needed. */
gboolean kr_settings_save(const KrSettings *settings, const char *path, GError **error);

G_END_DECLS

#endif /* KR_SETTINGS_H */
