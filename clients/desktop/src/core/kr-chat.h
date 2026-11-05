/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-chat: the chat-first surface model for krypton desktop (ADR-0100).
 *
 * Mirrors the hub's POST /api/v1/chat/messages contract and the `/` command table so the
 * desktop's landing page works like Claude Code and Codex: a session sidebar of projects, a
 * conversational transcript with tool-call cards and inline gate approval cards (with spend
 * gates clearly badged), a slash-command composer, and live narration from the ledger feed.
 * Pure C17 + GLib + json-glib: no GTK, no network, no clock. */

#ifndef KR_CHAT_H
#define KR_CHAT_H

#include <glib.h>

#include "kr-model.h"

G_BEGIN_DECLS

#define KR_CHAT_ERROR (kr_chat_error_quark())
GQuark kr_chat_error_quark(void);

typedef enum {
    KR_CHAT_ERROR_INVALID, /* empty or overlong message */
    KR_CHAT_ERROR_PARSE,   /* malformed JSON response */
    KR_CHAT_ERROR_SHAPE,   /* JSON does not match the hub chat turn contract */
} KrChatError;

typedef struct {
    const char *slash;       /* without leading '/', e.g. "status" */
    const char *usage;       /* e.g. "/status [project-id]" */
    const char *title;       /* e.g. "Project status" */
    const char *description; /* plain one-line explanation */
    const char *tool_name;   /* matching vibey_* tool name, or NULL for "/help" */
} KrChatSlashSpec;

typedef struct {
    char *name;         /* e.g. "vibey_status" */
    char *summary;      /* compact human summary of arguments and result */
    char *arguments_json;
    char *result_json;
} KrChatToolCall;

typedef struct {
    char *gate_id;
    char *project_id;
    char *kind;
    char *prompt;
    char **options;        /* NULL-terminated */
    char *default_answer;  /* NULL when none */
    char *grant_key;       /* e.g. "max_dollars" for a grant gate, else NULL */
    gboolean is_spend;     /* TRUE when answering requires the `spend` scope */
    char *requires_scope;  /* "spend" or "answer" */
} KrChatGateCard;

typedef struct {
    char *reply;           /* assistant text */
    char *project_id;      /* active project UUID in context, or NULL */
    GPtrArray *tool_calls; /* of KrChatToolCall, owning */
    GPtrArray *gates;      /* of KrChatGateCard, owning */
} KrChatTurn;

typedef struct {
    gint64 seq;
    char *kind;
    char *actor;
    char *summary; /* one-line narration for the chat feed */
} KrChatNarration;

typedef struct {
    char *project_id;
    gint64 last_seq;       /* 0 when no events in page */
    GPtrArray *events;     /* of KrChatNarration, owning */
} KrChatLedgerPage;

/* The `/` command table, in composer completion order. */
const KrChatSlashSpec *kr_chat_slash_commands(gsize *count);

/* Matches `/` commands whose slash name starts with `prefix` (with or without leading '/').
 * Returns a newly allocated NULL-terminated array of borrowed KrChatSlashSpec pointers;
 * free the array with g_free(). */
const KrChatSlashSpec **kr_chat_slash_complete(const char *prefix, gsize *count);

/* Builds the JSON request body for POST /api/v1/chat/messages. `project_id` and `request_id`
 * are optional (NULL when absent). Returns NULL with KR_CHAT_ERROR_INVALID when `message` is
 * empty or whitespace-only. */
char *kr_chat_request_body(const char *message, const char *project_id, const char *request_id,
                           GError **error);

/* Parses the JSON response of POST /api/v1/chat/messages. */
KrChatTurn *kr_chat_turn_parse(const char *json, gssize length, GError **error);

/* Parses the JSON response of GET /api/v1/projects/{id}/ledger/after into live narration lines. */
KrChatLedgerPage *kr_chat_ledger_page_parse(const char *json, gssize length, GError **error);

/* Formats a gate card's scope badge for display ("SPEND GATE · requires spend scope" or
 * "Gate · answer scope"). Static string: do not free. */
const char *kr_chat_gate_badge(const KrChatGateCard *card);

void kr_chat_tool_call_free(KrChatToolCall *call);
void kr_chat_gate_card_free(KrChatGateCard *card);
void kr_chat_turn_free(KrChatTurn *turn);
void kr_chat_narration_free(KrChatNarration *narration);
void kr_chat_ledger_page_free(KrChatLedgerPage *page);

G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrChatToolCall, kr_chat_tool_call_free)
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrChatGateCard, kr_chat_gate_card_free)
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrChatTurn, kr_chat_turn_free)
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrChatNarration, kr_chat_narration_free)
G_DEFINE_AUTOPTR_CLEANUP_FUNC(KrChatLedgerPage, kr_chat_ledger_page_free)

G_END_DECLS

#endif /* KR_CHAT_H */
