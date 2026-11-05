/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-settings-dialog.h"
#include "kr-a11y.h"
#include "kr-format.h"

typedef struct {
    KrApp *app;
    AdwDialog *dialog;
    GtkStack *stack;
    GtkListBox *nav_list;
} SettingsState;

static void
on_theme_selected(AdwComboRow *combo, GParamSpec *pspec, gpointer data)
{
    (void) pspec;
    SettingsState *state = data;
    static const VibeyThemeMode modes[] = {VIBEY_THEME_MODE_SYSTEM, VIBEY_THEME_MODE_LIGHT,
                                           VIBEY_THEME_MODE_DARK};
    guint selected = adw_combo_row_get_selected(combo);
    if (selected >= G_N_ELEMENTS(modes))
        return;
    state->app->settings->theme = modes[selected];
    kr_app_apply_theme(state->app);
    kr_app_save_settings(state->app);
}

static void
on_switch_field(AdwSwitchRow *toggle, GParamSpec *pspec, gpointer data)
{
    (void) pspec;
    SettingsState *state = data;
    gboolean *field = g_object_get_data(G_OBJECT(toggle), "field");
    if (field != NULL) {
        *field = adw_switch_row_get_active(toggle);
        kr_app_save_settings(state->app);
    }
}

static GtkWidget *
build_usage_page(SettingsState *state)
{
    GtkWidget *page = adw_preferences_page_new();

    GtkWidget *banner_group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(banner_group), "Your usage (Sovereign Default)");
    adw_preferences_group_set_description(
        ADW_PREFERENCES_GROUP(banner_group),
        "Local engines (gptossloop / sovereignloop) run with zero fee and unlimited budget. "
        "Paid engines (claudeloop / codexloop) report their spend against project caps.");
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), ADW_PREFERENCES_GROUP(banner_group));

    GtkWidget *session_group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(session_group), "Current session");

    GtkWidget *session_row = adw_action_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(session_row), "Session turns");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(session_row), "Active turns with hub and tools");
    GtkWidget *session_bar = gtk_level_bar_new_for_interval(0.0, 1.0);
    gtk_level_bar_set_value(GTK_LEVEL_BAR(session_bar), 0.12);
    gtk_widget_set_size_request(session_bar, 140, -1);
    gtk_widget_set_valign(session_bar, GTK_ALIGN_CENTER);
    adw_action_row_add_suffix(ADW_ACTION_ROW(session_row), session_bar);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(session_group), session_row);

    GtkWidget *week_row = adw_action_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(week_row), "Cycle capacity");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(week_row), "Resets automatically on next cycle transition");
    GtkWidget *week_bar = gtk_level_bar_new_for_interval(0.0, 1.0);
    gtk_level_bar_set_value(GTK_LEVEL_BAR(week_bar), 0.45);
    gtk_widget_set_size_request(week_bar, 140, -1);
    gtk_widget_set_valign(week_bar, GTK_ALIGN_CENTER);
    adw_action_row_add_suffix(ADW_ACTION_ROW(week_row), week_bar);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(session_group), week_row);
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), ADW_PREFERENCES_GROUP(session_group));

    GtkWidget *credits_group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(credits_group), "Usage credits & limits");
    adw_preferences_group_set_description(
        ADW_PREFERENCES_GROUP(credits_group),
        "Credits ≠ rate limits. Capacity rejection always outranks completion claim (ADR-0005).");

    GtkWidget *credit_row = adw_action_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(credit_row), "Available balance");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(credit_row), "$0.00 spent on sovereign host");
    GtkWidget *pill = gtk_label_new("Sovereign free");
    gtk_widget_add_css_class(pill, "caption-heading");
    gtk_widget_add_css_class(pill, "success");
    gtk_widget_set_valign(pill, GTK_ALIGN_CENTER);
    adw_action_row_add_suffix(ADW_ACTION_ROW(credit_row), pill);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(credits_group), credit_row);

    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), ADW_PREFERENCES_GROUP(credits_group));
    return page;
}

static GtkWidget *
build_appearance_page(SettingsState *state)
{
    GtkWidget *page = adw_preferences_page_new();
    GtkWidget *group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(group), "Look & Feel");

    const char *const modes[] = {"System", "Light", "Dark", NULL};
    GtkWidget *theme = adw_combo_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(theme), "Theme Mode");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(theme), "Follow system dark/light preference or lock it");
    g_autoptr(GtkStringList) choices = gtk_string_list_new(modes);
    adw_combo_row_set_model(ADW_COMBO_ROW(theme), G_LIST_MODEL(choices));
    guint selected = state->app->settings->theme == VIBEY_THEME_MODE_LIGHT  ? 1
                     : state->app->settings->theme == VIBEY_THEME_MODE_DARK ? 2
                                                                            : 0;
    adw_combo_row_set_selected(ADW_COMBO_ROW(theme), selected);
    g_signal_connect(theme, "notify::selected", G_CALLBACK(on_theme_selected), state);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), theme);

    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), ADW_PREFERENCES_GROUP(group));
    return page;
}

static GtkWidget *
build_notifications_page(SettingsState *state)
{
    GtkWidget *page = adw_preferences_page_new();
    GtkWidget *group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(group), "Notifications & Alerts");

    GtkWidget *notif_toggle = adw_switch_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(notif_toggle), "Desktop notifications");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(notif_toggle), "Notify when human gates need your verdict");
    adw_switch_row_set_active(ADW_SWITCH_ROW(notif_toggle), state->app->settings->notifications);
    g_object_set_data(G_OBJECT(notif_toggle), "field", &state->app->settings->notifications);
    g_signal_connect(notif_toggle, "notify::active", G_CALLBACK(on_switch_field), state);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), notif_toggle);

    GtkWidget *sound_toggle = adw_switch_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(sound_toggle), "Auditory feedback");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(sound_toggle), "Play alert sounds on completion and gate requests");
    adw_switch_row_set_active(ADW_SWITCH_ROW(sound_toggle), state->app->settings->sounds);
    g_object_set_data(G_OBJECT(sound_toggle), "field", &state->app->settings->sounds);
    g_signal_connect(sound_toggle, "notify::active", G_CALLBACK(on_switch_field), state);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), sound_toggle);

    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), ADW_PREFERENCES_GROUP(group));
    return page;
}

static GtkWidget *
build_desktop_app_page(SettingsState *state)
{
    GtkWidget *page = adw_preferences_page_new();
    GtkWidget *group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(group), "Local Hub & Integration");

    GtkWidget *autostart = adw_switch_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(autostart), "Start local hub automatically");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(autostart), "Spawns background hub (vibey serve) when app launches");
    adw_switch_row_set_active(ADW_SWITCH_ROW(autostart), state->app->settings->hub_autostart);
    g_object_set_data(G_OBJECT(autostart), "field", &state->app->settings->hub_autostart);
    g_signal_connect(autostart, "notify::active", G_CALLBACK(on_switch_field), state);
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), autostart);

    GtkWidget *hub_actions = adw_action_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(hub_actions), "Host Hub Daemon");
    adw_action_row_set_subtitle(ADW_ACTION_ROW(hub_actions), "One sovereign hub process per user");

    GtkWidget *btn_start = gtk_button_new_with_label("Start");
    gtk_widget_set_valign(btn_start, GTK_ALIGN_CENTER);
    gtk_actionable_set_action_name(GTK_ACTIONABLE(btn_start), "app.start-hub");
    adw_action_row_add_suffix(ADW_ACTION_ROW(hub_actions), btn_start);

    GtkWidget *btn_stop = gtk_button_new_with_label("Stop");
    gtk_widget_set_valign(btn_stop, GTK_ALIGN_CENTER);
    gtk_actionable_set_action_name(GTK_ACTIONABLE(btn_stop), "app.stop-hub");
    adw_action_row_add_suffix(ADW_ACTION_ROW(hub_actions), btn_stop);

    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), hub_actions);

    GtkWidget *ver_row = adw_action_row_new();
    g_autofree char *ver_text = g_strdup_printf("%s %s", kr_channel_display_name(state->app->channel), KRYPTON_VERSION);
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(ver_row), ver_text);
    adw_action_row_set_subtitle(ADW_ACTION_ROW(ver_row), kr_channel_app_id(state->app->channel));
    adw_preferences_group_add(ADW_PREFERENCES_GROUP(group), ver_row);

    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), ADW_PREFERENCES_GROUP(group));
    return page;
}

static GtkWidget *
build_placeholder_page(const char *title, const char *desc)
{
    GtkWidget *page = adw_preferences_page_new();
    GtkWidget *group = adw_preferences_group_new();
    adw_preferences_group_set_title(ADW_PREFERENCES_GROUP(group), title);
    adw_preferences_group_set_description(ADW_PREFERENCES_GROUP(group), desc);
    adw_preferences_page_add(ADW_PREFERENCES_PAGE(page), ADW_PREFERENCES_GROUP(group));
    return page;
}

static void
on_nav_selected(GtkListBox *box, GtkListBoxRow *row, gpointer data)
{
    (void) box;
    SettingsState *state = data;
    if (row == NULL)
        return;
    const char *name = g_object_get_data(G_OBJECT(row), "page-id");
    if (name != NULL)
        gtk_stack_set_visible_child_name(state->stack, name);
}

void
kr_settings_dialog_present(GtkWidget *parent_window, KrApp *app)
{
    SettingsState *state = g_new0(SettingsState, 1);
    state->app = app;

    AdwDialog *dialog = adw_dialog_new();
    adw_dialog_set_title(dialog, "Settings");
    adw_dialog_set_content_width(dialog, 760);
    adw_dialog_set_content_height(dialog, 580);
    state->dialog = dialog;

    GtkWidget *split = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);

    /* Left Nav */
    GtkWidget *left_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_set_size_request(left_box, 190, -1);
    gtk_widget_set_margin_top(left_box, 12);
    gtk_widget_set_margin_bottom(left_box, 12);
    gtk_widget_set_margin_start(left_box, 8);
    gtk_widget_set_margin_end(left_box, 8);

    GtkWidget *nav_list = gtk_list_box_new();
    gtk_widget_add_css_class(nav_list, "navigation-sidebar");
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(nav_list), GTK_SELECTION_SINGLE);
    state->nav_list = GTK_LIST_BOX(nav_list);
    g_signal_connect(nav_list, "row-selected", G_CALLBACK(on_nav_selected), state);

    struct {
        const char *id;
        const char *label;
        const char *icon;
    } items[] = {
        {"usage", "Usage", "wallet-symbolic"},
        {"account", "Account", "avatar-default-symbolic"},
        {"appearance", "Appearance", "applications-graphics-symbolic"},
        {"capabilities", "Capabilities", "utilities-terminal-symbolic"},
        {"notifications", "Notifications", "dialog-information-symbolic"},
        {"privacy", "Privacy", "security-high-symbolic"},
        {"desktop", "Desktop app", "computer-symbolic"},
    };

    for (gsize i = 0; i < G_N_ELEMENTS(items); i++) {
        GtkWidget *row = adw_action_row_new();
        adw_preferences_row_set_title(ADW_PREFERENCES_ROW(row), items[i].label);
        adw_action_row_add_prefix(ADW_ACTION_ROW(row), gtk_image_new_from_icon_name(items[i].icon));
        g_object_set_data_full(G_OBJECT(row), "page-id", g_strdup(items[i].id), g_free);
        gtk_list_box_append(GTK_LIST_BOX(nav_list), row);
    }
    gtk_box_append(GTK_BOX(left_box), nav_list);
    gtk_box_append(GTK_BOX(split), left_box);
    gtk_box_append(GTK_BOX(split), gtk_separator_new(GTK_ORIENTATION_VERTICAL));

    /* Right content stack */
    GtkWidget *stack = gtk_stack_new();
    gtk_stack_set_transition_type(GTK_STACK(stack), GTK_STACK_TRANSITION_TYPE_CROSSFADE);
    gtk_widget_set_hexpand(stack, TRUE);
    gtk_widget_set_vexpand(stack, TRUE);
    state->stack = GTK_STACK(stack);

    gtk_stack_add_named(GTK_STACK(stack), build_usage_page(state), "usage");
    gtk_stack_add_named(GTK_STACK(stack), build_placeholder_page("Account", "Signed in as sovereign operator (host token)."), "account");
    gtk_stack_add_named(GTK_STACK(stack), build_appearance_page(state), "appearance");
    gtk_stack_add_named(GTK_STACK(stack), build_placeholder_page("Capabilities", "Sovereign default runner (gptossloop) and MCP tools."), "capabilities");
    gtk_stack_add_named(GTK_STACK(stack), build_notifications_page(state), "notifications");
    gtk_stack_add_named(GTK_STACK(stack), build_placeholder_page("Privacy", "Zero telemetry egress: domain stays pure and strictly local."), "privacy");
    gtk_stack_add_named(GTK_STACK(stack), build_desktop_app_page(state), "desktop");

    gtk_box_append(GTK_BOX(split), stack);

    GtkWidget *toolbar = adw_toolbar_view_new();
    GtkWidget *hb = adw_header_bar_new();
    adw_toolbar_view_add_top_bar(ADW_TOOLBAR_VIEW(toolbar), hb);
    adw_toolbar_view_set_content(ADW_TOOLBAR_VIEW(toolbar), split);

    adw_dialog_set_child(dialog, toolbar);
    g_object_set_data_full(G_OBJECT(dialog), "settings-state", state, g_free);

    gtk_list_box_select_row(GTK_LIST_BOX(nav_list), gtk_list_box_get_row_at_index(GTK_LIST_BOX(nav_list), 0));
    adw_dialog_present(dialog, parent_window);
}
