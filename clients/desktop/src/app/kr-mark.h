/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-mark: the Krypton emblem, the krypton atom Kr-84, drawn live.
 *
 * 36 protons and 48 neutrons in the nucleus; 36 electrons on four shells of 2, 8, 18 and 8
 * (design/identity/krypton.svg is the still version). The electrons orbit slowly, and stand
 * still when the desktop asks for reduced motion (libadwaita's enable-animations). While
 * `busy` is set -- a lane is running -- the nucleus glows in the ULTRA colour. */

#ifndef KR_MARK_H
#define KR_MARK_H

#include <gtk/gtk.h>

G_BEGIN_DECLS

/* The electrons on each shell, innermost first. */
#define KR_MARK_SHELLS 4
extern const int kr_mark_shell_electrons[KR_MARK_SHELLS];

GtkWidget *kr_mark_new(int size);
void kr_mark_set_busy(GtkWidget *mark, gboolean busy);

G_END_DECLS

#endif /* KR_MARK_H */
