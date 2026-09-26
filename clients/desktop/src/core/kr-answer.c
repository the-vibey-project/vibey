/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-answer.h"

#include <json-glib/json-glib.h>
#include <math.h>
#include <stdlib.h>

G_DEFINE_QUARK(kr-answer-error-quark, kr_answer_error)

typedef struct {
    const char *kind;
    KrAnswerShape shape;
    const char *grant_key;
} AnswerRule;

/* Mirrors ANSWER_RULES in src/vibey/cli/gate_answers.py. */
static const AnswerRule RULES[] = {
    {"question", KR_ANSWER_DEFAULTS, NULL},
    {"approval", KR_ANSWER_VERDICT, NULL},
    {"deploy_demo_review", KR_ANSWER_VERDICT, NULL},
    {"choice", KR_ANSWER_CHOICE, NULL},
    {"deploy_interview", KR_ANSWER_CHOICE, NULL},
    {"deploy_failure_triage", KR_ANSWER_CHOICE, NULL},
    {"bus_dead_lettered", KR_ANSWER_CHOICE, NULL},
    {"deploy_acceptance", KR_ANSWER_CHOICE, NULL},
    {"budget_exhausted", KR_ANSWER_GRANT, "max_dollars"},
    {"escalation_exhausted", KR_ANSWER_GRANT, "max_attempts"},
    {"attempts_exhausted", KR_ANSWER_GRANT, "max_attempts"},
    {"verify_repair_exhausted", KR_ANSWER_GRANT, "max_rounds"},
    {"integrate_repair_exhausted", KR_ANSWER_GRANT, "max_rounds"},
    {"delivery_exhausted", KR_ANSWER_ANY, NULL},
    {"research_evidence", KR_ANSWER_ANY, NULL},
    {"engine_misconfigured", KR_ANSWER_ANY, NULL},
    {"ultra_needs_cap", KR_ANSWER_ANY, NULL},
};

KrAnswerShape
kr_answer_shape(const char *kind, const char **grant_key)
{
    for (size_t i = 0; kind != NULL && i < G_N_ELEMENTS(RULES); i++) {
        if (g_str_equal(RULES[i].kind, kind)) {
            if (grant_key != NULL)
                *grant_key = RULES[i].grant_key;
            return RULES[i].shape;
        }
    }
    if (grant_key != NULL)
        *grant_key = NULL;
    return KR_ANSWER_FREE_FORM;
}

static char *
one_member(const char *key, JsonNode *value)
{
    g_autoptr(JsonObject) object = json_object_new();
    json_object_set_member(object, key, value);
    g_autoptr(JsonNode) node = json_node_init_object(json_node_alloc(), object);
    return json_to_string(node, FALSE);
}

char *
kr_answer_build(const char *kind, const char *value, GError **error)
{
    const char *key = NULL;
    switch (kr_answer_shape(kind, &key)) {
    case KR_ANSWER_DEFAULTS:
        g_set_error_literal(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_UNSUPPORTED,
                            "this is the design interview: answer it with vibey answer --defaults "
                            "or in the interview itself");
        return NULL;
    case KR_ANSWER_VERDICT:
    case KR_ANSWER_CHOICE: {
        if (value == NULL || *value == '\0') {
            g_set_error_literal(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID,
                                "choose one of the gate's options");
            return NULL;
        }
        const char *member = kr_answer_shape(kind, NULL) == KR_ANSWER_VERDICT ? "verdict"
                                                                             : "choice";
        return one_member(member, json_node_init_string(json_node_alloc(), value));
    }
    case KR_ANSWER_GRANT: {
        char *end = NULL;
        double bound = value == NULL ? NAN : g_ascii_strtod(value, &end);
        if (value == NULL || end == value || *end != '\0' || !isfinite(bound) || bound < 0) {
            g_set_error(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID,
                        "a new %s is a number, zero or more", key);
            return NULL;
        }
        JsonNode *number = json_node_alloc();
        if (bound == floor(bound) && bound < 9007199254740992.0)
            json_node_init_int(number, (gint64) bound);
        else
            json_node_init_double(number, bound);
        return one_member(key, number);
    }
    case KR_ANSWER_ANY:
        return g_strdup("{}");
    case KR_ANSWER_FREE_FORM:
    default: {
        g_autoptr(JsonParser) parser = json_parser_new_immutable();
        if (value == NULL || !json_parser_load_from_data(parser, value, -1, NULL) ||
            !JSON_NODE_HOLDS_OBJECT(json_parser_get_root(parser))) {
            g_set_error_literal(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID,
                                "write the answer as a JSON object");
            return NULL;
        }
        return json_to_string(json_parser_get_root(parser), FALSE);
    }
    }
}

char *
kr_answer_body(const char *answer_json, const char *request_id, GError **error)
{
    g_autoptr(JsonParser) parser = json_parser_new_immutable();
    if (answer_json == NULL || !json_parser_load_from_data(parser, answer_json, -1, NULL) ||
        !JSON_NODE_HOLDS_OBJECT(json_parser_get_root(parser))) {
        g_set_error_literal(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID,
                            "the answer is not a JSON object");
        return NULL;
    }
    if (request_id == NULL || *request_id == '\0') {
        g_set_error_literal(error, KR_ANSWER_ERROR, KR_ANSWER_ERROR_INVALID,
                            "an answer carries a request id");
        return NULL;
    }
    g_autoptr(JsonObject) body = json_object_new();
    json_object_set_member(body, "answer", json_node_copy(json_parser_get_root(parser)));
    json_object_set_string_member(body, "request_id", request_id);
    g_autoptr(JsonNode) node = json_node_init_object(json_node_alloc(), body);
    return json_to_string(node, FALSE);
}

char *
kr_answer_request_id(void)
{
    return g_uuid_string_random();
}
