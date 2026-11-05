/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* kr-chat: see kr-chat.h. */

#include "kr-chat.h"

#include <json-glib/json-glib.h>
#include <string.h>

#define MAX_CHAT_MESSAGE 4000

G_DEFINE_QUARK(kr-chat-error-quark, kr_chat_error)

/* Mirrors CHAT_SLASH_COMMANDS in src/vibey/domain/hub_chat.py. */
static const KrChatSlashSpec SLASH_COMMANDS[] = {
    {"projects", "/projects", "List projects",
     "List every project on this hub with its phase and open gate count.", "vibey_projects"},
    {"status", "/status [project-id]", "Project status",
     "Show a project's phase, cycle, queue depth and engine circuits.", "vibey_status"},
    {"gates", "/gates [project-id]", "Open gates",
     "List open human gates waiting for your answer.", "vibey_gates"},
    {"answer", "/answer <gate-id> <choice|json>", "Answer a gate",
     "Answer an open human gate once.", "vibey_answer_gate"},
    {"budget", "/budget [project-id]", "Project budget",
     "Show a project's budget caps and spend (read-only).", "vibey_budget"},
    {"queue", "/queue [project-id]", "Project queue",
     "List a project's queued and running jobs in claim order.", "vibey_queue"},
    {"ledger", "/ledger [project-id] [search text]", "Search ledger",
     "Search a project's append-only ledger events.", "vibey_ledger"},
    {"loops", "/loops", "Loops and engines",
     "Show the configured loops, engines and effort levels.", "vibey_loops"},
    {"lanes", "/lanes", "Active lanes",
     "List the runner lanes active on this computer.", "vibey_lanes"},
    {"doctor", "/doctor", "Hub health checks",
     "Run the hub's self-checks.", "vibey_doctor"},
    {"new", "/new <name> <what to build>", "Start a project",
     "Create and enqueue a new project on the host.", "vibey_start_project"},
    {"start", "/start [project-id]", "Resume project worker",
     "Start or resume a project's worker.", "vibey_start_work"},
    {"pause", "/pause [project-id]", "Pause project worker",
     "Stop a project's own workers.", "vibey_pause_work"},
    {"abandon", "/abandon [project-id] [--confirm] <reason>", "Unwind a project",
     "Preview (or with --confirm, execute) unwinding a project.", "vibey_abandon_project"},
    {"help", "/help", "Show chat commands",
     "List every slash command and conversational shortcut.", NULL},
};

const KrChatSlashSpec *
kr_chat_slash_commands(gsize *count)
{
    if (count != NULL)
        *count = G_N_ELEMENTS(SLASH_COMMANDS);
    return SLASH_COMMANDS;
}

const KrChatSlashSpec **
kr_chat_slash_complete(const char *prefix, gsize *count)
{
    const char *needle = prefix != NULL ? prefix : "";
    while (*needle == ' ' || *needle == '\t')
        needle++;
    if (*needle == '/')
        needle++;
    /* Match only the command token before any space. */
    gsize token_len = strcspn(needle, " \t\r\n");
    g_autofree char *lower = g_ascii_strdown(needle, (gssize) token_len);

    const KrChatSlashSpec **matches = g_new0(const KrChatSlashSpec *, G_N_ELEMENTS(SLASH_COMMANDS) + 1);
    gsize matched = 0;
    for (gsize i = 0; i < G_N_ELEMENTS(SLASH_COMMANDS); i++) {
        if (lower[0] == '\0' || g_str_has_prefix(SLASH_COMMANDS[i].slash, lower))
            matches[matched++] = &SLASH_COMMANDS[i];
    }
    if (count != NULL)
        *count = matched;
    return matches;
}

char *
kr_chat_request_body(const char *message, const char *project_id, const char *request_id,
                     GError **error)
{
    if (message == NULL) {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_INVALID,
                            "write a message or a /command");
        return NULL;
    }
    g_autofree char *trimmed = g_strstrip(g_strdup(message));
    if (trimmed[0] == '\0') {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_INVALID,
                            "write a message or a /command");
        return NULL;
    }
    if (g_utf8_strlen(trimmed, -1) > MAX_CHAT_MESSAGE) {
        g_set_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_INVALID,
                    "a chat message is at most %d characters", MAX_CHAT_MESSAGE);
        return NULL;
    }
    g_autoptr(JsonObject) body = json_object_new();
    json_object_set_string_member(body, "message", trimmed);
    if (project_id != NULL && project_id[0] != '\0')
        json_object_set_string_member(body, "project_id", project_id);
    if (request_id != NULL && request_id[0] != '\0')
        json_object_set_string_member(body, "request_id", request_id);
    g_autoptr(JsonNode) node = json_node_init_object(json_node_alloc(), body);
    return json_to_string(node, FALSE);
}

static char *
dup_string_member(JsonObject *obj, const char *member)
{
    if (!json_object_has_member(obj, member))
        return NULL;
    JsonNode *node = json_object_get_member(obj, member);
    if (node == NULL || json_node_is_null(node) || json_node_get_value_type(node) != G_TYPE_STRING)
        return NULL;
    return g_strdup(json_node_get_string(node));
}

static char *
node_to_compact_json(JsonNode *node)
{
    if (node == NULL || json_node_is_null(node))
        return g_strdup("{}");
    return json_to_string(node, FALSE);
}

static KrChatToolCall *
parse_tool_call(JsonObject *obj)
{
    const char *name = json_object_get_string_member_with_default(obj, "name", "");
    if (name[0] == '\0')
        return NULL;
    KrChatToolCall *call = g_new0(KrChatToolCall, 1);
    call->name = g_strdup(name);
    call->arguments_json = node_to_compact_json(json_object_get_member(obj, "arguments"));
    call->result_json = node_to_compact_json(json_object_get_member(obj, "result"));
    call->summary = g_strdup_printf("%s(%s)", call->name, call->arguments_json);
    return call;
}

static char **
parse_string_array(JsonArray *arr)
{
    guint len = arr != NULL ? json_array_get_length(arr) : 0;
    char **out = g_new0(char *, len + 1);
    guint k = 0;
    for (guint i = 0; i < len; i++) {
        JsonNode *elem = json_array_get_element(arr, i);
        if (elem != NULL && json_node_get_value_type(elem) == G_TYPE_STRING)
            out[k++] = g_strdup(json_node_get_string(elem));
    }
    return out;
}

static KrChatGateCard *
parse_gate_card(JsonObject *obj)
{
    const char *gate_id = json_object_get_string_member_with_default(obj, "gate_id", "");
    const char *kind = json_object_get_string_member_with_default(obj, "kind", "");
    if (gate_id[0] == '\0' || kind[0] == '\0')
        return NULL;
    KrChatGateCard *card = g_new0(KrChatGateCard, 1);
    card->gate_id = g_strdup(gate_id);
    card->project_id = dup_string_member(obj, "project_id");
    card->kind = g_strdup(kind);
    card->prompt = g_strdup(json_object_get_string_member_with_default(obj, "prompt", ""));
    JsonNode *opts = json_object_get_member(obj, "options");
    card->options = parse_string_array(opts != NULL && JSON_NODE_HOLDS_ARRAY(opts)
                                           ? json_node_get_array(opts)
                                           : NULL);
    card->default_answer = dup_string_member(obj, "default_answer");
    card->grant_key = dup_string_member(obj, "grant_key");
    if (json_object_has_member(obj, "is_spend") &&
        json_node_get_value_type(json_object_get_member(obj, "is_spend")) == G_TYPE_BOOLEAN) {
        card->is_spend = json_object_get_boolean_member(obj, "is_spend");
    } else {
        KrGate probe = {.kind = (char *) kind};
        card->is_spend = kr_gate_spends(&probe);
    }
    char *req = dup_string_member(obj, "requires_scope");
    card->requires_scope = req != NULL ? req : g_strdup(card->is_spend ? "spend" : "answer");
    return card;
}

KrChatTurn *
kr_chat_turn_parse(const char *json, gssize length, GError **error)
{
    g_autoptr(JsonParser) parser = json_parser_new_immutable();
    if (json == NULL || !json_parser_load_from_data(parser, json, length, NULL)) {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_PARSE,
                            "the chat response is not valid JSON");
        return NULL;
    }
    JsonNode *root = json_parser_get_root(parser);
    if (root == NULL || !JSON_NODE_HOLDS_OBJECT(root)) {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE,
                            "the chat response is not a JSON object");
        return NULL;
    }
    JsonObject *obj = json_node_get_object(root);
    char *reply = dup_string_member(obj, "reply");
    if (reply == NULL) {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE,
                            "the chat response is missing `reply`");
        return NULL;
    }
    KrChatTurn *turn = g_new0(KrChatTurn, 1);
    turn->reply = reply;
    turn->project_id = dup_string_member(obj, "project_id");
    turn->tool_calls = g_ptr_array_new_with_free_func((GDestroyNotify) kr_chat_tool_call_free);
    turn->gates = g_ptr_array_new_with_free_func((GDestroyNotify) kr_chat_gate_card_free);

    if (json_object_has_member(obj, "tool_calls")) {
        JsonNode *tc_node = json_object_get_member(obj, "tool_calls");
        if (tc_node != NULL && JSON_NODE_HOLDS_ARRAY(tc_node)) {
            JsonArray *arr = json_node_get_array(tc_node);
            guint len = json_array_get_length(arr);
            for (guint i = 0; i < len; i++) {
                JsonNode *item = json_array_get_element(arr, i);
                if (item != NULL && JSON_NODE_HOLDS_OBJECT(item)) {
                    KrChatToolCall *call = parse_tool_call(json_node_get_object(item));
                    if (call != NULL)
                        g_ptr_array_add(turn->tool_calls, call);
                }
            }
        }
    }
    if (json_object_has_member(obj, "gates")) {
        JsonNode *g_node = json_object_get_member(obj, "gates");
        if (g_node != NULL && JSON_NODE_HOLDS_ARRAY(g_node)) {
            JsonArray *arr = json_node_get_array(g_node);
            guint len = json_array_get_length(arr);
            for (guint i = 0; i < len; i++) {
                JsonNode *item = json_array_get_element(arr, i);
                if (item != NULL && JSON_NODE_HOLDS_OBJECT(item)) {
                    KrChatGateCard *card = parse_gate_card(json_node_get_object(item));
                    if (card != NULL)
                        g_ptr_array_add(turn->gates, card);
                }
            }
        }
    }
    return turn;
}

static KrChatNarration *
parse_narration(JsonObject *obj)
{
    if (!json_object_has_member(obj, "seq") ||
        json_node_get_value_type(json_object_get_member(obj, "seq")) != G_TYPE_INT64)
        return NULL;
    gint64 seq = json_object_get_int_member(obj, "seq");
    const char *kind = json_object_get_string_member_with_default(obj, "kind", "Event");
    const char *actor = json_object_get_string_member_with_default(obj, "actor", "vibey");
    KrChatNarration *narration = g_new0(KrChatNarration, 1);
    narration->seq = seq;
    narration->kind = g_strdup(kind);
    narration->actor = g_strdup(actor);
    narration->summary = g_strdup_printf("#%" G_GINT64_FORMAT " %s (%s)", seq, kind, actor);
    return narration;
}

KrChatLedgerPage *
kr_chat_ledger_page_parse(const char *json, gssize length, GError **error)
{
    g_autoptr(JsonParser) parser = json_parser_new_immutable();
    if (json == NULL || !json_parser_load_from_data(parser, json, length, NULL)) {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_PARSE,
                            "the ledger feed page is not valid JSON");
        return NULL;
    }
    JsonNode *root = json_parser_get_root(parser);
    if (root == NULL || !JSON_NODE_HOLDS_OBJECT(root)) {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE,
                            "the ledger feed page is not a JSON object");
        return NULL;
    }
    JsonObject *obj = json_node_get_object(root);
    if (!json_object_has_member(obj, "events") ||
        !JSON_NODE_HOLDS_ARRAY(json_object_get_member(obj, "events"))) {
        g_set_error_literal(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE,
                            "the ledger feed page is missing `events`");
        return NULL;
    }
    KrChatLedgerPage *page = g_new0(KrChatLedgerPage, 1);
    page->project_id = dup_string_member(obj, "project_id");
    page->events = g_ptr_array_new_with_free_func((GDestroyNotify) kr_chat_narration_free);
    if (json_object_has_member(obj, "last_seq") &&
        json_node_get_value_type(json_object_get_member(obj, "last_seq")) == G_TYPE_INT64) {
        page->last_seq = json_object_get_int_member(obj, "last_seq");
    }
    JsonArray *events = json_node_get_array(json_object_get_member(obj, "events"));
    guint len = json_array_get_length(events);
    for (guint i = 0; i < len; i++) {
        JsonNode *item = json_array_get_element(events, i);
        if (item != NULL && JSON_NODE_HOLDS_OBJECT(item)) {
            KrChatNarration *narration = parse_narration(json_node_get_object(item));
            if (narration != NULL) {
                if (narration->seq > page->last_seq)
                    page->last_seq = narration->seq;
                g_ptr_array_add(page->events, narration);
            }
        }
    }
    return page;
}

const char *
kr_chat_gate_badge(const KrChatGateCard *card)
{
    if (card != NULL && card->is_spend)
        return "SPEND GATE · requires spend scope";
    return "Gate · answer scope";
}

void
kr_chat_tool_call_free(KrChatToolCall *call)
{
    if (call == NULL)
        return;
    g_free(call->name);
    g_free(call->summary);
    g_free(call->arguments_json);
    g_free(call->result_json);
    g_free(call);
}

void
kr_chat_gate_card_free(KrChatGateCard *card)
{
    if (card == NULL)
        return;
    g_free(card->gate_id);
    g_free(card->project_id);
    g_free(card->kind);
    g_free(card->prompt);
    g_strfreev(card->options);
    g_free(card->default_answer);
    g_free(card->grant_key);
    g_free(card->requires_scope);
    g_free(card);
}

void
kr_chat_turn_free(KrChatTurn *turn)
{
    if (turn == NULL)
        return;
    g_free(turn->reply);
    g_free(turn->project_id);
    if (turn->tool_calls != NULL)
        g_ptr_array_unref(turn->tool_calls);
    if (turn->gates != NULL)
        g_ptr_array_unref(turn->gates);
    g_free(turn);
}

void
kr_chat_narration_free(KrChatNarration *narration)
{
    if (narration == NULL)
        return;
    g_free(narration->kind);
    g_free(narration->actor);
    g_free(narration->summary);
    g_free(narration);
}

void
kr_chat_ledger_page_free(KrChatLedgerPage *page)
{
    if (page == NULL)
        return;
    g_free(page->project_id);
    if (page->events != NULL)
        g_ptr_array_unref(page->events);
    g_free(page);
}
