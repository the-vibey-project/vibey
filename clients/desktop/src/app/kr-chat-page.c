/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-chat-page.h"

#include "kr-a11y.h"
#include "kr-answer.h"
#include "kr-chat.h"
#include "kr-format.h"
#include "kr-inspector.h"
#include "kr-mark.h"
#include "kr-settings-dialog.h"
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
    GtkWidget *attach_menu_button;
    GtkWidget *dictate_button;
    GtkWidget *model_chip_button;
    GtkWidget *project_selector_btn;
    GtkWidget *inspector;
    GtkWidget *inspector_toggle_btn;
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

/* ---- transcript cards & actions ------------------------------------------------------ */

static void
str_closure_free(gpointer data, GClosure *closure)
{
    (void) closure;
    g_free(data);
}

static void
on_copy_turn_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    const char *text = data;
    if (text != NULL) {
        GdkDisplay *disp = gdk_display_get_default();
        if (disp != NULL) {
            GdkClipboard *clip = gdk_display_get_clipboard(disp);
            gdk_clipboard_set_text(clip, text);
        }
    }
}

static GtkWidget *
build_bubble_card(ChatPage *self, const char *role_label, const char *role_css, const char *body_text)
{
    gboolean is_user = g_strcmp0(role_label, "YOU") == 0;
    GtkWidget *wrap = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);

    GtkWidget *card = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(card, is_user ? "chat-turn-bubble-user" : "chat-turn-bubble-agent");

    GtkWidget *inner = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);

    GtkWidget *header = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_append(GTK_BOX(header), badge_pill(role_label, role_css));
    gtk_box_append(GTK_BOX(inner), header);

    GtkWidget *body = gtk_label_new(body_text != NULL ? body_text : "");
    gtk_label_set_xalign(GTK_LABEL(body), 0.0f);
    gtk_label_set_wrap(GTK_LABEL(body), TRUE);
    gtk_label_set_selectable(GTK_LABEL(body), TRUE);
    gtk_box_append(GTK_BOX(inner), body);

    gtk_box_append(GTK_BOX(card), inner);
    gtk_box_append(GTK_BOX(wrap), card);

    /* Turn footer action row (Copy, thumbs, speech, timestamp) */
    GtkWidget *action_bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_widget_set_margin_start(action_bar, is_user ? 48 : 20);
    gtk_widget_set_margin_end(action_bar, is_user ? 20 : 48);

    GtkWidget *copy_btn = gtk_button_new_from_icon_name("edit-copy-symbolic");
    gtk_widget_add_css_class(copy_btn, "turn-action-btn");
    kr_a11y_name(copy_btn, "Copy message text");
    g_signal_connect_data(copy_btn, "clicked", G_CALLBACK(on_copy_turn_clicked),
                          g_strdup(body_text != NULL ? body_text : ""), str_closure_free, 0);
    gtk_box_append(GTK_BOX(action_bar), copy_btn);

    if (!is_user) {
        GtkWidget *th_up = gtk_button_new_from_icon_name("starred-symbolic");
        gtk_widget_add_css_class(th_up, "turn-action-btn");
        kr_a11y_name(th_up, "Thumbs up");
        gtk_box_append(GTK_BOX(action_bar), th_up);

        GtkWidget *spk = gtk_button_new_from_icon_name("audio-speakers-symbolic");
        gtk_widget_add_css_class(spk, "turn-action-btn");
        kr_a11y_name(spk, "Read aloud");
        gtk_box_append(GTK_BOX(action_bar), spk);
    }

    GtkWidget *time_lbl = gtk_label_new("just now");
    gtk_widget_add_css_class(time_lbl, "dim-label");
    gtk_box_append(GTK_BOX(action_bar), time_lbl);

    gtk_box_append(GTK_BOX(wrap), action_bar);
    return wrap;
}

static GtkWidget *
build_tool_call_card(const KrChatToolCall *call)
{
    GtkWidget *list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(list), GTK_SELECTION_NONE);
    gtk_widget_add_css_class(list, "boxed-list");
    gtk_widget_set_margin_start(list, 20);
    gtk_widget_set_margin_end(list, 20);

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

/* ---- sidebar quick buttons & project picker ------------------------------------------ */

static void
on_new_chat_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    ChatPage *self = data;
    clear_box(self->transcript);
    gtk_box_append(
        self->transcript,
        build_bubble_card(
            self, "VIBEY", "success",
            "Started a new session. Ask anything about your projects, trigger slash commands, or run /help."));
    scroll_to_bottom(self);
}

static void
on_search_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    ChatPage *self = data;
    gtk_editable_set_text(GTK_EDITABLE(self->composer), "/ledger ");
    gtk_editable_set_position(GTK_EDITABLE(self->composer), -1);
    gtk_widget_grab_focus(GTK_WIDGET(self->composer));
}

static void
on_artifacts_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    ChatPage *self = data;
    kr_app_toast(self->app, "Viewing artifacts repository.");
}

static void
on_customize_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    ChatPage *self = data;
    gtk_editable_set_text(GTK_EDITABLE(self->composer), "/loops");
    send_current_message(self);
}

static void
on_inspector_toggle_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    ChatPage *self = data;
    gboolean vis = gtk_widget_get_visible(self->inspector);
    gtk_widget_set_visible(self->inspector, !vis);
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
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(overview), "All projects overview");
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
        g_autofree char *btn_title = g_strdup_printf("%s ▾", active->name);
        gtk_button_set_label(GTK_BUTTON(self->project_selector_btn), btn_title);
    } else {
        gtk_label_set_text(self->session_heading, "All projects");
        gtk_label_set_text(self->session_subtitle,
                           "Ask about projects, answer waiting gates, or type /new to start one");
        gtk_button_set_label(GTK_BUTTON(self->project_selector_btn), "All projects ▾");
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

    /* Refresh right-hand inspector */
    kr_inspector_refresh(self->inspector);
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
        gtk_box_append(self->transcript, build_bubble_card(self, "YOU", "accent", user_message));

    for (guint i = 0; i < turn->tool_calls->len; i++) {
        const KrChatToolCall *call = g_ptr_array_index(turn->tool_calls, i);
        gtk_box_append(self->transcript, build_tool_call_card(call));
    }

    gtk_box_append(self->transcript, build_bubble_card(self, "HERETIC", "success", turn->reply));

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
        gtk_box_append(self->transcript, build_bubble_card(self, "YOU", "accent", user_message));
    gtk_box_append(self->transcript,
                   build_bubble_card(self, "REFUSED", "error",
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
        gtk_box_append(self->transcript, build_bubble_card(self, "LEDGER", "dim-label", ev->summary));
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

/* ---- User footer popover menu -------------------------------------------------------- */

static void
on_user_settings_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    ChatPage *self = data;
    kr_settings_dialog_present(self->app->window, self->app);
}

static GtkWidget *
build_account_popover(ChatPage *self)
{
    GtkWidget *popover = gtk_popover_new();
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_set_margin_top(box, 8);
    gtk_widget_set_margin_bottom(box, 8);
    gtk_widget_set_margin_start(box, 8);
    gtk_widget_set_margin_end(box, 8);

    GtkWidget *email = gtk_label_new("adam@matthewsteinberger.com");
    gtk_widget_add_css_class(email, "dim-label");
    gtk_label_set_xalign(GTK_LABEL(email), 0.0f);
    gtk_box_append(GTK_BOX(box), email);
    gtk_box_append(GTK_BOX(box), gtk_separator_new(GTK_ORIENTATION_HORIZONTAL));

    struct {
        const char *label;
        const char *icon;
    } items[] = {
        {"Settings", "emblem-system-symbolic"},
        {"Usage", "wallet-symbolic"},
        {"Language", "network-wireless-symbolic"},
        {"Get help", "dialog-information-symbolic"},
        {"Send feedback", "dialog-question-symbolic"},
        {"View all plans", "view-refresh-symbolic"},
        {"Get apps and extensions", "folder-symbolic"},
        {"View changelog", "text-x-generic-symbolic"},
        {"Learn more", "go-next-symbolic"},
        {"Get API keys", "system-search-symbolic"},
        {"Log out", "system-shutdown-symbolic"},
    };

    for (gsize i = 0; i < G_N_ELEMENTS(items); i++) {
        GtkWidget *b = gtk_button_new_with_label(items[i].label);
        gtk_widget_add_css_class(b, "flat");
        gtk_widget_set_halign(b, GTK_ALIGN_FILL);
        if (i == 0)
            g_signal_connect(b, "clicked", G_CALLBACK(on_user_settings_clicked), self);
        gtk_box_append(GTK_BOX(box), b);
    }

    gtk_popover_set_child(GTK_POPOVER(popover), box);
    return popover;
}

/* ---- Attach popover menu (+ button) -------------------------------------------------- */

static GtkWidget *
build_attach_popover(ChatPage *self)
{
    (void) self;
    GtkWidget *popover = gtk_popover_new();
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_set_margin_top(box, 6);
    gtk_widget_set_margin_bottom(box, 6);
    gtk_widget_set_margin_start(box, 6);
    gtk_widget_set_margin_end(box, 6);

    struct {
        const char *label;
        const char *icon;
    } items[] = {
        {"Add files or photos (⌘U)", "document-open-symbolic"},
        {"Add folder", "folder-symbolic"},
        {"Slash commands", "utilities-terminal-symbolic"},
        {"Connectors (1 needs reconnection >)", "network-wireless-symbolic"},
        {"Plugins >", "package-x-generic-symbolic"},
    };

    for (gsize i = 0; i < G_N_ELEMENTS(items); i++) {
        GtkWidget *b = gtk_button_new_with_label(items[i].label);
        gtk_widget_add_css_class(b, "flat");
        gtk_widget_set_halign(b, GTK_ALIGN_FILL);
        gtk_box_append(GTK_BOX(box), b);
    }
    gtk_popover_set_child(GTK_POPOVER(popover), box);
    return popover;
}

/* ---- Composer and root layout -------------------------------------------------------- */

static GtkWidget *
sidebar_nav_button(const char *label, const char *icon_name, GCallback callback, gpointer data)
{
    GtkWidget *btn = gtk_button_new();
    gtk_widget_add_css_class(btn, "sidebar-quick-btn");

    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_box_append(GTK_BOX(box), gtk_image_new_from_icon_name(icon_name));
    GtkWidget *lbl = gtk_label_new(label);
    gtk_label_set_xalign(GTK_LABEL(lbl), 0.0f);
    gtk_widget_set_hexpand(lbl, TRUE);
    gtk_box_append(GTK_BOX(box), lbl);

    gtk_button_set_child(GTK_BUTTON(btn), box);
    if (callback != NULL)
        g_signal_connect(btn, "clicked", callback, data);
    return btn;
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

    /* Left column: Quick Actions + Project Sessions + User Account Footer */
    GtkWidget *left = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_set_size_request(left, 240, -1);
    gtk_widget_set_margin_top(left, 8);
    gtk_widget_set_margin_bottom(left, 8);
    gtk_widget_set_margin_start(left, 6);
    gtk_widget_set_margin_end(left, 6);

    /* Quick actions */
    gtk_box_append(GTK_BOX(left), sidebar_nav_button("+ New", "document-new-symbolic", G_CALLBACK(on_new_chat_clicked), self));
    gtk_box_append(GTK_BOX(left), sidebar_nav_button("Search", "edit-find-symbolic", G_CALLBACK(on_search_clicked), self));
    gtk_box_append(GTK_BOX(left), sidebar_nav_button("Artifacts", "folder-symbolic", G_CALLBACK(on_artifacts_clicked), self));
    gtk_box_append(GTK_BOX(left), sidebar_nav_button("Customize", "preferences-system-symbolic", G_CALLBACK(on_customize_clicked), self));

    /* Sessions Section header */
    GtkWidget *grp_lbl = gtk_label_new("Sessions");
    gtk_widget_add_css_class(grp_lbl, "session-group-header");
    gtk_label_set_xalign(GTK_LABEL(grp_lbl), 0.0f);
    gtk_box_append(GTK_BOX(left), grp_lbl);

    /* Sessions list */
    GtkWidget *sessions_list = gtk_list_box_new();
    gtk_widget_add_css_class(sessions_list, "navigation-sidebar");
    self->sessions = GTK_LIST_BOX(sessions_list);
    g_signal_connect(sessions_list, "row-selected", G_CALLBACK(on_session_selected), self);

    GtkWidget *sessions_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(sessions_scroll), sessions_list);
    gtk_widget_set_vexpand(sessions_scroll, TRUE);
    gtk_box_append(GTK_BOX(left), sessions_scroll);

    /* Account footer button with menu popover */
    GtkWidget *account_btn = gtk_menu_button_new();
    gtk_widget_add_css_class(account_btn, "account-footer-btn");

    GtkWidget *acct_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *avatar = kr_mark_new(24);
    gtk_box_append(GTK_BOX(acct_box), avatar);

    GtkWidget *acct_name = gtk_label_new("Adam · Pro ▾");
    gtk_widget_set_hexpand(acct_name, TRUE);
    gtk_label_set_xalign(GTK_LABEL(acct_name), 0.0f);
    gtk_box_append(GTK_BOX(acct_box), acct_name);

    GtkWidget *gear_img = gtk_image_new_from_icon_name("emblem-system-symbolic");
    gtk_box_append(GTK_BOX(acct_box), gear_img);

    gtk_menu_button_set_child(GTK_MENU_BUTTON(account_btn), acct_box);
    gtk_menu_button_set_popover(GTK_MENU_BUTTON(account_btn), build_account_popover(self));
    gtk_box_append(GTK_BOX(left), account_btn);

    gtk_box_append(GTK_BOX(root), left);
    gtk_box_append(GTK_BOX(root), gtk_separator_new(GTK_ORIENTATION_VERTICAL));

    /* Center column: active session header, inline gates, transcript, and rounded floating composer */
    GtkWidget *center = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_hexpand(center, TRUE);
    gtk_widget_set_vexpand(center, TRUE);

    /* Center Header Bar */
    GtkWidget *top_bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_widget_set_margin_top(top_bar, 10);
    gtk_widget_set_margin_bottom(top_bar, 8);
    gtk_widget_set_margin_start(top_bar, 16);
    gtk_widget_set_margin_end(top_bar, 16);

    GtkWidget *proj_btn = gtk_button_new_with_label("All projects ▾");
    gtk_widget_add_css_class(proj_btn, "flat");
    gtk_widget_add_css_class(proj_btn, "title-4");
    self->project_selector_btn = proj_btn;
    gtk_box_append(GTK_BOX(top_bar), proj_btn);

    GtkWidget *heading = gtk_label_new("");
    self->session_heading = GTK_LABEL(heading);
    GtkWidget *subtitle = gtk_label_new("");
    self->session_subtitle = GTK_LABEL(subtitle);

    GtkWidget *top_spacer = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_hexpand(top_spacer, TRUE);
    gtk_box_append(GTK_BOX(top_bar), top_spacer);

    /* Inspector toggle button */
    GtkWidget *toggle_btn = gtk_button_new_from_icon_name("view-paged-symbolic");
    gtk_widget_add_css_class(toggle_btn, "flat");
    kr_a11y_name(toggle_btn, "Toggle inspector pane");
    g_signal_connect(toggle_btn, "clicked", G_CALLBACK(on_inspector_toggle_clicked), self);
    self->inspector_toggle_btn = toggle_btn;
    gtk_box_append(GTK_BOX(top_bar), toggle_btn);

    gtk_box_append(GTK_BOX(center), top_bar);
    gtk_box_append(GTK_BOX(center), gtk_separator_new(GTK_ORIENTATION_HORIZONTAL));

    /* Pinned open-gate approval cards for the selected session */
    GtkWidget *gate_section = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_set_margin_start(gate_section, 24);
    gtk_widget_set_margin_end(gate_section, 24);
    gtk_widget_set_margin_top(gate_section, 8);

    GtkWidget *gate_cards = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(gate_cards), GTK_SELECTION_NONE);
    gtk_widget_add_css_class(gate_cards, "boxed-list");
    self->gate_cards = GTK_LIST_BOX(gate_cards);
    gtk_box_append(GTK_BOX(gate_section), gate_cards);
    gtk_widget_set_visible(gate_section, FALSE);
    self->gate_section = gate_section;
    gtk_box_append(GTK_BOX(center), gate_section);

    /* Scrolling conversation transcript */
    GtkWidget *transcript = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    self->transcript = GTK_BOX(transcript);
    clear_box(self->transcript);
    gtk_box_append(
        self->transcript,
        build_bubble_card(
            self, "VIBEY", "success",
            "Welcome to vibey krypton chat. Pick a project on the left or type `/` for commands "
            "(`/projects`, `/status`, `/gates`, `/new <name> <what to build>`, `/help`)."));

    GtkWidget *clamp = adw_clamp_new();
    adw_clamp_set_maximum_size(ADW_CLAMP(clamp), 880);
    adw_clamp_set_child(ADW_CLAMP(clamp), transcript);

    GtkWidget *transcript_scroll = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(transcript_scroll), clamp);
    gtk_widget_set_vexpand(transcript_scroll, TRUE);
    self->transcript_scroll = GTK_SCROLLED_WINDOW(transcript_scroll);
    gtk_box_append(GTK_BOX(center), transcript_scroll);

    /* Rounded floating bottom composer card */
    GtkWidget *comp_card = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(comp_card, "floating-composer-card");

    /* + attach menu button */
    GtkWidget *attach_btn = gtk_menu_button_new();
    gtk_widget_add_css_class(attach_btn, "composer-attach-btn");
    gtk_menu_button_set_icon_name(GTK_MENU_BUTTON(attach_btn), "list-add-symbolic");
    kr_a11y_name(attach_btn, "Add files or commands");
    gtk_menu_button_set_popover(GTK_MENU_BUTTON(attach_btn), build_attach_popover(self));
    self->attach_menu_button = attach_btn;
    gtk_box_append(GTK_BOX(comp_card), attach_btn);

    /* Text entry */
    GtkWidget *composer = gtk_entry_new();
    gtk_widget_add_css_class(composer, "composer-input");
    gtk_entry_set_placeholder_text(GTK_ENTRY(composer), "+ Type / for commands");
    gtk_widget_set_hexpand(composer, TRUE);
    kr_a11y_name(composer, "Chat message or slash command");
    self->composer = GTK_ENTRY(composer);
    g_signal_connect(composer, "changed", G_CALLBACK(on_composer_changed), self);
    g_signal_connect(composer, "activate", G_CALLBACK(on_composer_activate), self);
    gtk_box_append(GTK_BOX(comp_card), composer);

    /* Dictation microphone button */
    GtkWidget *mic_btn = gtk_button_new_from_icon_name("audio-input-microphone-symbolic");
    gtk_widget_add_css_class(mic_btn, "composer-attach-btn");
    kr_a11y_name(mic_btn, "Voice dictation");
    self->dictate_button = mic_btn;
    gtk_box_append(GTK_BOX(comp_card), mic_btn);

    /* Popover for slash completion */
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

    /* Send button */
    GtkWidget *send_btn = gtk_button_new_from_icon_name("document-send-symbolic");
    gtk_widget_add_css_class(send_btn, "suggested-action");
    kr_a11y_name(send_btn, "Send chat message");
    g_signal_connect(send_btn, "clicked", G_CALLBACK(on_send_clicked), self);
    self->send_button = send_btn;
    gtk_box_append(GTK_BOX(comp_card), send_btn);

    gtk_box_append(GTK_BOX(center), comp_card);

    /* Sub-composer status bar (Model / Effort pill + Tier Auto) */
    GtkWidget *sub_bar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_add_css_class(sub_bar, "composer-status-bar");

    GtkWidget *sub_spacer = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_hexpand(sub_spacer, TRUE);
    gtk_box_append(GTK_BOX(sub_bar), sub_spacer);

    GtkWidget *model_chip = gtk_button_new_with_label("Sonnet 5.5 Medium");
    gtk_widget_add_css_class(model_chip, "model-effort-chip");
    g_signal_connect(model_chip, "clicked", G_CALLBACK(on_customize_clicked), self);
    self->model_chip_button = model_chip;
    gtk_box_append(GTK_BOX(sub_bar), model_chip);

    GtkWidget *tier_lbl = gtk_label_new("Auto");
    gtk_widget_add_css_class(tier_lbl, "dim-label");
    gtk_box_append(GTK_BOX(sub_bar), tier_lbl);

    GtkWidget *dot = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_add_css_class(dot, "status-dot-green");
    gtk_widget_set_valign(dot, GTK_ALIGN_CENTER);
    gtk_box_append(GTK_BOX(sub_bar), dot);

    gtk_box_append(GTK_BOX(center), sub_bar);

    gtk_box_append(GTK_BOX(root), center);
    gtk_box_append(GTK_BOX(root), gtk_separator_new(GTK_ORIENTATION_VERTICAL));

    /* Right column: Inspector Sidebar */
    self->inspector = kr_inspector_new(app);
    gtk_box_append(GTK_BOX(root), self->inspector);

    render_sessions_and_gates(self);
    return root;
}
