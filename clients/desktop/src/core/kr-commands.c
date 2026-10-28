/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-commands: see kr-commands.h. */

#include "kr-commands.h"

static const char *const ACCEL_REFRESH[] = {"<Control>r", "F5", NULL};
static const char *const ACCEL_GATES[] = {"<Control>g", NULL};
static const char *const ACCEL_SETTINGS[] = {"<Control>comma", NULL};
static const char *const ACCEL_START[] = {"<Control>n", NULL};
static const char *const ACCEL_SHORTCUTS[] = {"<Control>question", NULL};
static const char *const ACCEL_QUIT[] = {"<Control>q", NULL};
static const char *const NO_ACCEL[] = {NULL};

static const KrCommand COMMANDS[] = {
    {"start-project", "Start a project…", "Projects", ACCEL_START},
    {"show-gates", "Answer waiting gates", "Projects", ACCEL_GATES},
    {"open", "Open krypton", "Projects", NO_ACCEL},
    {"refresh", "Refresh", "View", ACCEL_REFRESH},
    {"settings", "Preferences", "View", ACCEL_SETTINGS},
    {"start-hub", "Start the hub", "Hub", NO_ACCEL},
    {"stop-hub", "Stop the hub", "Hub", NO_ACCEL},
    {"hub-status", "Hub status", "Hub", NO_ACCEL},
    {"shortcuts", "Keyboard shortcuts", "krypton", ACCEL_SHORTCUTS},
    {"about", "About krypton", "krypton", NO_ACCEL},
    {"quit", "Quit", "krypton", ACCEL_QUIT},
};

const KrCommand *
kr_commands(gsize *count)
{
    if (count != NULL)
        *count = G_N_ELEMENTS(COMMANDS);
    return COMMANDS;
}

const KrCommand *
kr_command_find(const char *action)
{
    for (gsize i = 0; i < G_N_ELEMENTS(COMMANDS); i++)
        if (g_strcmp0(COMMANDS[i].action, action) == 0)
            return &COMMANDS[i];
    return NULL;
}

const char *const *
kr_command_groups(void)
{
    static const char *groups[G_N_ELEMENTS(COMMANDS) + 1];
    static gsize filled = 0;
    if (g_once_init_enter(&filled)) {
        gsize n = 0;
        for (gsize i = 0; i < G_N_ELEMENTS(COMMANDS); i++) {
            gboolean seen = FALSE;
            for (gsize j = 0; j < n && !seen; j++)
                seen = g_strcmp0(groups[j], COMMANDS[i].group) == 0;
            if (!seen)
                groups[n++] = COMMANDS[i].group;
        }
        groups[n] = NULL;
        g_once_init_leave(&filled, 1);
    }
    return groups;
}
