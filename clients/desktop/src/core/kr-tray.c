/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-tray.h"

static KrTrayEntry *
entry_new(const char *label, const char *action)
{
    KrTrayEntry *entry = g_new0(KrTrayEntry, 1);
    entry->label = g_strdup(label);
    entry->action = g_strdup(action);
    return entry;
}

static void
entry_free(gpointer data)
{
    KrTrayEntry *entry = data;
    g_free(entry->label);
    g_free(entry->action);
    g_free(entry);
}

KrTrayModel *
kr_tray_model_new(KrState *state, const char *name)
{
    KrTrayModel *model = g_new0(KrTrayModel, 1);
    model->entries = g_ptr_array_new_with_free_func(entry_free);

    g_autoptr(GPtrArray) gates = g_ptr_array_ref(kr_state_gates(state));
    guint waiting = gates->len;
    guint running = kr_state_running_lanes(state);
    KrConnection connection = kr_state_connection(state);
    gboolean trouble = connection == KR_CONNECTION_OFFLINE || connection == KR_CONNECTION_REFUSED;

    /* A hub that does not answer says so first: the counts below would be stale. */
    if (trouble)
        model->tooltip = g_strdup_printf("%s: no hub answers", name);
    else if (waiting > 0)
        model->tooltip = g_strdup_printf("%s: %u gate%s need%s you", name, waiting,
                                         waiting == 1 ? "" : "s", waiting == 1 ? "s" : "");
    else if (running > 0)
        model->tooltip = g_strdup_printf("%s: %u lane%s running", name, running,
                                         running == 1 ? "" : "s");
    else
        model->tooltip = g_strdup_printf("%s: all quiet", name);
    model->attention = !trouble && waiting > 0;

    g_autofree char *open = g_strdup_printf("Open %s", name);
    g_ptr_array_add(model->entries, entry_new(open, "open"));
    if (model->attention) {
        g_autofree char *answer = g_strdup_printf("Answer %u waiting gate%s", waiting,
                                                  waiting == 1 ? "" : "s");
        g_ptr_array_add(model->entries, entry_new(answer, "show-gates"));
    }
    g_ptr_array_add(model->entries, entry_new("Start a project…", "start-project"));
    g_ptr_array_add(model->entries, entry_new("Quit", "quit"));
    return model;
}

void
kr_tray_model_free(KrTrayModel *model)
{
    if (model == NULL)
        return;
    g_free(model->tooltip);
    g_ptr_array_unref(model->entries);
    g_free(model);
}

KrTrayModel *
kr_tray_model_copy(const KrTrayModel *model)
{
    KrTrayModel *copy = g_new0(KrTrayModel, 1);
    copy->attention = model->attention;
    copy->tooltip = g_strdup(model->tooltip);
    copy->entries = g_ptr_array_new_with_free_func(entry_free);
    for (guint i = 0; i < model->entries->len; i++) {
        const KrTrayEntry *entry = g_ptr_array_index(model->entries, i);
        g_ptr_array_add(copy->entries, entry_new(entry->label, entry->action));
    }
    return copy;
}

gboolean
kr_tray_model_equal(const KrTrayModel *a, const KrTrayModel *b)
{
    if (a->attention != b->attention || g_strcmp0(a->tooltip, b->tooltip) != 0 ||
        a->entries->len != b->entries->len)
        return FALSE;
    for (guint i = 0; i < a->entries->len; i++) {
        const KrTrayEntry *left = g_ptr_array_index(a->entries, i);
        const KrTrayEntry *right = g_ptr_array_index(b->entries, i);
        if (g_strcmp0(left->label, right->label) != 0 ||
            g_strcmp0(left->action, right->action) != 0)
            return FALSE;
    }
    return TRUE;
}
