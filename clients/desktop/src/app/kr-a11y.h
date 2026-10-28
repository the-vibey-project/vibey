/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-a11y: the one way a control gets the name a screen reader announces. GTK builds a name
 * for some widgets from their contents, but not reliably for an icon-only button, and a
 * tooltip is a hint shown to the pointer, not a name. tests/test-accessible-names.c fails
 * when an icon-only control in src/app is created without a call to this (#1699). */

#ifndef KR_A11Y_H
#define KR_A11Y_H

#include <gtk/gtk.h>

G_BEGIN_DECLS

static inline void
kr_a11y_name(GtkWidget *widget, const char *name)
{
    gtk_accessible_update_property(GTK_ACCESSIBLE(widget), GTK_ACCESSIBLE_PROPERTY_LABEL, name,
                                   -1);
}

static inline void
kr_a11y_name_with_hint(GtkWidget *widget, const char *name, const char *hint)
{
    gtk_accessible_update_property(GTK_ACCESSIBLE(widget), GTK_ACCESSIBLE_PROPERTY_LABEL, name,
                                   GTK_ACCESSIBLE_PROPERTY_DESCRIPTION, hint, -1);
}

G_END_DECLS

#endif /* KR_A11Y_H */
