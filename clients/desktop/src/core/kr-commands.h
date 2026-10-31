/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-commands: every command krypton offers, as one table. The header menu, the keyboard
 * shortcuts dialog and the registered accelerators all read it, so a command cannot be in
 * one and missing from another (#1699). Pure data: no GTK here; the app turns an accelerator
 * string into what a person reads. */

#ifndef KR_COMMANDS_H
#define KR_COMMANDS_H

#include <glib.h>

G_BEGIN_DECLS

typedef struct {
    const char *action;               /* the application action, without the "app." prefix */
    const char *label;                /* what a person reads, in the menu and the dialog */
    const char *group;                /* the heading the shortcuts dialog files it under */
    const char *const *accelerators; /* GTK accelerator strings, NULL-terminated; may be empty */
} KrCommand;

/* The whole table, in the order the shortcuts dialog lists it. */
const KrCommand *kr_commands(gsize *count);

/* The command for an action name, or NULL. */
const KrCommand *kr_command_find(const char *action);

/* The distinct group headings, in first-appearance order, NULL-terminated. Owned by the table. */
const char *const *kr_command_groups(void);

G_END_DECLS

#endif /* KR_COMMANDS_H */
