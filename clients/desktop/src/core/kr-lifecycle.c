/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-lifecycle.h"

#include <json-glib/json-glib.h>
#include <string.h>

G_DEFINE_QUARK(kr-lifecycle-error-quark, kr_lifecycle_error)

#define MAX_NAME 64

static gboolean
name_char(char c, gboolean first)
{
    if (g_ascii_isalnum(c))
        return TRUE;
    return !first && (c == '.' || c == '-' || c == '_');
}

const char *
kr_lifecycle_name_problem(const char *name)
{
    g_autofree char *trimmed = name != NULL ? g_strstrip(g_strdup(name)) : g_strdup("");
    if (*trimmed == '\0')
        return "Give the project a name, for example my-first-app.";
    gsize length = strlen(trimmed);
    gboolean ok = length <= MAX_NAME;
    for (gsize i = 0; ok && i < length; i++)
        ok = name_char(trimmed[i], i == 0);
    return ok ? NULL
              : "A name is letters, digits, dots, dashes and underscores, starts with a letter or "
                "digit, and is at most 64 characters. No spaces.";
}

static char *
to_json(JsonObject *object)
{
    g_autoptr(JsonNode) node = json_node_init_object(json_node_alloc(), object);
    return json_to_string(node, FALSE);
}

char *
kr_lifecycle_start_body(const char *name, const char *intake, GError **error)
{
    const char *problem = kr_lifecycle_name_problem(name);
    if (problem != NULL) {
        g_set_error_literal(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_INVALID, problem);
        return NULL;
    }
    g_autofree char *clean_name = g_strstrip(g_strdup(name));
    g_autofree char *clean_intake = intake != NULL ? g_strstrip(g_strdup(intake)) : g_strdup("");
    if (g_utf8_strlen(clean_intake, -1) > KR_LIFECYCLE_MAX_INTAKE) {
        g_set_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_INVALID,
                    "What to build is at most %d characters.", KR_LIFECYCLE_MAX_INTAKE);
        return NULL;
    }
    g_autoptr(JsonObject) body = json_object_new();
    json_object_set_string_member(body, "name", clean_name);
    if (*clean_intake != '\0')
        json_object_set_string_member(body, "intake", clean_intake);
    return to_json(body);
}

char *
kr_lifecycle_abandon_body(const char *reason, gboolean dry_run, GError **error)
{
    g_autofree char *clean = reason != NULL ? g_strstrip(g_strdup(reason)) : g_strdup("");
    if (*clean == '\0' || g_utf8_strlen(clean, -1) > KR_LIFECYCLE_MAX_REASON) {
        g_set_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_INVALID,
                    "Say why, in 1 to %d characters. It is recorded with the project.",
                    KR_LIFECYCLE_MAX_REASON);
        return NULL;
    }
    g_autoptr(JsonObject) body = json_object_new();
    json_object_set_string_member(body, "reason", clean);
    json_object_set_boolean_member(body, "dry_run", dry_run);
    return to_json(body);
}

static JsonObject *
parse_object(const char *json, const char *what, GError **error)
{
    g_autoptr(JsonParser) parser = json_parser_new_immutable();
    if (json == NULL || !json_parser_load_from_data(parser, json, -1, NULL) ||
        !JSON_NODE_HOLDS_OBJECT(json_parser_get_root(parser))) {
        g_set_error(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_ANSWER,
                    "The hub did not send %s.", what);
        return NULL;
    }
    return json_object_ref(json_node_get_object(json_parser_get_root(parser)));
}

static const char *
string_member(JsonObject *object, const char *key)
{
    if (!json_object_has_member(object, key))
        return NULL;
    JsonNode *node = json_object_get_member(object, key);
    return JSON_NODE_HOLDS_VALUE(node) && json_node_get_value_type(node) == G_TYPE_STRING
               ? json_node_get_string(node)
               : NULL;
}

static guint
list_length(JsonObject *object, const char *key)
{
    if (!json_object_has_member(object, key))
        return 0;
    JsonNode *node = json_object_get_member(object, key);
    return JSON_NODE_HOLDS_ARRAY(node) ? json_array_get_length(json_node_get_array(node)) : 0;
}

KrCreated *
kr_lifecycle_parse_created(const char *json, GError **error)
{
    g_autoptr(JsonObject) object = parse_object(json, "a project", error);
    if (object == NULL)
        return NULL;
    const char *id = string_member(object, "project_id");
    if (id == NULL) {
        g_set_error_literal(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_ANSWER,
                            "The hub did not send a project.");
        return NULL;
    }
    KrCreated *created = g_new0(KrCreated, 1);
    created->project_id = g_strdup(id);
    created->name = g_strdup(string_member(object, "name") != NULL ? string_member(object, "name") : id);
    created->outcome = g_strdup(string_member(object, "outcome") != NULL ? string_member(object, "outcome") : "");
    return created;
}

void
kr_created_free(KrCreated *created)
{
    if (created == NULL)
        return;
    g_free(created->project_id);
    g_free(created->name);
    g_free(created->outcome);
    g_free(created);
}

KrAbandonReport *
kr_lifecycle_parse_report(const char *json, GError **error)
{
    g_autoptr(JsonObject) object = parse_object(json, "an unwind report", error);
    if (object == NULL)
        return NULL;
    const char *id = string_member(object, "project_id");
    if (id == NULL) {
        g_set_error_literal(error, KR_LIFECYCLE_ERROR, KR_LIFECYCLE_ERROR_ANSWER,
                            "The hub did not send an unwind report.");
        return NULL;
    }
    KrAbandonReport *report = g_new0(KrAbandonReport, 1);
    report->name = g_strdup(string_member(object, "name") != NULL ? string_member(object, "name") : id);
    report->from = g_strdup(string_member(object, "from") != NULL ? string_member(object, "from") : "");
    report->already_abandoned = json_object_has_member(object, "already_abandoned") &&
                                json_object_get_boolean_member(object, "already_abandoned");
    report->dry_run = json_object_has_member(object, "dry_run") &&
                      json_object_get_boolean_member(object, "dry_run");
    report->cancelled_jobs = list_length(object, "cancelled_jobs");
    report->withdrawn_gates = list_length(object, "withdrawn_gates");
    return report;
}

void
kr_abandon_report_free(KrAbandonReport *report)
{
    if (report == NULL)
        return;
    g_free(report->name);
    g_free(report->from);
    g_free(report);
}

char *
kr_lifecycle_confirm_text(const KrAbandonReport *report)
{
    if (report->already_abandoned)
        return g_strdup_printf("\"%s\" is already unwound. Nothing changes.", report->name);
    return g_strdup_printf(
        "\"%s\"%s%s. Unwinding cancels %u queued or running %s and withdraws %u waiting %s, then "
        "records why on its ledger. This cannot be undone; the work already on disk is left as "
        "it is.",
        report->name, *report->from != '\0' ? " is in " : "", report->from,
        report->cancelled_jobs, report->cancelled_jobs == 1 ? "job" : "jobs",
        report->withdrawn_gates, report->withdrawn_gates == 1 ? "question" : "questions");
}

char *
kr_lifecycle_message(const char *json, const char *fallback)
{
    g_autoptr(JsonObject) object = parse_object(json, "a message", NULL);
    const char *message = object != NULL ? string_member(object, "message") : NULL;
    return g_strdup(message != NULL && *message != '\0' ? message : fallback);
}
