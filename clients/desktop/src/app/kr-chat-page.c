/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-chat-page.h"

#include "kr-a11y.h"
#include "kr-answer.h"
#include "kr-chat.h"
#include "kr-format.h"
#include "kr-window.h"

typedef struct {
    KrApp *app;
    GtkListBox *sessions;
    GtkBox *transcript;
    GtkScrolledWindow *transcript_scroll;
    GtkListBox *gate_cards;
    GtkWidget *gate_section;
    GtkListBox *completions;
    GtkPopover *completion_popover;
    GtkEntry *composer;
    GtkWidget *send_button;
    GtkLabel *session_heading;
    GtkLabel *session_subtitle;
    gboolean updating_sessions;
} ChatPage;

static ChatPage *
chat_page_of(GtkWidget *widget)
{
    return g_object_get_data(G_OBJECT(widget), "kr-chat-page");
}

static void
clear_box(GtkBox *box)
{
    for (GtkWidget *child; (child = gtk_widget_get_first_child(GTK_WIDGET(box))) != NULL;)
        gtk_box_remove(box, child);
}

static GtkWidget *
badge_pill(const char *text, const char *css_class)
{
    GtkWidget *label = gtk_label_new(text);
    gtk_widget_add_css_class(label, "caption-heading");
    if (css_class != NULL)
        gtk_widget_add_css_class(label, css_class);
    gtk_widget_set_valign(label, GTK_ALIGN_CENTER);
    return label;
}

static void
scroll_to_bottom(ChatPage *self)
{
    GtkAdjustment *adj = gtk_scrolled_window_get_vadjustment(self->transcript_scroll);
    if (adj != NULL) {
        double upper = gtk_adjustment_get_upper(adj);
        double page_size = gtk_adjustment_get_page_size(adj);
        gtk_adjustment_set_value(adj, upper > page_size ? upper - page_size : 0.0);
    }
}

/* ---- inline gate approval cards ------------------------------------------------------ */

typedef struct {
    KrApp *app;
    KrGate *gate;
    GtkEditable *entry;
} ChatGateAction;

static void
chat_gate_action_free(gpointer data, GClosure *closure)
{
    (void) closure;
    ChatGateAction *act = data;
    kr_gate_free(act->gate);
    g_free(act);
}

static KrGate *
gate_from_card(const KrChatGateCard *card)
{
    KrGate *gate = g_new0(KrGate, 1);
    gate->gate_id = g_strdup(card->gate_id);
    gate->project_id = g_strdup(card->project_id);
    gate->kind = g_strdup(card->kind);
    gate->prompt = g_strdup(card->prompt);
    gate->options = g_strdupv(card->options);
    gate->default_answer = g_strdup(card->default_answer);
    return gate;
}

static KrGate *
copy_state_gate(const KrGate *src)
{
    KrGate *gate = g_new0(KrGate, 1);
    gate->gate_id = g_strdup(src->gate_id);
    gate->project_id = g_strdup(src->project_id);
    gate->project_name = g_strdup(src->project_name);
    gate->job_id = g_strdup(src->job_id);
    gate->kind = g_strdup(src->kind);
    gate->prompt = g_strdup(src->prompt);
    gate->options = g_strdupv(src->options);
    gate->default_answer = g_strdup(src->default_answer);
    gate->answer_with = g_strdup(src->answer_with);
    gate->raised_at = src->raised_at;
    gate->timeout_at = src->timeout_at;
    return gate;
}

static void
on_gate_option_clicked(GtkButton *button, gpointer data)
{
    ChatGateAction *act = data;
    const char *choice = g_object_get_data(G_OBJECT(button), "gate-choice");
    kr_app_answer(act->app, act->gate, choice);
}

static void
on_gate_entry_submit(GtkWidget *widget, gpointer data)
{
    (void) widget;
    ChatGateAction *act = data;
    const char *typed = act->entry != NULL ? gtk_editable_get_text(act->entry) : "";
    kr_app_answer(act->app, act->gate, typed);
}

static GtkWidget *
build_gate_row(KrApp *app, const KrGate *gate)
{
    gboolean spends = kr_gate_spends(gate);
    g_autofree char *subtitle = g_strdup_printf(
        "%s · %s",
        gate->project_name != NULL ? gate->project_name : "project",
        spends ? "SPEND GATE (requires host or spend scope)" : gate->kind);

    GtkWidget *expander = adw_expander_row_new();
    adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(expander), FALSE);
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(expander),
                                  gate->prompt != NULL ? gate->prompt : gate->kind);
    adw_expander_row_set_subtitle(ADW_EXPANDER_ROW(expander), subtitle);
    adw_expander_row_set_expanded(ADW_EXPANDER_ROW(expander), TRUE);
    adw_expander_row_add_suffix(ADW_EXPANDER_ROW(expander),
                                badge_pill(spends ? "SPEND GATE" : "GATE",
                                           spends ? "warning" : "accent"));

    const char *grant_key = NULL;
    KrAnswerShape shape = kr_answer_shape(gate->kind, &grant_key);
    if ((shape == KR_ANSWER_VERDICT || shape == KR_ANSWER_CHOICE) && gate->options != NULL &&
        gate->options[0] != NULL) {
        GtkWidget *action_row = adw_action_row_new();
        adw_preferences_row_set_title(ADW_PREFERENCES_ROW(action_row),
                                      spends ? "Approve spend decision" : "Choose an answer");
        for (gsize i = 0; gate->options[i] != NULL; i++) {
            GtkWidget *btn = gtk_button_new_with_label(gate->options[i]);
            gtk_widget_set_valign(btn, GTK_ALIGN_CENTER);
            if (i == 0)
                gtk_widget_add_css_class(btn, spends ? "warning" : "suggested-action");
            g_object_set_data_full(G_OBJECT(btn), "gate-choice", g_strdup(gate->options[i]), g_free);
            ChatGateAction *act = g_new0(ChatGateAction, 1);
            act->app = app;
            act->gate = copy_state_gate(gate);
            g_signal_connect_data(btn, "clicked", G_CALLBACK(on_gate_option_clicked), act,
                                  chat_gate_action_free, 0);
            adw_action_row_add_suffix(ADW_ACTION_ROW(action_row), btn);
        }
        adw_expander_row_add_row(ADW_EXPANDER_ROW(expander), action_row);
    } else if (shape == KR_ANSWER_DEFAULTS || shape == KR_ANSWER_ANY) {
        GtkWidget *action_row = adw_action_row_new();
        adw_preferences_row_set_title(
            ADW_PREFERENCES_ROW(action_row),
            shape == KR_ANSWER_DEFAULTS ? "Accept recommended defaults" : "Continue");
        GtkWidget *btn = gtk_button_new_with_label(
            shape == KR_ANSWER_DEFAULTS ? "Accept defaults" : "Retry");
        gtk_widget_set_valign(btn, GTK_ALIGN_CENTER);
        gtk_widget_add_css_class(btn, "suggested-action");
        g_object_set_data_full(G_OBJECT(btn), "gate-choice", g_strdup(""), g_free);
        ChatGateAction *act = g_new0(ChatGateAction, 1);
        act->app = app;
        act->gate = copy_state_gate(gate);
        g_signal_connect_data(btn, "clicked", G_CALLBACK(on_gate_option_clicked), act,
                              chat_gate_action_free, 0);
        adw_action_row_add_suffix(ADW_ACTION_ROW(action_row), btn);
        adw_expander_row_add_row(ADW_EXPANDER_ROW(expander), action_row);
    } else {
        GtkWidget *entry = adw_entry_row_new();
        g_autofree char *label =
            grant_key != NULL ? g_strdup_printf("New %s (non-negative number)", grant_key)
                              : g_strdup("Answer (JSON object)");
        adw_preferences_row_set_title(ADW_PREFERENCES_ROW(entry), label);
        GtkWidget *btn = gtk_button_new_with_label(spends ? "Approve spend" : "Send answer");
        gtk_widget_set_valign(btn, GTK_ALIGN_CENTER);
        gtk_widget_add_css_class(btn, spends ? "warning" : "suggested-action");
        ChatGateAction *act = g_new0(ChatGateAction, 1);
        act->app = app;
        act->gate = copy_state_gate(gate);
        act->entry = GTK_EDITABLE(entry);
        g_signal_connect_data(btn, "clicked", G_CALLBACK(on_gate_entry_submit), act,
                              chat_gate_action_free, 0);
        adw_entry_row_add_suffix(ADW_ENTRY_ROW(entry), btn);
        adw_expander_row_add_row(ADW_EXPANDER_ROW(expander), entry);
    }
    return expander;
}

/* ---- transcript cards ---------------------------------------------------------------- */

static GtkWidget *
build_bubble_card(const char *role_label, const char *role_css, const char *body_text)
{
    GtkWidget *card = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(card, "card");
    gtk_widget_set_margin_top(card, 4);
    gtk_widget_set_margin_bottom(card, 4);

    GtkWidget *inner = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_set_margin_top(inner, 10);
    gtk_widget_set_margin_bottom(inner, 10);
    gtk_widget_set_margin_start(inner, 14);
    gtk_widget_set_margin_end(inner, 14);

    GtkWidget *header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_append(GTK_BOX(header), badge_pill(role_label, role_css));
    gtk_box_append(GTK_BOX(inner), header);

    GtkWidget *body = gtk_label_new(body_text != NULL ? body_text : "");
    gtk_label_set_xalign(GTK_LABEL(body), 0.0f);
    gtk_label_set_wrap(GTK_LABEL(body), TRUE);
    gtk_label_set_selectable(GTK_LABEL(body), TRUE);
    gtk_box_append(GTK_BOX(inner), body);

    gtk_box_append(GTK_BOX(card), inner);
    return card;
}

static GtkWidget *
build_tool_call_card(const KrChatToolCall *call)
{
    GtkWidget *list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(list), GTK_SELECTION_NONE);
    gtk_widget_add_css_class(list, "boxed-list");

    GtkWidget *expander = adw_expander_row_new();
    adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(expander), FALSE);
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(expander), call->name);
    adw_expander_row_set_subtitle(ADW_EXPANDER_ROW(expander), call->arguments_json);
    adw_expander_row_add_suffix(ADW_EXPANDER_ROW(expander), badge_pill("TOOL", "dim-label"));

    GtkWidget *result_row = adw_action_row_new();
    adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(result_row), FALSE);
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(result_row), "Result");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(result_row), call->result_json);
    adw_expander_row_add_row(ADW_EXPANDER_ROW(expander), result_row);

    gtk_list_box_append(GTK_LIST_BOX(list), expander);
    return list;
}

/* ---- slash-command completions ------------------------------------------------------- */

static void
on_completion_activated(GtkListBox *box, GtkListBoxRow *row_widget, gpointer data)
{
    (void) box;
    ChatPage *self = data;
    if (row_widget == NULL)
        return;
    const char *slash = g_object_get_data(G_OBJECT(row_widget), "slash-name");
    if (slash == NULL)
        return;
    g_autofree char *filled = g_strdup_printf("/%s ", slash);
    gtk_editable_set_text(GTK_EDITABLE(self->composer), filled);
    gtk_editable_set_position(GTK_EDITABLE(self->composer), -1);
    gtk_popover_popdown(self->completion_popover);
    gtk_widget_grab_focus(GTK_WIDGET(self->composer));
}

static void
update_completions(ChatPage *self, const char *typed)
{
    gtk_list_box_remove_all(self->completions);
    if (typed == NULL || typed[0] != '/' || strchr(typed, ' ') != NULL) {
        gtk_popover_popdown(self->completion_popover);
        return;
    }
    gsize matched = 0;
    g_autofree const KrChatSlashSpec **specs = kr_chat_slash_complete(typed, &matched);
    if (matched == 0) {
        gtk_popover_popdown(self->completion_popover);
        return;
    }
    for (gsize i = 0; i < matched; i++) {
        GtkWidget *item = adw_action_row_new();
        adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(item), FALSE);
        adw_preferences_row_set_title(ADW_PREFERENCES_ROW(item), specs[i]->usage);
        adw_action_row_set_subtitle(ADW_ACTION_ROW(item), specs[i]->description);
        gtk_list_box_row_set_activatable(GTK_LIST_BOX_ROW(item), TRUE);
        g_object_set_data_full(G_OBJECT(item), "slash-name", g_strdup(specs[i]->slash), g_free);
        gtk_list_box_append(self->completions, item);
    }
    gtk_popover_popup(self->completion_popover);
}

static void
on_composer_changed(GtkEditable *editable, gpointer data)
{
    ChatPage *self = data;
    const char *typed = gtk_editable_get_text(editable);
    update_completions(self, typed);
}

static void
send_current_message(ChatPage *self)
{
    const char *typed = gtk_editable_get_text(GTK_EDITABLE(self->composer));
    g_autofree char *trimmed = g_strstrip(g_strdup(typed != NULL ? typed : ""));
    if (trimmed[0] == '\0')
        return;
    gtk_popover_popdown(self->completion_popover);
    gtk_editable_set_text(GTK_EDITABLE(self->composer), "");
    kr_app_chat_send(self->app, trimmed);
}

static void
on_composer_activate(GtkEntry *entry, gpointer data)
{
    (void) entry;
    send_current_message(data);
}

static void
on_send_clicked(GtkButton *button, gpointer data)
{
    (void) button;
    send_current_message(data);
}

static void
on_quick_chip_clicked(GtkButton *button, gpointer data)
{
    ChatPage *self = data;
    const char *command = g_object_get_data(G_OBJECT(button), "quick-command");
    if (command != NULL)
        kr_app_chat_send(self->app, command);
}

/* ---- session sidebar (projects as sessions) ------------------------------------------ */

static void render_sessions_and_gates(ChatPage *self);

static void
on_session_selected(GtkListBox *box, GtkListBoxRow *selected, gpointer data)
{
    (void) box;
    ChatPage *self = data;
    if (self->updating_sessions || selected == NULL)
        return;
    const char *project_id = g_object_get_data(G_OBJECT(selected), "project-id");
    kr_state_select_project(self->app->state, project_id);
    if (project_id != NULL) {
        kr_app_refresh_budget(self->app, project_id);
        kr_app_refresh_ledger(self->app, project_id);
    }
    render_sessions_and_gates(self);
}

static void
render_sessions_and_gates(ChatPage *self)
{
    self->updating_sessions = TRUE;
    gtk_list_box_remove_all(self->sessions);

    const char *selected_id = kr_state_selected_project(self->app->state);
    GPtrArray *projects = kr_state_projects(self->app->state);

    /* Row 0: All projects overview session */
    GtkWidget *overview = adw_action_row_new();
    adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(overview), FALSE);
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(overview), "All projects");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(overview), "Hub overview & global commands");
    gtk_list_box_row_set_activatable(GTK_LIST_BOX_ROW(overview), TRUE);
    gtk_list_box_append(self->sessions, overview);
    GtkListBoxRow *to_select = gtk_list_box_get_row_at_index(self->sessions, 0);

    for (guint i = 0; i < projects->len; i++) {
        const KrProject *project = g_ptr_array_index(projects, i);
        g_autofree char *sub = g_strdup_printf("%s · cycle %" G_GINT64_FORMAT,
                                               kr_format_phase(project->phase), project->cycle);
        GtkWidget *row = adw_action_row_new();
        adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(row), FALSE);
        adw_preferences_row_set_title(ADW_PREFERENCES_ROW(row), project->name);
        adw_action_row_set_subtitle(ADW_ACTION_ROW(row), sub);
        if (project->open_gates > 0) {
            g_autofree char *badge = g_strdup_printf("%" G_GINT64_FORMAT, project->open_gates);
            adw_action_row_add_suffix(ADW_ACTION_ROW(row), badge_pill(badge, "warning"));
        }
        gtk_list_box_row_set_activatable(GTK_LIST_BOX_ROW(row), TRUE);
        g_object_set_data_full(G_OBJECT(row), "project-id", g_strdup(project->project_id), g_free);
        gtk_list_box_append(self->sessions, row);
        if (selected_id != NULL && g_str_equal(project->project_id, selected_id))
            to_select = gtk_list_box_get_row_at_index(self->sessions, (int) i + 1);
    }
    if (to_select != NULL)
        gtk_list_box_select_row(self->sessions, to_select);
    self->updating_sessions = FALSE;

    /* Update header title & subtitle for active session */
    const KrProject *active = kr_state_selected(self->app->state);
    if (active != NULL) {
        g_autofree char *sub = g_strdup_printf(
            "%s · cycle %" G_GINT64_FORMAT " of %" G_GINT64_FORMAT " · %s",
            kr_format_phase(active->phase), active->cycle, active->max_cycles, active->project_id);
        gtk_label_set_text(self->session_heading, active->name);
        gtk_label_set_text(self->session_subtitle, sub);
    } else {
        gtk_label_set_text(self->session_heading, "All projects");
        gtk_label_set_text(self->session_subtitle,
                           "Ask about projects, answer waiting gates, or type /new to start one");
    }

    /* Update inline open-gate cards for the active session */
    gtk_list_box_remove_all(self->gate_cards);
    g_autoptr(GPtrArray) open_gates = selected_id != NULL
                                          ? kr_state_gates_for(self->app->state, selected_id)
                                          : g_ptr_array_ref(kr_state_gates(self->app->state));
    for (guint i = 0; i < open_gates->len; i++) {
        const KrGate *gate = g_ptr_array_index(open_gates, i);
        gtk_list_box_append(self->gate_cards, build_gate_row(self->app, gate));
    }
    gtk_widget_set_visible(self->gate_section, open_gates->len > 0);
}

/* ---- public API ---------------------------------------------------------------------- */

void
kr_chat_page_refresh(GtkWidget *page)
{
    ChatPage *self = chat_page_of(page);
    if (self != NULL)
        render_sessions_and_gates(self);
}

void
kr_chat_page_append_turn(GtkWidget *page, const char *user_message, const KrChatTurn *turn)
{
    ChatPage *self = chat_page_of(page);
    if (self == NULL || turn == NULL)
        return;
    if (user_message != NULL && user_message[0] != '\0')
        gtk_box_append(self->transcript, build_bubble_card("YOU", "accent", user_message));

    for (guint i = 0; i < turn->tool_calls->len; i++) {
        const KrChatToolCall *call = g_ptr_array_index(turn->tool_calls, i);
        gtk_box_append(self->transcript, build_tool_call_card(call));
    }

    gtk_box_append(self->transcript, build_bubble_card("KRYPTON", "success", turn->reply));

    for (guint i = 0; i < turn->gates->len; i++) {
        const KrChatGateCard *card = g_ptr_array_index(turn->gates, i);
        KrGate *gate = gate_from_card(card);
        GtkWidget *list = gtk_list_box_new();
        gtk_list_box_set_selection_mode(GTK_LIST_BOX(list), GTK_SELECTION_NONE);
        gtk_widget_add_css_class(list, "boxed-list");
        gtk_list_box_append(GTK_LIST_BOX(list), build_gate_row(self->app, gate));
        kr_gate_free(gate);
        gtk_box_append(self->transcript, list);
    }
    scroll_to_bottom(self);
}

void
kr_chat_page_append_error(GtkWidget *page, const char *user_message, const char *error_text)
{
    ChatPage *self = chat_page_of(page);
    if (self == NULL)
        return;
    if (user_message != NULL && user_message[0] != '\0')
        gtk_box_append(self->transcript, build_bubble_card("YOU", "accent", user_message));
    gtk_box_append(self->transcript,
                   build_bubble_card("REFUSED", "error",
                                     error_text != NULL ? error_text : "Request failed"));
    scroll_to_bottom(self);
}

void
kr_chat_page_append_ledger(GtkWidget *page, const KrChatLedgerPage *ledger)
{
    ChatPage *self = chat_page_of(page);
    if (self == NULL || ledger == NULL || ledger->events->len == 0)
        return;
    for (guint i = 0; i < ledger->events->len; i++) {
        const KrChatNarration *ev = g_ptr_array_index(ledger->events, i);
        gtk_box_append(self->transcript, build_bubble_card("LEDGER", "dim-label", ev->summary));
    }
    scroll_to_bottom(self);
}

void
kr_chat_page_focus_composer(GtkWidget *page)
{
    ChatPage *self = chat_page_of(page);
    if (self != NULL && self->composer != NULL)
        gtk_widget_grab_focus(GTK_WIDGET(self->composer));
}

GtkWidget *
kr_chat_page_new(KrApp *app)
{
    ChatPage *self = g_new0(ChatPage, 1);
    self->app = app;

    GtkWidget *root = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_hexpand(root, TRUE);
    gtk_widget_set_vexpand(root, TRUE);
    g_object_set_data_full(G_OBJECT(root), "kr-chat-page", self, g_free);

    /* Left column: project sessions sidebar */
    GtkWidget *left = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_size_request(left, 240, -1);
    gtk_widget_set_margin_top(left, 12);
    gtk_widget_set_margin_bottom(left, 12);
    gtk_widget_set_margin_start(left, 12);
    gtk_widget_set_margin_end(left, 6);

    GtkWidget *left_header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *sessions_title = gtk_label_new("Sessions");
    gtk_widget_add_css_class(sessions_title, "heading");
    gtk_label_set_xalign(GTK_LABEL(sessions_title), 0.0f);
    gtk_widget_set_hexpand(sessions_title, TRUE);
    gtk_box_append(GTK_BOX(left_header), sessions_title);

    GtkWidget *new_btn = gtk_button_new_from_icon_name("list-add-symbolic");
    gtk_actionable_set_action_name(GTK_ACTIONABLE(new_btn), "app.start-project");
    gtk_widget_set_tooltip_text(new_btn, "Start a project (Ctrl+N)");
    kr_a11y_name(new_btn, "Start a project");
    gtk_box_append(GTK_BOX(left_header), new_btn);
    gtk_box_append(GTK_BOX(left), left_header);

    GtkWidget *sessions_list = gtk_list_box_new();
    gtk_widget_add_css_class(sessions_list, "navigation-sidebar");
    self->sessions = GTK_LIST_BOX(sessions_list);
    g_signal_connect(sessions_list, "row-selected", G_CALLBACK(on_session_selected), self);

    GtkWidget *sessions_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(sessions_scroll), sessions_list);
    gtk_widget_set_vexpand(sessions_scroll, TRUE);
    gtk_box_append(GTK_BOX(left), sessions_scroll);

    gtk_box_append(GTK_BOX(root), left);
    gtk_box_append(GTK_BOX(root), gtk_separator_new(GTK_ORIENTATION_VERTICAL));

    /* Right column: active session header, inline open gates, transcript, and bottom composer */
    GtkWidget *right = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_hexpand(right, TRUE);
    gtk_widget_set_vexpand(right, TRUE);
    gtk_widget_set_margin_top(right, 12);
    gtk_widget_set_margin_bottom(right, 12);
    gtk_widget_set_margin_start(right, 12);
    gtk_widget_set_margin_end(right, 12);

    /* Session header + quick command chips */
    GtkWidget *top_bar = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    GtkWidget *heading = gtk_label_new("All projects");
    gtk_widget_add_css_class(heading, "title-3");
    gtk_label_set_xalign(GTK_LABEL(heading), 0.0f);
    self->session_heading = GTK_LABEL(heading);
    gtk_box_append(GTK_BOX(top_bar), heading);

    GtkWidget *subtitle = gtk_label_new("");
    gtk_widget_add_css_class(subtitle, "dim-label");
    gtk_label_set_xalign(GTK_LABEL(subtitle), 0.0f);
    gtk_label_set_wrap(GTK_LABEL(subtitle), TRUE);
    self->session_subtitle = GTK_LABEL(subtitle);
    gtk_box_append(GTK_BOX(top_bar), subtitle);

    GtkWidget *chips = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    static const struct {
        const char *label;
        const char *cmd;
    } quick_commands[] = {
        {"Status", "/status"},
        {"Open gates", "/gates"},
        {"Budget", "/budget"},
        {"Queue", "/queue"},
        {"Lanes", "/lanes"},
        {"Doctor", "/doctor"},
        {"Help", "/help"},
    };
    for (gsize i = 0; i < G_N_ELEMENTS(quick_commands); i++) {
        GtkWidget *chip = gtk_button_new_with_label(quick_commands[i].label);
        gtk_widget_add_css_class(chip, "pill");
        g_object_set_data(G_OBJECT(chip), "quick-command", (gpointer) quick_commands[i].cmd);
        g_signal_connect(chip, "clicked", G_CALLBACK(on_quick_chip_clicked), self);
        gtk_box_append(GTK_BOX(chips), chip);
    }
    gtk_box_append(GTK_BOX(top_bar), chips);
    gtk_box_append(GTK_BOX(right), top_bar);

    /* Pinned open-gate approval cards for the selected session */
    GtkWidget *gate_section = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    GtkWidget *gate_title = gtk_label_new("Waiting for your decision");
    gtk_widget_add_css_class(gate_title, "heading");
    gtk_label_set_xalign(GTK_LABEL(gate_title), 0.0f);
    gtk_box_append(GTK_BOX(gate_section), gate_title);

    GtkWidget *gate_cards = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(gate_cards), GTK_SELECTION_NONE);
    gtk_widget_add_css_class(gate_cards, "boxed-list");
    self->gate_cards = GTK_LIST_BOX(gate_cards);
    gtk_box_append(GTK_BOX(gate_section), gate_cards);
    gtk_widget_set_visible(gate_section, FALSE);
    self->gate_section = gate_section;
    gtk_box_append(GTK_BOX(right), gate_section);

    /* Scrolling conversation transcript */
    GtkWidget *transcript = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    self->transcript = GTK_BOX(transcript);
    clear_box(self->transcript);
    gtk_box_append(
        self->transcript,
        build_bubble_card(
            "KRYPTON", "success",
            "Welcome to krypton chat. Pick a project on the left or type `/` for commands "
            "(`/projects`, `/status`, `/gates`, `/new <name> <what to build>`, `/help`)."));

    GtkWidget *clamp = adw_clamp_new();
    adw_clamp_set_maximum_size(ADW_CLAMP(clamp), 860);
    adw_clamp_set_child(ADW_CLAMP(clamp), transcript);

    GtkWidget *transcript_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(transcript_scroll), clamp);
    gtk_widget_set_vexpand(transcript_scroll, TRUE);
    self->transcript_scroll = GTK_SCROLLED_WINDOW(transcript_scroll);
    gtk_box_append(GTK_BOX(right), transcript_scroll);

    /* Bottom composer with `/` completion popover */
    GtkWidget *composer_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *composer = gtk_entry_new();
    gtk_entry_set_placeholder_text(
        GTK_ENTRY(composer),
        "Ask about a project, answer a gate, or type / for commands…");
    gtk_widget_set_hexpand(composer, TRUE);
    kr_a11y_name(composer, "Chat message or slash command");
    self->composer = GTK_ENTRY(composer);
    g_signal_connect(composer, "changed", G_CALLBACK(on_composer_changed), self);
    g_signal_connect(composer, "activate", G_CALLBACK(on_composer_activate), self);
    gtk_box_append(GTK_BOX(composer_box), composer);

    GtkWidget *popover = gtk_popover_new();
    gtk_popover_set_autohide(GTK_POPOVER(popover), FALSE);
    gtk_popover_set_position(GTK_POPOVER(popover), GTK_POS_TOP);
    gtk_widget_set_parent(popover, composer);
    GtkWidget *comp_list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(comp_list), GTK_SELECTION_SINGLE);
    gtk_widget_add_css_class(comp_list, "boxed-list");
    g_signal_connect(comp_list, "row-activated", G_CALLBACK(on_completion_activated), self);
    self->completions = GTK_LIST_BOX(comp_list);
    GtkWidget *comp_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_min_content_width(GTK_SCROLLED_WINDOW(comp_scroll), 420);
    gtk_scrolled_window_set_min_content_height(GTK_SCROLLED_WINDOW(comp_scroll), 220);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(comp_scroll), comp_list);
    gtk_popover_set_child(GTK_POPOVER(popover), comp_scroll);
    self->completion_popover = GTK_POPOVER(popover);

    GtkWidget *send_btn = gtk_button_new_with_label("Send");
    gtk_widget_add_css_class(send_btn, "suggested-action");
    kr_a11y_name(send_btn, "Send chat message");
    g_signal_connect(send_btn, "clicked", G_CALLBACK(on_send_clicked), self);
    self->send_button = send_btn;
    gtk_box_append(GTK_BOX(composer_box), send_btn);

    gtk_box_append(GTK_BOX(right), composer_box);
    gtk_box_append(GTK_BOX(root), right);

    render_sessions_and_gates(self);
    return root;
}
