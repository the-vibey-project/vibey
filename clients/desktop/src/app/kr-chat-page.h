/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-chat-page: the chat-first workspace view for krypton desktop (ADR-0100).
 *
 * Modelled on the Claude Code and Codex desktop apps:
 * - Left session sidebar: every project as a conversation session (plus an "All projects"
 *   overview session and a "New project" button).
 * - Center transcript: user and assistant turns, tool-call cards showing which `vibey_*`
 *   tool ran and its JSON arguments/result, inline approval cards for open human gates (with
 *   `SPEND GATE` clearly badged), and live narration lines from the project's ledger feed.
 * - Bottom composer: `/` slash-command completion popover, entry row, and Send button. */

#ifndef KR_CHAT_PAGE_H
#define KR_CHAT_PAGE_H

#include "kr-app.h"

G_BEGIN_DECLS

GtkWidget *kr_chat_page_new(KrApp *app);

/* Redraws the session list and open-gate cards when app->state changes. */
void kr_chat_page_refresh(GtkWidget *page);

/* Appends a completed turn from POST /api/v1/chat/messages to the transcript. */
void kr_chat_page_append_turn(GtkWidget *page, const char *user_message, const KrChatTurn *turn);

/* Appends a refusal or transport error line to the transcript. */
void kr_chat_page_append_error(GtkWidget *page, const char *user_message, const char *error_text);

/* Appends new ledger events from the live feed as narration lines. */
void kr_chat_page_append_ledger(GtkWidget *page, const KrChatLedgerPage *ledger);

/* Focuses the bottom composer entry (Ctrl+L). */
void kr_chat_page_focus_composer(GtkWidget *page);

G_END_DECLS

#endif /* KR_CHAT_PAGE_H */
