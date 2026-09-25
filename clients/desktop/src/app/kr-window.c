/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-window.h"

#include "kr-answer.h"
#include "kr-format.h"
#include "kr-mark.h"
#include "kr-pairing.h"

const char *const kr_window_page_names[KR_WINDOW_PAGES] = {
    "projects", "gates", "lanes", "loops", "budgets", "doctor", "devices", "settings",
};

typedef struct {
    const char *title;
    const char *icon;
} Place;

static const Place PLACES[KR_WINDOW_PAGES] = {
    {"Projects", "folder-symbolic"},
    {"Gates", "dialog-question-symbolic"},
    {"Lanes", "media-playback-start-symbolic"},
    {"Loops and effort", "view-refresh-symbolic"},
    {"Budgets", "wallet-symbolic"},
    {"Doctor", "emblem-ok-symbolic"},
    {"Devices", "network-wireless-symbolic"},
    {"Settings", "emblem-system-symbolic"},
};

typedef struct {
    KrApp *app;
    AdwToastOverlay *overlay;
    AdwNavigationSplitView *split;
    AdwNavigationPage *content_page;
    GtkListBox *sidebar;
    GtkStack *stack;
    GtkWidget *mark;
    AdwBanner *banner;
    GtkListBox *lists[KR_WINDOW_PAGES];
    AdwStatusPage *empty[KR_WINDOW_PAGES];
    GtkStack *page_stacks[KR_WINDOW_PAGES];
    GtkWidget *gates_badge;
    guint listener;
} KrWindow;

enum { PAGE_PROJECTS, PAGE_GATES, PAGE_LANES, PAGE_LOOPS, PAGE_BUDGETS, PAGE_DOCTOR,
       PAGE_DEVICES, PAGE_SETTINGS };

static KrWindow *
window_of(GtkWidget *window)
{
    return g_object_get_data(G_OBJECT(window), "kr-window");
}

void
kr_window_toast(GtkWidget *window, const char *text)
{
    KrWindow *self = window_of(window);
    AdwToast *toast = adw_toast_new(text);
    adw_toast_set_use_markup(toast, FALSE);
    adw_toast_overlay_add_toast(self->overlay, toast);
}

/* ---- building blocks ----------------------------------------------------------------- */

static GtkWidget *
row(const char *title, const char *subtitle)
{
    GtkWidget *widget = adw_action_row_new();
    adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(widget), FALSE);
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(widget), title != NULL ? title : "");
    if (subtitle != NULL)
        adw_action_row_set_subtitle(ADW_ACTION_ROW(widget), subtitle);
    return widget;
}

static GtkWidget *
pill(const char *text, const char *css_class)
{
    GtkWidget *label = gtk_label_new(text);
    gtk_widget_add_css_class(label, "caption-heading");
    gtk_widget_add_css_class(label, css_class);
    gtk_widget_set_valign(label, GTK_ALIGN_CENTER);
    return label;
}

/* Shows either the list or the empty state of a page. */
static void
show_list(KrWindow *self, int page, gboolean has_rows)
{
    gtk_stack_set_visible_child_name(self->page_stacks[page], has_rows ? "list" : "empty");
}

/* A page: a scrolling, width-clamped boxed list, and a designed empty state beside it. */
static GtkWidget *
list_page(KrWindow *self, int page, const char *empty_title, const char *empty_description)
{
    GtkWidget *list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(list), GTK_SELECTION_NONE);
    gtk_widget_add_css_class(list, "boxed-list");
    gtk_widget_set_valign(list, GTK_ALIGN_START);
    self->lists[page] = GTK_LIST_BOX(list);

    GtkWidget *clamp = adw_clamp_new();
    adw_clamp_set_maximum_size(ADW_CLAMP(clamp), 820);
    adw_clamp_set_child(ADW_CLAMP(clamp), list);
    gtk_widget_set_margin_top(clamp, 18);
    gtk_widget_set_margin_bottom(clamp, 18);
    gtk_widget_set_margin_start(clamp, 12);
    gtk_widget_set_margin_end(clamp, 12);

    GtkWidget *scroller = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroller), clamp);
    gtk_widget_set_vexpand(scroller, TRUE);

    GtkWidget *empty = adw_status_page_new();
    adw_status_page_set_icon_name(ADW_STATUS_PAGE(empty), PLACES[page].icon);
    adw_status_page_set_title(ADW_STATUS_PAGE(empty), empty_title);
    adw_status_page_set_description(ADW_STATUS_PAGE(empty), empty_description);
    self->empty[page] = ADW_STATUS_PAGE(empty);

    GtkWidget *stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(stack), GTK_STACK_TRANSITION_TYPE_CROSSFADE);
    gtk_stack_add_named(GTK_STACK(stack), scroller, "list");
    gtk_stack_add_named(GTK_STACK(stack), empty, "empty");
    gtk_stack_set_visible_child_name(GTK_STACK(stack), "empty");
    self->page_stacks[page] = GTK_STACK(stack);
    return stack;
}

/* ---- projects ------------------------------------------------------------------------ */

static void
on_project_activated(AdwActionRow *widget, gpointer data)
{
    KrWindow *self = data;
    const char *project_id = g_object_get_data(G_OBJECT(widget), "project-id");
    kr_state_select_project(self->app->state, project_id);
    kr_app_refresh_budget(self->app, project_id);
    kr_window_show_page(self->app->window, "budgets");
}

static void
render_projects(KrWindow *self)
{
    GPtrArray *projects = kr_state_projects(self->app->state);
    gtk_list_box_remove_all(self->lists[PAGE_PROJECTS]);
    gint64 now = g_get_real_time() / G_USEC_PER_SEC;
    for (guint i = 0; i < projects->len; i++) {
        const KrProject *project = g_ptr_array_index(projects, i);
        g_autofree char *since = kr_format_relative(project->created_at, now);
        g_autofree char *subtitle = g_strdup_printf(
            "%s · cycle %" G_GINT64_FORMAT " of %" G_GINT64_FORMAT " · started %s",
            kr_format_phase(project->phase), project->cycle, project->max_cycles, since);
        GtkWidget *widget = row(project->name, subtitle);
        if (project->open_gates > 0) {
            g_autofree char *gates =
                g_strdup_printf("%" G_GINT64_FORMAT " waiting", project->open_gates);
            adw_action_row_add_suffix(ADW_ACTION_ROW(widget), pill(gates, "warning"));
        }
        adw_action_row_add_suffix(ADW_ACTION_ROW(widget),
                                  gtk_image_new_from_icon_name("go-next-symbolic"));
        gtk_list_box_row_set_activatable(GTK_LIST_BOX_ROW(widget), TRUE);
        g_object_set_data_full(G_OBJECT(widget), "project-id", g_strdup(project->project_id),
                               g_free);
        g_signal_connect(widget, "activated", G_CALLBACK(on_project_activated), self);
        gtk_list_box_append(self->lists[PAGE_PROJECTS], widget);
    }
    show_list(self, PAGE_PROJECTS, projects->len > 0);
}

/* ---- gates --------------------------------------------------------------------------- */

typedef struct {
    KrWindow *self;
    char *gate_id;
    char *value;
} Answer;

static void
answer_free(gpointer data, GClosure *closure)
{
    (void) closure;
    Answer *answer = data;
    g_free(answer->gate_id);
    g_free(answer->value);
    g_free(answer);
}

static const KrGate *
find_gate(KrWindow *self, const char *gate_id)
{
    GPtrArray *gates = kr_state_gates(self->app->state);
    for (guint i = 0; i < gates->len; i++) {
        const KrGate *gate = g_ptr_array_index(gates, i);
        if (g_str_equal(gate->gate_id, gate_id))
            return gate;
    }
    return NULL;
}

static void
on_option_clicked(GtkButton *button, gpointer data)
{
    (void) button;
    Answer *answer = data;
    const KrGate *gate = find_gate(answer->self, answer->gate_id);
    if (gate != NULL)
        kr_app_answer(answer->self->app, gate, answer->value);
}

static void
on_entry_apply(AdwEntryRow *entry, gpointer data)
{
    Answer *answer = data;
    const KrGate *gate = find_gate(answer->self, answer->gate_id);
    if (gate != NULL)
        kr_app_answer(answer->self->app, gate, gtk_editable_get_text(GTK_EDITABLE(entry)));
}

static Answer *
answer_new(KrWindow *self, const KrGate *gate, const char *value)
{
    Answer *answer = g_new0(Answer, 1);
    answer->self = self;
    answer->gate_id = g_strdup(gate->gate_id);
    answer->value = g_strdup(value);
    return answer;
}

static GtkWidget *
option_button(KrWindow *self, const KrGate *gate, const char *label, const char *value,
              gboolean suggested)
{
    GtkWidget *button = gtk_button_new_with_label(label);
    gtk_widget_add_css_class(button, "pill");
    if (suggested)
        gtk_widget_add_css_class(button, "suggested-action");
    g_signal_connect_data(button, "clicked", G_CALLBACK(on_option_clicked),
                          answer_new(self, gate, value), answer_free, 0);
    return button;
}

static GtkWidget *
entry_row(KrWindow *self, const KrGate *gate, const char *title)
{
    GtkWidget *entry = adw_entry_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(entry), title);
    adw_entry_row_set_show_apply_button(ADW_ENTRY_ROW(entry), TRUE);
    g_signal_connect_data(entry, "apply", G_CALLBACK(on_entry_apply), answer_new(self, gate, NULL),
                          answer_free, 0);
    return entry;
}

/* The controls that answer one gate, by the shape its kind reads (kr-answer.h). */
static void
add_answer_controls(KrWindow *self, AdwExpanderRow *expander, const KrGate *gate)
{
    const char *grant_key = NULL;
    KrAnswerShape shape = kr_answer_shape(gate->kind, &grant_key);
    if (kr_gate_spends(gate)) {
        GtkWidget *warn = row("Answering this can spend money",
                              "It needs the spend scope as well as answer.");
        adw_action_row_add_prefix(ADW_ACTION_ROW(warn),
                                  gtk_image_new_from_icon_name("dialog-warning-symbolic"));
        adw_expander_row_add_row(expander, warn);
    }
    switch (shape) {
    case KR_ANSWER_VERDICT:
    case KR_ANSWER_CHOICE: {
        GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
        gtk_widget_set_margin_top(box, 10);
        gtk_widget_set_margin_bottom(box, 10);
        gtk_widget_set_margin_start(box, 12);
        gtk_widget_set_margin_end(box, 12);
        for (char **option = gate->options; option != NULL && *option != NULL; option++)
            gtk_box_append(GTK_BOX(box),
                           option_button(self, gate, *option, *option,
                                         g_strcmp0(*option, gate->default_answer) == 0));
        adw_expander_row_add_row(expander, box);
        break;
    }
    case KR_ANSWER_GRANT: {
        g_autofree char *title = g_strdup_printf("New %s", grant_key);
        adw_expander_row_add_row(expander, entry_row(self, gate, title));
        break;
    }
    case KR_ANSWER_ANY: {
        GtkWidget *retry = row("It is fixed: try again", NULL);
        adw_action_row_add_suffix(ADW_ACTION_ROW(retry),
                                  option_button(self, gate, "Retry", NULL, TRUE));
        adw_expander_row_add_row(expander, retry);
        break;
    }
    case KR_ANSWER_FREE_FORM:
        adw_expander_row_add_row(expander, entry_row(self, gate, "Answer (a JSON object)"));
        break;
    case KR_ANSWER_DEFAULTS:
    default:
        adw_expander_row_add_row(expander, row("Answer it in the design interview",
                                               gate->answer_with));
        break;
    }
}

static void
render_gates(KrWindow *self)
{
    GPtrArray *gates = kr_state_gates(self->app->state);
    gtk_list_box_remove_all(self->lists[PAGE_GATES]);
    gint64 now = g_get_real_time() / G_USEC_PER_SEC;
    for (guint i = 0; i < gates->len; i++) {
        const KrGate *gate = g_ptr_array_index(gates, i);
        g_autofree char *raised = kr_format_relative(gate->raised_at, now);
        g_autofree char *subtitle =
            g_strdup_printf("%s · %s · raised %s",
                            gate->project_name != NULL ? gate->project_name : "vibey",
                            gate->kind, raised);
        GtkWidget *expander = adw_expander_row_new();
        adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(expander), FALSE);
        adw_preferences_row_set_title(ADW_PREFERENCES_ROW(expander),
                                      gate->prompt != NULL ? gate->prompt : gate->kind);
        adw_expander_row_set_subtitle(ADW_EXPANDER_ROW(expander), subtitle);
        add_answer_controls(self, ADW_EXPANDER_ROW(expander), gate);
        gtk_list_box_append(self->lists[PAGE_GATES], expander);
    }
    show_list(self, PAGE_GATES, gates->len > 0);

    g_autofree char *count = g_strdup_printf("%u", gates->len);
    gtk_label_set_text(GTK_LABEL(self->gates_badge), count);
    gtk_widget_set_visible(self->gates_badge, gates->len > 0);
}

/* ---- lanes --------------------------------------------------------------------------- */

static void
render_lanes(KrWindow *self)
{
    GPtrArray *lanes = kr_state_lanes(self->app->state);
    gtk_list_box_remove_all(self->lists[PAGE_LANES]);
    gint64 now = g_get_real_time() / G_USEC_PER_SEC;
    for (guint i = 0; i < lanes->len; i++) {
        const KrLane *lane = g_ptr_array_index(lanes, i);
        g_autofree char *last = kr_format_relative((gint64) lane->last_event_at, now);
        g_autofree char *subtitle = g_strdup_printf("%s · last event %s",
                                                    lane->cwd != NULL ? lane->cwd : "", last);
        GtkWidget *widget = row(lane->label != NULL ? lane->label : lane->id, subtitle);
        const char *state = lane->state != NULL ? lane->state : "unknown";
        const char *css = g_str_equal(state, "running")  ? "accent"
                          : g_str_equal(state, "quiet") ? "warning"
                                                        : "dim-label";
        adw_action_row_add_suffix(ADW_ACTION_ROW(widget),
                                  pill(lane->outcome != NULL ? lane->outcome : state, css));
        gtk_list_box_append(self->lists[PAGE_LANES], widget);
    }
    show_list(self, PAGE_LANES, lanes->len > 0);
    kr_mark_set_busy(self->mark, kr_state_running_lanes(self->app->state) > 0);
}

/* ---- loops --------------------------------------------------------------------------- */

static void
render_loops(KrWindow *self)
{
    const KrLoops *loops = kr_state_loops(self->app->state);
    gtk_list_box_remove_all(self->lists[PAGE_LOOPS]);
    if (loops == NULL) {
        show_list(self, PAGE_LOOPS, FALSE);
        return;
    }
    g_autofree char *efforts = g_strjoinv(" · ", loops->efforts);
    gtk_list_box_append(self->lists[PAGE_LOOPS], row("Effort ladder", efforts));
    for (guint i = 0; i < loops->loops->len; i++) {
        const KrLoop *loop = g_ptr_array_index(loops->loops, i);
        g_autofree char *engines = g_strjoinv(", ", loop->engine_ids);
        g_autofree char *subtitle =
            g_strdup_printf("%s tier · %s", loop->tier != NULL ? loop->tier : "?",
                            *engines != '\0' ? engines : "no engines");
        GtkWidget *widget = row(loop->loop, subtitle);
        if (loop->is_default)
            adw_action_row_add_suffix(ADW_ACTION_ROW(widget), pill("default", "accent"));
        if (loop->declared_only)
            adw_action_row_add_suffix(ADW_ACTION_ROW(widget), pill("declared only", "dim-label"));
        gtk_list_box_append(self->lists[PAGE_LOOPS], widget);
    }
    show_list(self, PAGE_LOOPS, TRUE);
}

/* ---- budgets ------------------------------------------------------------------------- */

static GtkWidget *
meter(const char *title, const char *subtitle, double fraction)
{
    GtkWidget *widget = row(title, subtitle);
    GtkWidget *bar = gtk_level_bar_new_for_interval(0.0, 1.0);
    gtk_level_bar_set_value(GTK_LEVEL_BAR(bar), fraction);
    gtk_widget_set_size_request(bar, 160, -1);
    gtk_widget_set_valign(bar, GTK_ALIGN_CENTER);
    adw_action_row_add_suffix(ADW_ACTION_ROW(widget), bar);
    return widget;
}

static void
render_budgets(KrWindow *self)
{
    const KrProject *project = kr_state_selected(self->app->state);
    const KrBudget *budget =
        kr_state_budget(self->app->state, kr_state_selected_project(self->app->state));
    gtk_list_box_remove_all(self->lists[PAGE_BUDGETS]);
    if (budget == NULL) {
        show_list(self, PAGE_BUDGETS, FALSE);
        return;
    }
    const char *name = budget->name != NULL ? budget->name
                       : project != NULL    ? project->name
                                            : budget->project_id;
    g_autofree char *cycle = g_strdup_printf("Cycle %" G_GINT64_FORMAT, budget->cycle);
    gtk_list_box_append(self->lists[PAGE_BUDGETS], row(name, cycle));

    g_autofree char *spent = kr_format_dollars(budget->spent_dollars);
    g_autofree char *cap = budget->has_max_dollars ? kr_format_dollars(budget->max_dollars)
                                                   : g_strdup("no cap");
    g_autofree char *dollars = g_strdup_printf("%s of %s", spent, cap);
    gtk_list_box_append(
        self->lists[PAGE_BUDGETS],
        meter("Spend this cycle", dollars,
              budget->has_max_dollars ? kr_format_fraction(budget->spent_dollars,
                                                           budget->max_dollars)
                                      : 0.0));
    g_autofree char *turns =
        kr_format_turns(budget->spent_turns, budget->has_max_turns ? budget->max_turns : 0);
    gtk_list_box_append(self->lists[PAGE_BUDGETS],
                        meter("Turns this cycle", turns,
                              budget->has_max_turns
                                  ? kr_format_fraction((double) budget->spent_turns,
                                                       (double) budget->max_turns)
                                  : 0.0));
    if (budget->exhausted) {
        GtkWidget *warn = row("This budget is spent",
                              "Its gate is waiting: raise the cap there, or let it rest.");
        adw_action_row_add_prefix(ADW_ACTION_ROW(warn),
                                  gtk_image_new_from_icon_name("dialog-warning-symbolic"));
        gtk_list_box_append(self->lists[PAGE_BUDGETS], warn);
    }
    show_list(self, PAGE_BUDGETS, TRUE);
}

/* ---- doctor -------------------------------------------------------------------------- */

static void
render_doctor(KrWindow *self)
{
    const KrDoctor *doctor = kr_state_doctor(self->app->state);
    gtk_list_box_remove_all(self->lists[PAGE_DOCTOR]);
    if (doctor == NULL) {
        show_list(self, PAGE_DOCTOR, FALSE);
        return;
    }
    for (guint i = 0; i < doctor->checks->len; i++) {
        const KrDoctorCheck *check = g_ptr_array_index(doctor->checks, i);
        GtkWidget *widget = row(check->name, check->detail);
        gboolean pass = g_ascii_strcasecmp(check->mark, "PASS") == 0;
        gboolean fail = g_ascii_strcasecmp(check->mark, "FAIL") == 0;
        adw_action_row_add_suffix(
            ADW_ACTION_ROW(widget),
            pill(check->mark, pass ? "success" : fail ? "error" : "warning"));
        gtk_list_box_append(self->lists[PAGE_DOCTOR], widget);
    }
    show_list(self, PAGE_DOCTOR, doctor->checks->len > 0);
}

/* ---- devices ------------------------------------------------------------------------- */

typedef struct {
    KrWindow *self;
    char *host;
    guint16 port;
} HubChoice;

static void
hub_choice_free(gpointer data, GClosure *closure)
{
    (void) closure;
    HubChoice *choice = data;
    g_free(choice->host);
    g_free(choice);
}

static void
on_use_hub(GtkButton *button, gpointer data)
{
    (void) button;
    HubChoice *choice = data;
    kr_app_use_hub(choice->self->app, choice->host, choice->port);
}

static GtkWidget *
use_button(KrWindow *self, const char *host, guint16 port)
{
    HubChoice *choice = g_new0(HubChoice, 1);
    choice->self = self;
    choice->host = g_strdup(host);
    choice->port = port;
    GtkWidget *button = gtk_button_new_with_label("Use");
    gtk_widget_set_valign(button, GTK_ALIGN_CENTER);
    g_signal_connect_data(button, "clicked", G_CALLBACK(on_use_hub), choice, hub_choice_free, 0);
    return button;
}

static void
on_pair_code(AdwEntryRow *entry, gpointer data)
{
    KrWindow *self = data;
    g_autofree char *code = kr_pairing_code_normalise(gtk_editable_get_text(GTK_EDITABLE(entry)));
    if (code == NULL) {
        kr_window_toast(self->app->window, "A pairing code is six digits.");
        return;
    }
    /* The hub's half of pairing is its own change (ADR-0068); until it lands, a code is
     * checked here and the person is told plainly that the hub cannot take it yet. */
    kr_window_toast(self->app->window,
                    "Code accepted. This hub cannot pair devices yet: it lands with the "
                    "hub's pairing change.");
}

static void
render_devices(KrWindow *self)
{
    GtkListBox *list = self->lists[PAGE_DEVICES];
    gtk_list_box_remove_all(list);

    const KrHubEndpoint *endpoint = kr_hub_client_endpoint(self->app->client);
    g_autofree char *current = g_strdup_printf("Connected to %s:%u", endpoint->host,
                                               endpoint->port);
    GtkWidget *here = row("This computer", "vibey serve on this computer, with its token");
    adw_action_row_add_suffix(ADW_ACTION_ROW(here), use_button(self, NULL, 0));
    gtk_list_box_append(list, here);

    if (self->app->discovery != NULL) {
        g_autoptr(GPtrArray) services = kr_discovery_services(self->app->discovery);
        for (guint i = 0; i < services->len; i++) {
            const KrHubService *service = g_ptr_array_index(services, i);
            g_autofree char *where = g_strdup_printf("%s:%u%s%s", service->host, service->port,
                                                     service->version ? " · vibey " : "",
                                                     service->version ? service->version : "");
            GtkWidget *found = row(service->name, where);
            adw_action_row_add_suffix(ADW_ACTION_ROW(found),
                                      use_button(self, service->host, service->port));
            gtk_list_box_append(list, found);
        }
    } else {
        gtk_list_box_append(list, row("Hubs on this network are not being looked for",
                                      self->app->discovery_problem));
    }

    GtkWidget *pair = adw_entry_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(pair), "Pair with a 6-digit code");
    adw_entry_row_set_show_apply_button(ADW_ENTRY_ROW(pair), TRUE);
    adw_entry_row_set_input_purpose(ADW_ENTRY_ROW(pair), GTK_INPUT_PURPOSE_DIGITS);
    g_signal_connect(pair, "apply", G_CALLBACK(on_pair_code), self);
    gtk_list_box_append(list, pair);
    gtk_list_box_append(list, row(current, kr_state_connection_message(self->app->state)));
    show_list(self, PAGE_DEVICES, TRUE);
}

void
kr_window_devices_changed(GtkWidget *window)
{
    render_devices(window_of(window));
}

/* ---- settings ------------------------------------------------------------------------ */

static void
on_theme_selected(AdwComboRow *combo, GParamSpec *pspec, gpointer data)
{
    (void) pspec;
    KrWindow *self = data;
    static const VibeyThemeMode modes[] = {VIBEY_THEME_MODE_SYSTEM, VIBEY_THEME_MODE_LIGHT,
                                           VIBEY_THEME_MODE_DARK};
    guint selected = adw_combo_row_get_selected(combo);
    if (selected >= G_N_ELEMENTS(modes))
        return;
    self->app->settings->theme = modes[selected];
    kr_app_apply_theme(self->app);
    kr_app_save_settings(self->app);
}

static void
on_switch(AdwSwitchRow *toggle, GParamSpec *pspec, gpointer data)
{
    (void) pspec;
    KrWindow *self = data;
    gboolean *field = g_object_get_data(G_OBJECT(toggle), "field");
    *field = adw_switch_row_get_active(toggle);
    kr_app_save_settings(self->app);
}

static GtkWidget *
switch_row(KrWindow *self, const char *title, const char *subtitle, gboolean *field)
{
    GtkWidget *toggle = adw_switch_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(toggle), title);
    adw_action_row_set_subtitle(ADW_ACTION_ROW(toggle), subtitle);
    adw_switch_row_set_active(ADW_SWITCH_ROW(toggle), *field);
    g_object_set_data(G_OBJECT(toggle), "field", field);
    g_signal_connect(toggle, "notify::active", G_CALLBACK(on_switch), self);
    return toggle;
}

static void
build_settings(KrWindow *self)
{
    GtkListBox *list = self->lists[PAGE_SETTINGS];
    const char *const modes[] = {"System", "Light", "Dark", NULL};
    GtkWidget *theme = adw_combo_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(theme), "Appearance");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(theme), "System follows your desktop, live");
    g_autoptr(GtkStringList) choices = gtk_string_list_new(modes);
    adw_combo_row_set_model(ADW_COMBO_ROW(theme), G_LIST_MODEL(choices));
    guint selected = self->app->settings->theme == VIBEY_THEME_MODE_LIGHT  ? 1
                     : self->app->settings->theme == VIBEY_THEME_MODE_DARK ? 2
                                                                           : 0;
    adw_combo_row_set_selected(ADW_COMBO_ROW(theme), selected);
    g_signal_connect(theme, "notify::selected", G_CALLBACK(on_theme_selected), self);
    gtk_list_box_append(list, theme);

    gtk_list_box_append(list, switch_row(self, "Notifications",
                                         "Say when a gate needs you, even with the window closed",
                                         &self->app->settings->notifications));
    gtk_list_box_append(list, switch_row(self, "Sounds", "Play vibey's own sounds with them",
                                         &self->app->settings->sounds));
    g_autofree char *about = g_strdup_printf("%s %s", kr_channel_display_name(self->app->channel),
                                             KRYPTON_VERSION);
    gtk_list_box_append(list, row(about, kr_channel_app_id(self->app->channel)));
    show_list(self, PAGE_SETTINGS, TRUE);
}

/* ---- the state speaks ---------------------------------------------------------------- */

static void
render_connection(KrWindow *self)
{
    KrConnection connection = kr_state_connection(self->app->state);
    const char *message = kr_state_connection_message(self->app->state);
    gboolean trouble = connection == KR_CONNECTION_REFUSED || connection == KR_CONNECTION_OFFLINE;
    adw_banner_set_title(self->banner, message != NULL ? message : "");
    adw_banner_set_revealed(self->banner, trouble);
    render_devices(self);
}

static void
on_state(KrState *state, KrStateSlice slice, gpointer data)
{
    (void) state;
    KrWindow *self = data;
    switch (slice) {
    case KR_STATE_PROJECTS:
        render_projects(self);
        render_budgets(self);
        break;
    case KR_STATE_GATES:
        render_gates(self);
        break;
    case KR_STATE_LANES:
        render_lanes(self);
        break;
    case KR_STATE_LOOPS:
        render_loops(self);
        break;
    case KR_STATE_DOCTOR:
        render_doctor(self);
        break;
    case KR_STATE_BUDGET:
    case KR_STATE_SELECTION:
        render_budgets(self);
        break;
    case KR_STATE_CONNECTION:
        render_connection(self);
        break;
    }
}

/* ---- the frame ----------------------------------------------------------------------- */

void
kr_window_show_page(GtkWidget *window, const char *name)
{
    KrWindow *self = window_of(window);
    for (int i = 0; i < KR_WINDOW_PAGES; i++) {
        if (g_str_equal(kr_window_page_names[i], name)) {
            gtk_list_box_select_row(self->sidebar, gtk_list_box_get_row_at_index(self->sidebar, i));
            return;
        }
    }
}

static void
on_place_selected(GtkListBox *box, GtkListBoxRow *selected, gpointer data)
{
    (void) box;
    KrWindow *self = data;
    if (selected == NULL)
        return;
    int index = gtk_list_box_row_get_index(selected);
    gtk_stack_set_visible_child_name(self->stack, kr_window_page_names[index]);
    adw_navigation_page_set_title(self->content_page, PLACES[index].title);
    adw_navigation_split_view_set_show_content(self->split, TRUE);
    if (index == PAGE_DEVICES)
        render_devices(self);
}

static GtkWidget *
place_row(KrWindow *self, int index)
{
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_set_margin_top(box, 8);
    gtk_widget_set_margin_bottom(box, 8);
    gtk_widget_set_margin_start(box, 6);
    gtk_widget_set_margin_end(box, 6);
    gtk_box_append(GTK_BOX(box), gtk_image_new_from_icon_name(PLACES[index].icon));
    GtkWidget *label = gtk_label_new(PLACES[index].title);
    gtk_label_set_xalign(GTK_LABEL(label), 0.0f);
    gtk_widget_set_hexpand(label, TRUE);
    gtk_box_append(GTK_BOX(box), label);
    if (index == PAGE_GATES) {
        self->gates_badge = pill("0", "accent");
        gtk_widget_set_visible(self->gates_badge, FALSE);
        gtk_box_append(GTK_BOX(box), self->gates_badge);
    }
    return box;
}

static void
on_refresh_clicked(GtkButton *button, gpointer data)
{
    (void) button;
    KrWindow *self = data;
    kr_app_refresh(self->app);
}

static void
on_destroy(GtkWidget *widget, gpointer data)
{
    (void) widget;
    KrWindow *self = data;
    kr_state_unlisten(self->app->state, self->listener);
    self->app->window = NULL;
}

GtkWidget *
kr_window_new(KrApp *app)
{
    KrWindow *self = g_new0(KrWindow, 1);
    self->app = app;

    GtkWidget *window = adw_application_window_new(GTK_APPLICATION(app->application));
    gtk_window_set_title(GTK_WINDOW(window), kr_channel_display_name(app->channel));
    gtk_window_set_default_size(GTK_WINDOW(window), 1080, 720);
    g_object_set_data_full(G_OBJECT(window), "kr-window", self, g_free);
    app->window = window;

    /* The sidebar: the mark, the name, the places. */
    GtkWidget *sidebar = gtk_list_box_new();
    gtk_widget_add_css_class(sidebar, "navigation-sidebar");
    self->sidebar = GTK_LIST_BOX(sidebar);
    for (int i = 0; i < KR_WINDOW_PAGES; i++)
        gtk_list_box_append(self->sidebar, place_row(self, i));
    g_signal_connect(sidebar, "row-selected", G_CALLBACK(on_place_selected), self);

    GtkWidget *brand = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    self->mark = kr_mark_new(28);
    gtk_box_append(GTK_BOX(brand), self->mark);
    GtkWidget *name = gtk_label_new(kr_channel_display_name(app->channel));
    gtk_widget_add_css_class(name, "heading");
    gtk_box_append(GTK_BOX(brand), name);

    GtkWidget *sidebar_header = adw_header_bar_new();
    adw_header_bar_set_title_widget(ADW_HEADER_BAR(sidebar_header), brand);
    GtkWidget *sidebar_view = adw_toolbar_view_new();
    adw_toolbar_view_add_top_bar(ADW_TOOLBAR_VIEW(sidebar_view), sidebar_header);
    GtkWidget *sidebar_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(sidebar_scroll), sidebar);
    adw_toolbar_view_set_content(ADW_TOOLBAR_VIEW(sidebar_view), sidebar_scroll);
    AdwNavigationPage *sidebar_page =
        adw_navigation_page_new(sidebar_view, kr_channel_display_name(app->channel));

    /* The content: one page per place. */
    GtkWidget *stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(stack), GTK_STACK_TRANSITION_TYPE_CROSSFADE);
    self->stack = GTK_STACK(stack);
    const char *const empty_titles[KR_WINDOW_PAGES] = {
        "No projects yet",
        "Nothing is waiting on you",
        "No lanes running",
        "Loops are not known yet",
        "Choose a project",
        "The doctor has not been asked",
        "Devices",
        "Settings",
    };
    const char *const empty_descriptions[KR_WINDOW_PAGES] = {
        "Start one with: vibey new NAME --repo PATH",
        "When vibey needs a decision, it appears here and Krypton tells you.",
        "Lanes started on this computer appear here as they run.",
        "Krypton asks the hub which loops, engines and efforts there are.",
        "Pick a project to see what it has spent this cycle.",
        "Refresh to run the checks the hub can run itself.",
        "",
        "",
    };
    for (int i = 0; i < KR_WINDOW_PAGES; i++)
        gtk_stack_add_named(GTK_STACK(stack),
                            list_page(self, i, empty_titles[i], empty_descriptions[i]),
                            kr_window_page_names[i]);

    GtkWidget *refresh = gtk_button_new_from_icon_name("view-refresh-symbolic");
    gtk_widget_set_tooltip_text(refresh, "Refresh (Ctrl+R)");
    g_signal_connect(refresh, "clicked", G_CALLBACK(on_refresh_clicked), self);
    GtkWidget *content_header = adw_header_bar_new();
    adw_header_bar_pack_end(ADW_HEADER_BAR(content_header), refresh);

    GtkWidget *banner = adw_banner_new("");
    adw_banner_set_use_markup(ADW_BANNER(banner), FALSE);
    self->banner = ADW_BANNER(banner);

    GtkWidget *content_view = adw_toolbar_view_new();
    adw_toolbar_view_add_top_bar(ADW_TOOLBAR_VIEW(content_view), content_header);
    adw_toolbar_view_add_top_bar(ADW_TOOLBAR_VIEW(content_view), banner);
    adw_toolbar_view_set_content(ADW_TOOLBAR_VIEW(content_view), stack);
    self->content_page = adw_navigation_page_new(content_view, PLACES[0].title);

    GtkWidget *split = adw_navigation_split_view_new();
    self->split = ADW_NAVIGATION_SPLIT_VIEW(split);
    adw_navigation_split_view_set_sidebar(self->split, sidebar_page);
    adw_navigation_split_view_set_content(self->split, self->content_page);

    /* Below 720px the split folds into one pane with back navigation. */
    AdwBreakpoint *narrow =
        adw_breakpoint_new(adw_breakpoint_condition_parse("max-width: 720sp"));
    GValue collapsed = G_VALUE_INIT;
    g_value_init(&collapsed, G_TYPE_BOOLEAN);
    g_value_set_boolean(&collapsed, TRUE);
    adw_breakpoint_add_setter(narrow, G_OBJECT(split), "collapsed", &collapsed);
    g_value_unset(&collapsed);
    adw_application_window_add_breakpoint(ADW_APPLICATION_WINDOW(window), narrow);

    GtkWidget *overlay = adw_toast_overlay_new();
    self->overlay = ADW_TOAST_OVERLAY(overlay);
    adw_toast_overlay_set_child(self->overlay, split);
    adw_application_window_set_content(ADW_APPLICATION_WINDOW(window), overlay);

    build_settings(self);
    self->listener = kr_state_listen(app->state, on_state, self);
    g_signal_connect(window, "destroy", G_CALLBACK(on_destroy), self);

    render_projects(self);
    render_gates(self);
    render_lanes(self);
    render_loops(self);
    render_budgets(self);
    render_doctor(self);
    render_connection(self);
    gtk_list_box_select_row(self->sidebar, gtk_list_box_get_row_at_index(self->sidebar, 0));
    return window;
}
