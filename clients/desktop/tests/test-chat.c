/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include <glib.h>
#include <string.h>

#include "kr-chat.h"

static void
test_slash_commands_and_completion(void)
{
    gsize count = 0;
    const KrChatSlashSpec *all = kr_chat_slash_commands(&count);
    g_assert_nonnull(all);
    g_assert_cmpuint(count, ==, 15);
    g_assert_nonnull(kr_chat_slash_commands(NULL));
    for (gsize i = 0; i < count; i++) {
        g_assert_nonnull(all[i].slash);
        g_assert_true(all[i].slash[0] != '\0');
        g_assert_true(g_str_has_prefix(all[i].usage, "/"));
        g_assert_nonnull(all[i].title);
        g_assert_nonnull(all[i].description);
    }

    gsize matched = 0;
    g_autofree const KrChatSlashSpec **empty_matches = kr_chat_slash_complete(NULL, &matched);
    g_assert_cmpuint(matched, ==, count);

    g_autofree const KrChatSlashSpec **slash_only = kr_chat_slash_complete("  /", &matched);
    g_assert_cmpuint(matched, ==, count);

    g_autofree const KrChatSlashSpec **st_matches = kr_chat_slash_complete("/st", &matched);
    g_assert_cmpuint(matched, ==, 2);
    g_assert_cmpstr(st_matches[0]->slash, ==, "status");
    g_assert_cmpstr(st_matches[1]->slash, ==, "start");
    g_assert_null(st_matches[2]);

    g_autofree const KrChatSlashSpec **with_args = kr_chat_slash_complete("/BUDGET 123", NULL);
    g_assert_nonnull(with_args[0]);
    g_assert_cmpstr(with_args[0]->slash, ==, "budget");

    g_autofree const KrChatSlashSpec **none = kr_chat_slash_complete("/zzz", &matched);
    g_assert_cmpuint(matched, ==, 0);
    g_assert_null(none[0]);
}

static void
test_request_body(void)
{
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_chat_request_body(NULL, NULL, NULL, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_INVALID);
    g_clear_error(&error);

    g_assert_null(kr_chat_request_body("   \t\n ", NULL, NULL, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_INVALID);
    g_clear_error(&error);

    g_autofree char *huge = g_strnfill(4001, 'a');
    g_assert_null(kr_chat_request_body(huge, NULL, NULL, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_INVALID);
    g_clear_error(&error);

    g_autofree char *minimal = kr_chat_request_body("  /status  ", "", "", &error);
    g_assert_no_error(error);
    g_assert_cmpstr(minimal, ==, "{\"message\":\"/status\"}");

    g_autofree char *full = kr_chat_request_body("/gates", "proj-1", "req-1", &error);
    g_assert_no_error(error);
    g_assert_nonnull(strstr(full, "\"message\":\"/gates\""));
    g_assert_nonnull(strstr(full, "\"project_id\":\"proj-1\""));
    g_assert_nonnull(strstr(full, "\"request_id\":\"req-1\""));
}

static void
test_turn_parse_and_badges(void)
{
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_chat_turn_parse(NULL, -1, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_PARSE);
    g_clear_error(&error);

    g_assert_null(kr_chat_turn_parse("{bad", -1, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_PARSE);
    g_clear_error(&error);

    g_assert_null(kr_chat_turn_parse("[]", -1, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE);
    g_clear_error(&error);

    g_assert_null(kr_chat_turn_parse("{\"project_id\":\"p\"}", -1, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE);
    g_clear_error(&error);

    const char *payload =
        "{"
        "\"reply\":\"alpha is in BUILD (cycle 1).\","
        "\"project_id\":\"11111111-1111-4111-8111-111111111111\","
        "\"tool_calls\":["
        "  {\"name\":\"vibey_status\",\"arguments\":{\"project_id\":\"p\"},\"result\":{\"ok\":true}},"
        "  {\"name\":\"\"},"
        "  \"ignored\""
        "],"
        "\"gates\":["
        "  {"
        "    \"gate_id\":\"g1\","
        "    \"project_id\":\"p1\","
        "    \"kind\":\"budget_exhausted\","
        "    \"prompt\":\"Raise cap?\","
        "    \"options\":[\"25\",\"50\",123],"
        "    \"default_answer\":null,"
        "    \"grant_key\":\"max_dollars\","
        "    \"is_spend\":true,"
        "    \"requires_scope\":\"spend\""
        "  },"
        "  {"
        "    \"gate_id\":\"g2\","
        "    \"kind\":\"approval\","
        "    \"prompt\":\"Ship it?\","
        "    \"options\":[\"accept\",\"changes\"]"
        "  },"
        "  {\"gate_id\":\"\"}"
        "]"
        "}";

    g_autoptr(KrChatTurn) turn = kr_chat_turn_parse(payload, -1, &error);
    g_assert_no_error(error);
    g_assert_nonnull(turn);
    g_assert_cmpstr(turn->reply, ==, "alpha is in BUILD (cycle 1).");
    g_assert_cmpstr(turn->project_id, ==, "11111111-1111-4111-8111-111111111111");
    g_assert_cmpuint(turn->tool_calls->len, ==, 1);

    const KrChatToolCall *call = g_ptr_array_index(turn->tool_calls, 0);
    g_assert_cmpstr(call->name, ==, "vibey_status");
    g_assert_nonnull(strstr(call->summary, "vibey_status("));

    g_assert_cmpuint(turn->gates->len, ==, 2);
    const KrChatGateCard *spend_card = g_ptr_array_index(turn->gates, 0);
    g_assert_true(spend_card->is_spend);
    g_assert_cmpstr(spend_card->requires_scope, ==, "spend");
    g_assert_cmpstr(spend_card->grant_key, ==, "max_dollars");
    g_assert_cmpstr(spend_card->options[0], ==, "25");
    g_assert_cmpstr(spend_card->options[1], ==, "50");
    g_assert_null(spend_card->options[2]);
    g_assert_cmpstr(kr_chat_gate_badge(spend_card), ==, "SPEND GATE · requires spend scope");

    const KrChatGateCard *plain_card = g_ptr_array_index(turn->gates, 1);
    g_assert_false(plain_card->is_spend);
    g_assert_cmpstr(plain_card->requires_scope, ==, "answer");
    g_assert_cmpstr(kr_chat_gate_badge(plain_card), ==, "Gate · answer scope");
    g_assert_cmpstr(kr_chat_gate_badge(NULL), ==, "Gate · answer scope");

    kr_chat_tool_call_free(NULL);
    kr_chat_gate_card_free(NULL);
    kr_chat_turn_free(NULL);
}

static void
test_ledger_page_parse(void)
{
    g_autoptr(GError) error = NULL;
    g_assert_null(kr_chat_ledger_page_parse(NULL, -1, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_PARSE);
    g_clear_error(&error);

    g_assert_null(kr_chat_ledger_page_parse("[]", -1, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE);
    g_clear_error(&error);

    g_assert_null(kr_chat_ledger_page_parse("{\"project_id\":\"p\"}", -1, &error));
    g_assert_error(error, KR_CHAT_ERROR, KR_CHAT_ERROR_SHAPE);
    g_clear_error(&error);

    const char *json =
        "{"
        "\"project_id\":\"p1\","
        "\"last_seq\":7,"
        "\"events\":["
        "  {\"seq\":6,\"kind\":\"JobStarted\",\"actor\":\"worker-1\"},"
        "  {\"seq\":9,\"kind\":\"GateRaised\",\"actor\":\"review\"},"
        "  {\"kind\":\"MissingSeq\"}"
        "]"
        "}";

    g_autoptr(KrChatLedgerPage) page = kr_chat_ledger_page_parse(json, -1, &error);
    g_assert_no_error(error);
    g_assert_nonnull(page);
    g_assert_cmpstr(page->project_id, ==, "p1");
    g_assert_cmpint(page->last_seq, ==, 9);
    g_assert_cmpuint(page->events->len, ==, 2);

    const KrChatNarration *first = g_ptr_array_index(page->events, 0);
    g_assert_cmpint(first->seq, ==, 6);
    g_assert_cmpstr(first->summary, ==, "#6 JobStarted (worker-1)");

    kr_chat_narration_free(NULL);
    kr_chat_ledger_page_free(NULL);
}

int
main(int argc, char **argv)
{
    g_test_init(&argc, &argv, NULL);
    g_test_add_func("/chat/slash-commands", test_slash_commands_and_completion);
    g_test_add_func("/chat/request-body", test_request_body);
    g_test_add_func("/chat/turn-parse", test_turn_parse_and_badges);
    g_test_add_func("/chat/ledger-page-parse", test_ledger_page_parse);
    return g_test_run();
}
