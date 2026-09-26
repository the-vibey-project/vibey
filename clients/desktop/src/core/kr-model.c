/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-model.h"

#include <json-glib/json-glib.h>
#include <string.h>

G_DEFINE_QUARK(kr-model-error-quark, kr_model_error)

/* ---- reading one JSON document ------------------------------------------------------- */

static JsonNode *
parse_root(const char *json, gssize length, GError **error)
{
    if (json == NULL) {
        g_set_error_literal(error, KR_MODEL_ERROR, KR_MODEL_ERROR_PARSE, "no body");
        return NULL;
    }
    g_autoptr(JsonParser) parser = json_parser_new_immutable();
    g_autoptr(GError) local = NULL;
    if (!json_parser_load_from_data(parser, json, length, &local)) {
        g_set_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_PARSE, "not JSON: %s",
                    local->message);
        return NULL;
    }
    JsonNode *root = json_parser_get_root(parser);
    if (root == NULL) {
        g_set_error_literal(error, KR_MODEL_ERROR, KR_MODEL_ERROR_PARSE, "an empty body");
        return NULL;
    }
    return json_node_copy(root);
}

static gboolean
shape_error(GError **error, const char *what)
{
    g_set_error(error, KR_MODEL_ERROR, KR_MODEL_ERROR_SHAPE, "not the expected document: %s",
                what);
    return FALSE;
}

/* The member `key` of `object` as a string, or NULL when absent, null or not a string. */
static char *
dup_string(JsonObject *object, const char *key)
{
    JsonNode *node = json_object_get_member(object, key);
    if (node == NULL || !JSON_NODE_HOLDS_VALUE(node) ||
        json_node_get_value_type(node) != G_TYPE_STRING)
        return NULL;
    return g_strdup(json_node_get_string(node));
}

/* The member as text: a string as itself, anything else but null as its JSON. */
static char *
dup_text(JsonObject *object, const char *key)
{
    JsonNode *node = json_object_get_member(object, key);
    if (node == NULL || JSON_NODE_HOLDS_NULL(node))
        return NULL;
    if (JSON_NODE_HOLDS_VALUE(node) && json_node_get_value_type(node) == G_TYPE_STRING)
        return g_strdup(json_node_get_string(node));
    return json_to_string(node, FALSE);
}

static gboolean
is_number(JsonNode *node)
{
    if (node == NULL || !JSON_NODE_HOLDS_VALUE(node))
        return FALSE;
    GType type = json_node_get_value_type(node);
    return type == G_TYPE_INT64 || type == G_TYPE_DOUBLE;
}

static gint64
get_int(JsonObject *object, const char *key, gint64 otherwise)
{
    JsonNode *node = json_object_get_member(object, key);
    if (!is_number(node))
        return otherwise;
    if (json_node_get_value_type(node) == G_TYPE_DOUBLE)
        return (gint64) json_node_get_double(node);
    return json_node_get_int(node);
}

static double
get_double(JsonObject *object, const char *key, double otherwise)
{
    JsonNode *node = json_object_get_member(object, key);
    if (!is_number(node))
        return otherwise;
    return json_node_get_double(node);
}

static gboolean
get_bool(JsonObject *object, const char *key)
{
    JsonNode *node = json_object_get_member(object, key);
    if (node == NULL || !JSON_NODE_HOLDS_VALUE(node) ||
        json_node_get_value_type(node) != G_TYPE_BOOLEAN)
        return FALSE;
    return json_node_get_boolean(node);
}

/* An ISO 8601 time (Python's isoformat) as Unix seconds; 0 when absent or unreadable. */
static gint64
get_time(JsonObject *object, const char *key)
{
    g_autofree char *text = dup_string(object, key);
    if (text == NULL)
        return 0;
    g_autoptr(GTimeZone) utc = g_time_zone_new_utc();
    g_autoptr(GDateTime) when = g_date_time_new_from_iso8601(text, utc);
    return when == NULL ? 0 : g_date_time_to_unix(when);
}

/* The member as a NULL-terminated string array: strings as themselves, others as JSON. */
static char **
get_strv(JsonObject *object, const char *key, const char *inner_key)
{
    GStrvBuilder *builder = g_strv_builder_new();
    JsonNode *node = json_object_get_member(object, key);
    if (node != NULL && JSON_NODE_HOLDS_ARRAY(node)) {
        JsonArray *array = json_node_get_array(node);
        for (guint i = 0; i < json_array_get_length(array); i++) {
            JsonNode *element = json_array_get_element(array, i);
            if (inner_key != NULL) {
                if (!JSON_NODE_HOLDS_OBJECT(element))
                    continue;
                g_autofree char *text = dup_string(json_node_get_object(element), inner_key);
                if (text != NULL)
                    g_strv_builder_add(builder, text);
            } else if (JSON_NODE_HOLDS_VALUE(element) &&
                       json_node_get_value_type(element) == G_TYPE_STRING) {
                g_strv_builder_add(builder, json_node_get_string(element));
            } else {
                g_autofree char *text = json_to_string(element, FALSE);
                g_strv_builder_add(builder, text);
            }
        }
    }
    char **out = g_strv_builder_end(builder);
    g_strv_builder_unref(builder);
    return out;
}

/* The array a list route returns: the root itself, or the root's `key` member. */
static JsonArray *
list_of(JsonNode *root, const char *key, GError **error)
{
    if (key == NULL) {
        if (!JSON_NODE_HOLDS_ARRAY(root)) {
            shape_error(error, "expected an array");
            return NULL;
        }
        return json_node_get_array(root);
    }
    if (!JSON_NODE_HOLDS_OBJECT(root)) {
        shape_error(error, "expected an object");
        return NULL;
    }
    JsonNode *member = json_object_get_member(json_node_get_object(root), key);
    if (member == NULL || !JSON_NODE_HOLDS_ARRAY(member)) {
        g_autofree char *what = g_strdup_printf("no \"%s\" array", key);
        shape_error(error, what);
        return NULL;
    }
    return json_node_get_array(member);
}

typedef gpointer (*ReadOne)(JsonObject *object);

/* Reads every element of a list route with `read`; any element that is not an object, or
 * that `read` refuses (NULL), fails the whole document. */
static GPtrArray *
parse_list(const char *json, gssize length, const char *key, ReadOne read,
           GDestroyNotify free_one, const char *what, GError **error)
{
    g_autoptr(JsonNode) root = parse_root(json, length, error);
    if (root == NULL)
        return NULL;
    JsonArray *array = list_of(root, key, error);
    if (array == NULL)
        return NULL;

    g_autoptr(GPtrArray) out = g_ptr_array_new_with_free_func(free_one);
    for (guint i = 0; i < json_array_get_length(array); i++) {
        JsonNode *element = json_array_get_element(array, i);
        gpointer one = JSON_NODE_HOLDS_OBJECT(element) ? read(json_node_get_object(element))
                                                       : NULL;
        if (one == NULL) {
            g_autofree char *why = g_strdup_printf("%s %u is malformed", what, i);
            shape_error(error, why);
            return NULL;
        }
        g_ptr_array_add(out, one);
    }
    return g_steal_pointer(&out);
}

/* ---- projects ------------------------------------------------------------------------ */

void
kr_project_free(KrProject *project)
{
    if (project == NULL)
        return;
    g_free(project->project_id);
    g_free(project->name);
    g_free(project->phase);
    g_free(project->repo_path);
    g_free(project);
}

static gpointer
read_project(JsonObject *object)
{
    KrProject *project = g_new0(KrProject, 1);
    project->project_id = dup_string(object, "project_id");
    project->name = dup_string(object, "name");
    if (project->project_id == NULL || project->name == NULL) {
        kr_project_free(project);
        return NULL;
    }
    project->phase = dup_string(object, "phase");
    project->repo_path = dup_string(object, "repo_path");
    project->cycle = get_int(object, "cycle", 0);
    project->max_cycles = get_int(object, "max_cycles", 0);
    project->open_gates = get_int(object, "open_gates", 0);
    project->created_at = get_time(object, "created_at");
    return project;
}

GPtrArray *
kr_projects_parse(const char *json, gssize length, GError **error)
{
    return parse_list(json, length, NULL, read_project, (GDestroyNotify) kr_project_free,
                      "project", error);
}

/* ---- gates --------------------------------------------------------------------------- */

void
kr_gate_free(KrGate *gate)
{
    if (gate == NULL)
        return;
    g_free(gate->gate_id);
    g_free(gate->project_id);
    g_free(gate->project_name);
    g_free(gate->job_id);
    g_free(gate->kind);
    g_free(gate->prompt);
    g_strfreev(gate->options);
    g_free(gate->default_answer);
    g_free(gate->answer_with);
    g_free(gate);
}

static gpointer
read_gate(JsonObject *object)
{
    KrGate *gate = g_new0(KrGate, 1);
    gate->gate_id = dup_string(object, "gate_id");
    gate->kind = dup_string(object, "kind");
    gate->options = get_strv(object, "options", NULL);
    if (gate->gate_id == NULL || gate->kind == NULL) {
        kr_gate_free(gate);
        return NULL;
    }
    gate->project_id = dup_string(object, "project_id");
    gate->project_name = dup_string(object, "project_name");
    gate->job_id = dup_string(object, "job_id");
    gate->prompt = dup_string(object, "prompt");
    gate->default_answer = dup_text(object, "default_answer");
    gate->answer_with = dup_string(object, "answer_with");
    gate->raised_at = get_time(object, "raised_at");
    gate->timeout_at = get_time(object, "timeout_at");
    return gate;
}

GPtrArray *
kr_gates_parse(const char *json, gssize length, GError **error)
{
    return parse_list(json, length, "gates", read_gate, (GDestroyNotify) kr_gate_free, "gate",
                      error);
}

gboolean
kr_gate_spends(const KrGate *gate)
{
    if (gate == NULL || gate->kind == NULL)
        return FALSE;
    return g_str_equal(gate->kind, "budget_exhausted") || g_str_has_prefix(gate->kind, "deploy_");
}

/* ---- lanes --------------------------------------------------------------------------- */

void
kr_lane_free(KrLane *lane)
{
    if (lane == NULL)
        return;
    g_free(lane->id);
    g_free(lane->engine);
    g_free(lane->cwd);
    g_free(lane->label);
    g_free(lane->state);
    g_free(lane->outcome);
    g_free(lane);
}

static gpointer
read_lane(JsonObject *object)
{
    KrLane *lane = g_new0(KrLane, 1);
    lane->id = dup_string(object, "id");
    if (lane->id == NULL) {
        kr_lane_free(lane);
        return NULL;
    }
    lane->engine = dup_string(object, "engine");
    lane->cwd = dup_string(object, "cwd");
    lane->label = dup_string(object, "label");
    lane->state = dup_string(object, "state");
    lane->outcome = dup_text(object, "outcome");
    lane->offset = get_int(object, "offset", 0);
    lane->last_event_at = get_double(object, "last_event_at", 0.0);
    return lane;
}

GPtrArray *
kr_lanes_parse(const char *json, gssize length, GError **error)
{
    return parse_list(json, length, "lanes", read_lane, (GDestroyNotify) kr_lane_free, "lane",
                      error);
}

/* ---- budget -------------------------------------------------------------------------- */

void
kr_budget_free(KrBudget *budget)
{
    if (budget == NULL)
        return;
    g_free(budget->project_id);
    g_free(budget->name);
    g_free(budget);
}

static JsonObject *
object_member(JsonObject *object, const char *key)
{
    JsonNode *node = json_object_get_member(object, key);
    return node != NULL && JSON_NODE_HOLDS_OBJECT(node) ? json_node_get_object(node) : NULL;
}

KrBudget *
kr_budget_parse(const char *json, gssize length, GError **error)
{
    g_autoptr(JsonNode) root = parse_root(json, length, error);
    if (root == NULL)
        return NULL;
    if (!JSON_NODE_HOLDS_OBJECT(root)) {
        shape_error(error, "a budget is an object");
        return NULL;
    }
    JsonObject *object = json_node_get_object(root);
    g_autoptr(KrBudget) budget = g_new0(KrBudget, 1);
    budget->project_id = dup_string(object, "project_id");
    if (budget->project_id == NULL) {
        shape_error(error, "a budget names its project");
        return NULL;
    }
    budget->name = dup_string(object, "name");
    budget->cycle = get_int(object, "cycle", 0);
    budget->exhausted = get_bool(object, "exhausted");

    JsonObject *caps = object_member(object, "caps");
    if (caps != NULL) {
        budget->has_max_dollars = is_number(json_object_get_member(caps, "max_cycle_dollars"));
        budget->max_dollars = get_double(caps, "max_cycle_dollars", 0.0);
        budget->has_max_turns = is_number(json_object_get_member(caps, "max_cycle_turns"));
        budget->max_turns = get_int(caps, "max_cycle_turns", 0);
    }
    JsonObject *spend = object_member(object, "spend");
    if (spend != NULL) {
        budget->spent_dollars = get_double(spend, "dollars", 0.0);
        budget->spent_turns = get_int(spend, "turns", 0);
    }
    return g_steal_pointer(&budget);
}

/* ---- loops --------------------------------------------------------------------------- */

void
kr_loop_free(KrLoop *loop)
{
    if (loop == NULL)
        return;
    g_free(loop->loop);
    g_free(loop->tier);
    g_strfreev(loop->engine_ids);
    g_free(loop);
}

void
kr_loops_free(KrLoops *loops)
{
    if (loops == NULL)
        return;
    g_free(loops->default_loop);
    g_strfreev(loops->efforts);
    if (loops->loops != NULL)
        g_ptr_array_unref(loops->loops);
    g_free(loops);
}

static gpointer
read_loop(JsonObject *object)
{
    KrLoop *loop = g_new0(KrLoop, 1);
    loop->loop = dup_string(object, "loop");
    loop->engine_ids = get_strv(object, "engines", "engine_id");
    if (loop->loop == NULL) {
        kr_loop_free(loop);
        return NULL;
    }
    loop->tier = dup_string(object, "tier");
    loop->is_default = get_bool(object, "default");
    loop->declared_only = get_bool(object, "declared_only");
    return loop;
}

KrLoops *
kr_loops_parse(const char *json, gssize length, GError **error)
{
    g_autoptr(JsonNode) root = parse_root(json, length, error);
    if (root == NULL)
        return NULL;
    JsonArray *array = list_of(root, "loops", error);
    if (array == NULL)
        return NULL;
    JsonObject *object = json_node_get_object(root);

    g_autoptr(KrLoops) loops = g_new0(KrLoops, 1);
    loops->default_loop = dup_string(object, "default_loop");
    loops->efforts = get_strv(object, "efforts", NULL);
    loops->loops = g_ptr_array_new_with_free_func((GDestroyNotify) kr_loop_free);
    for (guint i = 0; i < json_array_get_length(array); i++) {
        JsonNode *element = json_array_get_element(array, i);
        gpointer loop = JSON_NODE_HOLDS_OBJECT(element) ? read_loop(json_node_get_object(element))
                                                        : NULL;
        if (loop == NULL) {
            shape_error(error, "a loop is malformed");
            return NULL;
        }
        g_ptr_array_add(loops->loops, loop);
    }
    return g_steal_pointer(&loops);
}

/* ---- doctor -------------------------------------------------------------------------- */

void
kr_doctor_check_free(KrDoctorCheck *check)
{
    if (check == NULL)
        return;
    g_free(check->name);
    g_free(check->mark);
    g_free(check->detail);
    g_free(check);
}

void
kr_doctor_free(KrDoctor *doctor)
{
    if (doctor == NULL)
        return;
    g_free(doctor->scope);
    if (doctor->checks != NULL)
        g_ptr_array_unref(doctor->checks);
    g_free(doctor);
}

static gpointer
read_check(JsonObject *object)
{
    KrDoctorCheck *check = g_new0(KrDoctorCheck, 1);
    check->name = dup_string(object, "name");
    check->mark = dup_string(object, "mark");
    if (check->name == NULL || check->mark == NULL) {
        kr_doctor_check_free(check);
        return NULL;
    }
    check->detail = dup_string(object, "detail");
    return check;
}

KrDoctor *
kr_doctor_parse(const char *json, gssize length, GError **error)
{
    g_autoptr(JsonNode) root = parse_root(json, length, error);
    if (root == NULL)
        return NULL;
    JsonArray *array = list_of(root, "checks", error);
    if (array == NULL)
        return NULL;

    g_autoptr(KrDoctor) doctor = g_new0(KrDoctor, 1);
    doctor->scope = dup_text(json_node_get_object(root), "scope");
    doctor->checks = g_ptr_array_new_with_free_func((GDestroyNotify) kr_doctor_check_free);
    for (guint i = 0; i < json_array_get_length(array); i++) {
        JsonNode *element = json_array_get_element(array, i);
        gpointer check = JSON_NODE_HOLDS_OBJECT(element)
                             ? read_check(json_node_get_object(element))
                             : NULL;
        if (check == NULL) {
            shape_error(error, "a check is malformed");
            return NULL;
        }
        g_ptr_array_add(doctor->checks, check);
    }
    return g_steal_pointer(&doctor);
}

const char *
kr_doctor_worst(const KrDoctor *doctor)
{
    gboolean warned = FALSE;
    for (guint i = 0; doctor != NULL && i < doctor->checks->len; i++) {
        const KrDoctorCheck *check = g_ptr_array_index(doctor->checks, i);
        if (g_ascii_strcasecmp(check->mark, "FAIL") == 0)
            return "FAIL";
        if (g_ascii_strcasecmp(check->mark, "WARN") == 0)
            warned = TRUE;
    }
    return warned ? "WARN" : "PASS";
}
