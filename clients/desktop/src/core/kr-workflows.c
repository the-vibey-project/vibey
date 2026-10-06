/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-workflows.h"

#include <json-glib/json-glib.h>
#include <string.h>

#include "kr-hub.h"

G_DEFINE_QUARK(kr-workflows-error-quark, kr_workflows_error)

/* The hub's names for the states, in KrWorkflowState's order (RemoteState). */
static const char *const STATE_NAMES[] = {"queued", "running", "done", "failed"};

void
kr_workflow_run_free(KrWorkflowRun *run)
{
    if (run == NULL)
        return;
    g_free(run->request_id);
    g_free(run->url);
    g_free(run->output);
    g_free(run->errors);
    g_free(run->detail);
    g_free(run);
}

KrWorkflowRun *
kr_workflow_run_copy(const KrWorkflowRun *run)
{
    KrWorkflowRun *copy = g_new0(KrWorkflowRun, 1);
    copy->request_id = g_strdup(run->request_id);
    copy->state = run->state;
    copy->url = g_strdup(run->url);
    copy->has_exit_code = run->has_exit_code;
    copy->exit_code = run->exit_code;
    copy->output = g_strdup(run->output);
    copy->errors = g_strdup(run->errors);
    copy->detail = g_strdup(run->detail);
    return copy;
}

/* ---- the command line ------------------------------------------------------------------ */

static gboolean
command_error(GError **error, const char *message)
{
    g_set_error_literal(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_COMMAND, message);
    return FALSE;
}

static gboolean
too_many(GError **error, guint words)
{
    g_set_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_COMMAND,
                "A command sent to GitHub is at most %d words; this one has %u.",
                KR_WORKFLOWS_MAX_WORDS, words);
    return FALSE;
}

static gboolean
is_workflows_flag(const char *word)
{
    return g_str_equal(word, "-w") || g_str_equal(word, "--workflows");
}

/* Drops a leading `vibey`, then `-w`/`--workflows` among the options before the command:
 * the hub takes the command line without either. */
static void
drop_invocation(GPtrArray *words)
{
    if (words->len > 0 && g_str_equal(g_ptr_array_index(words, 0), "vibey"))
        g_ptr_array_remove_index(words, 0);
    guint index = 0;
    while (index < words->len) {
        const char *word = g_ptr_array_index(words, index);
        if (word[0] != '-' || g_str_equal(word, "-") || g_str_equal(word, "--"))
            break;
        if (is_workflows_flag(word))
            g_ptr_array_remove_index(words, index);
        else
            index++;
    }
}

char **
kr_workflows_split(const char *line, GError **error)
{
    g_autoptr(GPtrArray) words = g_ptr_array_new_with_free_func(g_free);
    g_autoptr(GString) word = NULL; /* NULL between words */
    gboolean quoted = FALSE;
    for (const char *c = line != NULL ? line : ""; *c != '\0'; c++) {
        if (quoted) {
            if (*c == '\\' && (c[1] == '"' || c[1] == '\\'))
                g_string_append_c(word, *++c);
            else if (*c == '"')
                quoted = FALSE;
            else
                g_string_append_c(word, *c);
            continue;
        }
        if (g_ascii_isspace(*c)) {
            if (word != NULL)
                g_ptr_array_add(words, g_string_free(g_steal_pointer(&word), FALSE));
            continue;
        }
        if (word == NULL)
            word = g_string_new(NULL);
        if (*c == '"')
            quoted = TRUE;
        else
            g_string_append_c(word, *c);
    }
    if (quoted) {
        command_error(error, "A double quote in that command line is not closed.");
        return NULL;
    }
    if (word != NULL)
        g_ptr_array_add(words, g_string_free(g_steal_pointer(&word), FALSE));
    drop_invocation(words);
    if (words->len == 0) {
        command_error(error, "Type a vibey command to run on GitHub, such as: status --json");
        return NULL;
    }
    if (words->len > KR_WORKFLOWS_MAX_WORDS) {
        too_many(error, words->len);
        return NULL;
    }
    g_ptr_array_add(words, NULL);
    return (char **) g_ptr_array_free(g_steal_pointer(&words), FALSE);
}

char *
kr_workflows_run_body(const char *const *argv, GError **error)
{
    guint count = argv != NULL ? g_strv_length((char **) argv) : 0;
    if (count == 0) {
        command_error(error, "Type a vibey command to run on GitHub, such as: status --json");
        return NULL;
    }
    if (count > KR_WORKFLOWS_MAX_WORDS) {
        too_many(error, count);
        return NULL;
    }
    g_autoptr(JsonBuilder) builder = json_builder_new();
    json_builder_begin_object(builder);
    json_builder_set_member_name(builder, "argv");
    json_builder_begin_array(builder);
    for (const char *const *word = argv; *word != NULL; word++)
        json_builder_add_string_value(builder, *word);
    json_builder_end_array(builder);
    json_builder_end_object(builder);
    g_autoptr(JsonNode) root = json_builder_get_root(builder);
    return json_to_string(root, FALSE);
}

/* ---- the hub's answer ------------------------------------------------------------------ */

static KrWorkflowRun *
response_error(GError **error, const char *why)
{
    g_set_error(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_RESPONSE,
                "The hub's answer is not a run on the workflows: %s", why);
    return NULL;
}

/* The member `key` as a string, NULL when it is absent, null, empty or not a string. */
static char *
dup_text(JsonObject *object, const char *key)
{
    JsonNode *node = json_object_get_member(object, key);
    if (node == NULL || !JSON_NODE_HOLDS_VALUE(node) ||
        json_node_get_value_type(node) != G_TYPE_STRING)
        return NULL;
    const char *text = json_node_get_string(node);
    return *text != '\0' ? g_strdup(text) : NULL;
}

KrWorkflowRun *
kr_workflow_run_parse(const char *json, gssize length, GError **error)
{
    if (json == NULL)
        return response_error(error, "no body");
    g_autoptr(JsonParser) parser = json_parser_new_immutable();
    if (!json_parser_load_from_data(parser, json, length, NULL))
        return response_error(error, "not JSON");
    JsonNode *root = json_parser_get_root(parser);
    if (root == NULL || !JSON_NODE_HOLDS_OBJECT(root))
        return response_error(error, "not an object");
    JsonObject *object = json_node_get_object(root);

    g_autoptr(KrWorkflowRun) run = g_new0(KrWorkflowRun, 1);
    run->request_id = dup_text(object, "request_id");
    if (run->request_id == NULL)
        return response_error(error, "no request_id");
    g_autofree char *state = dup_text(object, "state");
    gboolean known = FALSE;
    for (guint i = 0; state != NULL && i < G_N_ELEMENTS(STATE_NAMES) && !known; i++) {
        if (g_str_equal(state, STATE_NAMES[i])) {
            run->state = (KrWorkflowState) i;
            known = TRUE;
        }
    }
    if (!known)
        return response_error(error, "no state krypton knows");
    JsonNode *exit_code = json_object_get_member(object, "exit_code");
    if (exit_code != NULL && JSON_NODE_HOLDS_VALUE(exit_code) &&
        json_node_get_value_type(exit_code) == G_TYPE_INT64) {
        run->has_exit_code = TRUE;
        run->exit_code = json_node_get_int(exit_code);
    }
    run->url = dup_text(object, "url");
    run->output = dup_text(object, "stdout");
    run->errors = dup_text(object, "stderr");
    run->detail = dup_text(object, "detail");
    return g_steal_pointer(&run);
}

gboolean
kr_workflow_run_finished(const KrWorkflowRun *run)
{
    return run->state == KR_WORKFLOW_DONE || run->state == KR_WORKFLOW_FAILED;
}

const char *
kr_workflow_state_name(KrWorkflowState state)
{
    return (guint) state < G_N_ELEMENTS(STATE_NAMES) ? STATE_NAMES[state] : "unknown";
}

char *
kr_workflow_run_summary(const KrWorkflowRun *run)
{
    switch (run->state) {
    case KR_WORKFLOW_QUEUED:
        return g_strdup("Queued: waiting for a GitHub runner");
    case KR_WORKFLOW_RUNNING:
        return g_strdup("Running on a GitHub runner");
    case KR_WORKFLOW_DONE:
        return run->has_exit_code
                   ? g_strdup_printf("Done: exit code %" G_GINT64_FORMAT, run->exit_code)
                   : g_strdup("Done");
    case KR_WORKFLOW_FAILED:
    default:
        return g_strdup_printf("Failed: %s", run->detail != NULL
                                                 ? run->detail
                                                 : "the run ended without a report");
    }
}

/* ---- refusals -------------------------------------------------------------------------- */

char *
kr_workflows_refusal_message(guint status, const char *detail)
{
    g_autofree char *said = detail != NULL && *detail != '\0'
                                ? g_strdup_printf(" (the hub said: %s)", detail)
                                : g_strdup("");
    switch (status) {
    case 401:
        return g_strdup_printf("The hub does not know this device%s. Pair it again on the "
                               "Devices page.",
                               said);
    case 403:
        return g_strdup_printf(
            "The hub will not run that on GitHub for this device%s. It needs the "
            KR_WORKFLOWS_SCOPE " scope and the scopes of what the command itself does, and "
            "some commands (migrate, budget set) the hub never runs. Ask the host to pair "
            "this device again with them: vibey hub pair --scope view --scope "
            KR_WORKFLOWS_SCOPE,
            said);
    case 422:
        return g_strdup_printf("The hub could not take that command line%s.", said);
    case 429:
        return g_strdup_printf("Too many requests%s. Wait a moment, then run it again.", said);
    case 502:
        return g_strdup_printf("GitHub refused the run, or could not be read%s.", said);
    case 503:
        return g_strdup_printf("Running vibey on GitHub is not enabled on this hub%s. Its host "
                               "turns it on with the VIBEY_WORKFLOWS_* settings that vibey "
                               "serve reads.",
                               said);
    default:
        return g_strdup_printf("The hub refused it (%u): %s%s", status,
                               kr_hub_status_text(status), said);
    }
}

char *
kr_workflows_timeout_message(const KrWorkflowRun *last, guint limit_seconds)
{
    guint minutes = limit_seconds / 60;
    g_autofree char *after = limit_seconds % 60 == 0 && minutes > 0
                                 ? g_strdup_printf("%u minute%s", minutes, minutes == 1 ? "" : "s")
                                 : g_strdup_printf("%u second%s", limit_seconds,
                                                   limit_seconds == 1 ? "" : "s");
    if (last == NULL)
        return g_strdup_printf("krypton stopped following it after %s.", after);
    if (last->url != NULL)
        return g_strdup_printf("krypton stopped following it after %s; it is still %s at %s",
                               after, kr_workflow_state_name(last->state), last->url);
    return g_strdup_printf("krypton stopped following it after %s; it is still %s, and GitHub "
                           "has not shown its run yet. Its request id is %s.",
                           after, kr_workflow_state_name(last->state), last->request_id);
}

gboolean
kr_workflows_scope_held(const char *const *scopes)
{
    return scopes != NULL && g_strv_contains(scopes, KR_WORKFLOWS_SCOPE);
}
