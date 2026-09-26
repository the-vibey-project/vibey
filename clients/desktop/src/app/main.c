/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* Krypton desktop: the application. It owns the core's state, reaches the hub through the
 * core's client, and hands the window its views. Every hub answer is parsed by the core
 * (kr-model.h); a refusal or silence is said in the window's banner, never swallowed. */
#include "kr-answer.h"
#include "kr-app.h"
#include "kr-model.h"
#include "kr-window.h"

/* How often the views are refreshed while the window is open. */
#define REFRESH_SECONDS 5

/* ---- talking to the hub -------------------------------------------------------------- */

typedef enum {
    WANT_PROJECTS,
    WANT_GATES,
    WANT_LANES,
    WANT_LOOPS,
    WANT_DOCTOR,
    WANT_BUDGET,
    WANT_ANSWER,
} Want;

typedef struct {
    KrApp *app;
    Want want;
    char *gate_prompt; /* WANT_ANSWER: what was answered, for the toast */
} Pending;

static void
pending_free(Pending *pending)
{
    g_free(pending->gate_prompt);
    g_free(pending);
}

static void
announce_gates(KrApp *app, GPtrArray *fresh)
{
    if (!app->settings->notifications)
        return;
    for (guint i = 0; i < fresh->len; i++) {
        const KrGate *gate = g_ptr_array_index(fresh, i);
        g_autoptr(GNotification) notification = g_notification_new("A gate needs you");
        g_autofree char *body =
            g_strdup_printf("%s: %s", gate->project_name != NULL ? gate->project_name : "krypton",
                            gate->prompt != NULL ? gate->prompt : gate->kind);
        g_notification_set_body(notification, body);
        g_notification_set_priority(notification, G_NOTIFICATION_PRIORITY_HIGH);
        g_notification_set_default_action(notification, "app.show-gates");
        g_notification_add_button(notification, "Answer", "app.show-gates");
        g_autofree char *id = g_strdup_printf("gate-%s", gate->gate_id);
        g_application_send_notification(G_APPLICATION(app->application), id, notification);
    }
}

static void
on_answered(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Pending *pending = data;
    KrApp *app = pending->app;
    guint status = 0;
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) body = kr_hub_client_call_finish(app->client, result, &status, &error);
    if (g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED)) {
        pending_free(pending);
        return;
    }
    if (body != NULL) {
        kr_app_toast(app, "Answered. krypton carries on.");
        kr_app_refresh(app);
    } else {
        kr_app_toast(app, status != 0 ? kr_hub_status_text(status) : error->message);
    }
    pending_free(pending);
}

static void
on_answer(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Pending *pending = data;
    KrApp *app = pending->app;
    guint status = 0;
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) body = kr_hub_client_call_finish(app->client, result, &status, &error);
    if (g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED)) {
        pending_free(pending);
        return;
    }
    if (body == NULL) {
        if (status == 0)
            kr_state_set_connection(app->state, KR_CONNECTION_OFFLINE,
                                    "No hub answers. Start one with: vibey serve");
        else
            kr_state_set_connection(app->state, KR_CONNECTION_REFUSED, kr_hub_status_text(status));
        pending_free(pending);
        return;
    }
    kr_state_set_connection(app->state, KR_CONNECTION_ONLINE, NULL);

    gsize size = 0;
    const char *text = g_bytes_get_data(body, &size);
    g_autoptr(GError) parse_error = NULL;
    switch (pending->want) {
    case WANT_PROJECTS: {
        GPtrArray *projects = kr_projects_parse(text, (gssize) size, &parse_error);
        if (projects != NULL)
            kr_state_set_projects(app->state, projects);
        break;
    }
    case WANT_GATES: {
        GPtrArray *gates = kr_gates_parse(text, (gssize) size, &parse_error);
        if (gates != NULL) {
            g_autoptr(GPtrArray) fresh = kr_state_set_gates(app->state, gates);
            announce_gates(app, fresh);
        }
        break;
    }
    case WANT_LANES: {
        GPtrArray *lanes = kr_lanes_parse(text, (gssize) size, &parse_error);
        if (lanes != NULL)
            kr_state_set_lanes(app->state, lanes);
        break;
    }
    case WANT_LOOPS: {
        KrLoops *loops = kr_loops_parse(text, (gssize) size, &parse_error);
        if (loops != NULL)
            kr_state_set_loops(app->state, loops);
        break;
    }
    case WANT_DOCTOR: {
        KrDoctor *doctor = kr_doctor_parse(text, (gssize) size, &parse_error);
        if (doctor != NULL)
            kr_state_set_doctor(app->state, doctor);
        break;
    }
    case WANT_BUDGET: {
        KrBudget *budget = kr_budget_parse(text, (gssize) size, &parse_error);
        if (budget != NULL)
            kr_state_set_budget(app->state, budget);
        break;
    }
    case WANT_ANSWER:
        break;
    }
    if (parse_error != NULL) {
        g_autofree char *said = g_strdup_printf("The hub sent something Krypton cannot read: %s",
                                                parse_error->message);
        kr_state_set_connection(app->state, KR_CONNECTION_REFUSED, said);
    }
    pending_free(pending);
}

static void
ask(KrApp *app, KrHubRoute route, const char *project_id, Want want)
{
    Pending *pending = g_new0(Pending, 1);
    pending->app = app;
    pending->want = want;
    kr_hub_client_call_async(app->client, route, project_id, NULL, NULL, app->cancel, on_answer,
                             pending);
}

void
kr_app_refresh(KrApp *app)
{
    ask(app, KR_HUB_ROUTE_PROJECTS, NULL, WANT_PROJECTS);
    ask(app, KR_HUB_ROUTE_GATES, NULL, WANT_GATES);
    ask(app, KR_HUB_ROUTE_LANES, NULL, WANT_LANES);
    ask(app, KR_HUB_ROUTE_LOOPS, NULL, WANT_LOOPS);
    ask(app, KR_HUB_ROUTE_DOCTOR, NULL, WANT_DOCTOR);
    const char *selected = kr_state_selected_project(app->state);
    if (selected != NULL)
        kr_app_refresh_budget(app, selected);
}

void
kr_app_refresh_budget(KrApp *app, const char *project_id)
{
    if (project_id != NULL)
        ask(app, KR_HUB_ROUTE_PROJECT_BUDGET, project_id, WANT_BUDGET);
}

void
kr_app_answer(KrApp *app, const KrGate *gate, const char *value)
{
    g_autoptr(GError) error = NULL;
    g_autofree char *answer = kr_answer_build(gate->kind, value, &error);
    g_autofree char *request_id = kr_answer_request_id();
    g_autofree char *body = answer != NULL ? kr_answer_body(answer, request_id, &error) : NULL;
    if (body == NULL) {
        kr_app_toast(app, error->message);
        return;
    }
    Pending *pending = g_new0(Pending, 1);
    pending->app = app;
    pending->want = WANT_ANSWER;
    pending->gate_prompt = g_strdup(gate->prompt);
    kr_hub_client_call_async(app->client, KR_HUB_ROUTE_GATE_ANSWER, NULL, gate->gate_id, body,
                             app->cancel, on_answered, pending);
}

void
kr_app_toast(KrApp *app, const char *text)
{
    if (app->window != NULL)
        kr_window_toast(app->window, text);
}

/* ---- where the hub is ---------------------------------------------------------------- */

static void
connect_client(KrApp *app)
{
    g_clear_pointer(&app->client, kr_hub_client_free);
    /* This computer's hub is reached with its host token; a hub elsewhere needs pairing,
     * which lands with the hub's pairing change (ADR-0068). */
    g_autofree char *token = NULL;
    const char *problem = NULL;
    if (app->settings->hub_host == NULL) {
        g_autofree char *path = kr_hub_token_path(g_getenv("VIBEY_HUB_STATE_DIR"));
        g_autoptr(GError) error = NULL;
        token = kr_hub_read_token(path, &error);
        if (token == NULL)
            problem = "No hub token on this computer yet. Start the hub with: vibey serve";
    }
    g_autoptr(KrHubEndpoint) endpoint =
        kr_hub_endpoint_new("http", app->settings->hub_host, app->settings->hub_port, token);
    app->client = kr_hub_client_new(endpoint, 0);
    kr_state_set_connection(app->state,
                            problem != NULL ? KR_CONNECTION_OFFLINE : KR_CONNECTION_UNKNOWN,
                            problem);
}

void
kr_app_use_hub(KrApp *app, const char *host, guint16 port)
{
    g_free(app->settings->hub_host);
    app->settings->hub_host = g_strdup(host);
    app->settings->hub_port = port;
    kr_app_save_settings(app);
    connect_client(app);
    kr_app_refresh(app);
    kr_app_toast(app, host != NULL ? "Using the hub you chose." : "Using this computer's hub.");
}

void
kr_app_save_settings(KrApp *app)
{
    g_autoptr(GError) error = NULL;
    if (!kr_settings_save(app->settings, app->settings_path, &error))
        kr_app_toast(app, error->message);
}

void
kr_app_apply_theme(KrApp *app)
{
    static const AdwColorScheme schemes[] = {
        [VIBEY_THEME_MODE_SYSTEM] = ADW_COLOR_SCHEME_DEFAULT,
        [VIBEY_THEME_MODE_LIGHT] = ADW_COLOR_SCHEME_FORCE_LIGHT,
        [VIBEY_THEME_MODE_DARK] = ADW_COLOR_SCHEME_FORCE_DARK,
    };
    adw_style_manager_set_color_scheme(adw_style_manager_get_default(),
                                       schemes[app->settings->theme]);
}

/* ---- discovery ----------------------------------------------------------------------- */

static void
on_hub_seen(const KrHubService *service, gpointer data)
{
    (void) service;
    KrApp *app = data;
    if (app->window != NULL)
        kr_window_devices_changed(app->window);
}

static void
on_hub_gone(const char *name, gpointer data)
{
    (void) name;
    on_hub_seen(NULL, data);
}

static void
start_discovery(KrApp *app)
{
    app->discovery = kr_discovery_new(NULL, on_hub_seen, on_hub_gone, app);
    if (app->discovery == NULL) {
        app->discovery_problem = g_strdup("This build has no network discovery; pair by code.");
        return;
    }
    g_autoptr(GError) error = NULL;
    if (!kr_discovery_start(app->discovery, &error)) {
        app->discovery_problem = g_strdup(error->message);
        g_clear_pointer(&app->discovery, kr_discovery_free);
    }
}

/* ---- the application ----------------------------------------------------------------- */

static gboolean
on_refresh_tick(gpointer data)
{
    kr_app_refresh(data);
    return G_SOURCE_CONTINUE;
}

static void
action_refresh(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    kr_app_refresh(data);
}

static void
show_page(KrApp *app, const char *name)
{
    g_application_activate(G_APPLICATION(app->application));
    if (app->window != NULL)
        kr_window_show_page(app->window, name);
}

static void
action_show_gates(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    show_page(data, "gates");
}

static void
action_settings(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    show_page(data, "settings");
}

static void
action_quit(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    KrApp *app = data;
    g_application_quit(G_APPLICATION(app->application));
}

static void
on_startup(GApplication *application, gpointer data)
{
    (void) application;
    KrApp *app = data;
    const GActionEntry actions[] = {
        {.name = "refresh", .activate = action_refresh},
        {.name = "show-gates", .activate = action_show_gates},
        {.name = "settings", .activate = action_settings},
        {.name = "quit", .activate = action_quit},
    };
    g_action_map_add_action_entries(G_ACTION_MAP(app->application), actions,
                                    G_N_ELEMENTS(actions), app);
    GtkApplication *gtk = GTK_APPLICATION(app->application);
    gtk_application_set_accels_for_action(gtk, "app.refresh", (const char *const[]){"<Control>r", "F5", NULL});
    gtk_application_set_accels_for_action(gtk, "app.show-gates", (const char *const[]){"<Control>g", NULL});
    gtk_application_set_accels_for_action(gtk, "app.settings", (const char *const[]){"<Control>comma", NULL});
    gtk_application_set_accels_for_action(gtk, "app.quit", (const char *const[]){"<Control>q", NULL});

    kr_app_apply_theme(app);
    connect_client(app);
    start_discovery(app);
    app->refresh_source = g_timeout_add_seconds(REFRESH_SECONDS, on_refresh_tick, app);
}

static void
on_activate(GApplication *application, gpointer data)
{
    (void) application;
    KrApp *app = data;
    if (app->window == NULL) {
        kr_window_new(app);
        kr_app_refresh(app);
    }
    gtk_window_present(GTK_WINDOW(app->window));
}

static void
on_shutdown(GApplication *application, gpointer data)
{
    (void) application;
    KrApp *app = data;
    g_cancellable_cancel(app->cancel);
    g_clear_handle_id(&app->refresh_source, g_source_remove);
}

int
main(int argc, char **argv)
{
    KrApp app = {0};
    app.channel = KRYPTON_CHANNEL;
    app.state = kr_state_new();
    app.settings_path = kr_settings_path(app.channel, NULL);
    app.settings = kr_settings_load(app.settings_path);
    app.cancel = g_cancellable_new();

    g_set_application_name(kr_channel_display_name(app.channel));
    app.application = adw_application_new(kr_channel_app_id(app.channel), G_APPLICATION_DEFAULT_FLAGS);
    /* Both channels read the one stylesheet pair, generated from the design tokens. */
    g_application_set_resource_base_path(G_APPLICATION(app.application),
                                         "/io/github/the_vibey_project/Krypton");
    g_signal_connect(app.application, "startup", G_CALLBACK(on_startup), &app);
    g_signal_connect(app.application, "activate", G_CALLBACK(on_activate), &app);
    g_signal_connect(app.application, "shutdown", G_CALLBACK(on_shutdown), &app);
    int status = g_application_run(G_APPLICATION(app.application), argc, argv);

    g_object_unref(app.application);
    kr_discovery_free(app.discovery);
    kr_hub_client_free(app.client);
    kr_state_free(app.state);
    kr_settings_free(app.settings);
    g_free(app.settings_path);
    g_free(app.discovery_problem);
    g_object_unref(app.cancel);
    return status;
}
