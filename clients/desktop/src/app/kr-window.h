/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-window: the main window. A sidebar of places (AdwNavigationSplitView, which folds to
 * one pane on a narrow window) and a page per place, each redrawn from the state. */

#ifndef KR_WINDOW_H
#define KR_WINDOW_H

#include "kr-app.h"

G_BEGIN_DECLS

/* The places, in sidebar order. Each is also a page name ("chat", "projects", "gates", ...). */
#define KR_WINDOW_PAGES 10
extern const char *const kr_window_page_names[KR_WINDOW_PAGES];

GtkWidget *kr_window_new(KrApp *app);
void kr_window_show_page(GtkWidget *window, const char *name);
void kr_window_toast(GtkWidget *window, const char *text);
/* Appends a chat turn, error or live ledger page to the Chat view. */
void kr_window_chat_turn(GtkWidget *window, const char *user_message, const KrChatTurn *turn);
void kr_window_chat_error(GtkWidget *window, const char *user_message, const char *error_text);
void kr_window_chat_ledger(GtkWidget *window, const KrChatLedgerPage *ledger);
void kr_window_chat_focus(GtkWidget *window);
/* Ask what to build and what to call it, then start the project (Ctrl+N). */
void kr_window_start_dialog(GtkWidget *window);
/* Say what an unwind cancels and that it cannot be undone; on confirmation, do it. */
void kr_window_confirm_unwind(GtkWidget *window, const char *project_id, const char *name,
                              const char *text);
/* The About dialog. */
void kr_window_about(GtkWidget *window);
/* The keyboard shortcuts, listed from the command table (Ctrl+?). */
void kr_window_shortcuts(GtkWidget *window);
/* The hubs seen on the network changed: redraw the Devices page. */
void kr_window_devices_changed(GtkWidget *window);

G_END_DECLS

#endif /* KR_WINDOW_H */
