/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* krypton desktop: the application. It owns the core's state, reaches the hub through the
 * core's client, and hands the window its views. Every hub answer is parsed by the core
 * (kr-model.h); a refusal or silence is said in the window's banner, never swallowed. */
#include "kr-answer.h"
#include "kr-app.h"
#include "kr-commands.h"
#include "kr-lifecycle.h"
#include "kr-model.h"
#include "kr-pairing-client.h"
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
        if (status == 0) {
            g_autofree char *said = kr_hub_engine_offline_text(
                app->settings->hub_host, app->settings->hub_port != 0 ? app->settings->hub_port : KR_HUB_DEFAULT_PORT,
                app->settings->hub_autostart);
            kr_state_set_connection(app->state, KR_CONNECTION_OFFLINE, said);
        } else
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
        g_autofree char *said = g_strdup_printf("The hub sent something krypton cannot read: %s",
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
    /* A hub elsewhere that this device has not paired with would refuse every request: the
     * banner already says to pair, and nothing is sent until it has. */
    if (app->awaiting_pairing)
        return;
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
    if (project_id != NULL && !app->awaiting_pairing)
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

/* ---- starting, pausing and unwinding a project (ADR-0091) ---------------------------- */

typedef enum {
    LIFE_START,
    LIFE_WORK,
    LIFE_PREVIEW,
    LIFE_UNWIND,
} LifeKind;

typedef struct {
    KrApp *app;
    LifeKind kind;
    char *project_id;
    char *name;
    char *fallback; /* what to say when the hub answers without a message of its own */
} Life;

static void
life_free(Life *life)
{
    g_free(life->project_id);
    g_free(life->name);
    g_free(life->fallback);
    g_free(life);
}

static gboolean
life_blocked(KrApp *app)
{
    if (!app->awaiting_pairing)
        return FALSE;
    kr_app_toast(app, "Pair this computer with the hub first (Devices), then try again.");
    return TRUE;
}

static void
on_lifecycle(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    Life *life = data;
    KrApp *app = life->app;
    guint status = 0;
    g_autofree char *detail = NULL;
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) body =
        kr_hub_client_call_finish_full(app->client, result, &status, &detail, &error);
    if (g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED)) {
        life_free(life);
        return;
    }
    if (body == NULL) {
        /* The hub's own words first: they say what to do ("a project is already running"). */
        kr_app_toast(app, detail != NULL      ? detail
                          : status != 0       ? kr_hub_status_text(status)
                                              : error->message);
        life_free(life);
        return;
    }
    gsize size = 0;
    const char *text = g_bytes_get_data(body, &size);
    g_autofree char *json = g_strndup(text, size);
    g_autoptr(GError) parse_error = NULL;
    switch (life->kind) {
    case LIFE_START: {
        g_autoptr(KrCreated) created = kr_lifecycle_parse_created(json, &parse_error);
        g_autofree char *said =
            created != NULL
                ? g_strdup_printf("Started \"%s\". krypton is designing it now (%s).",
                                  created->name, created->outcome != NULL ? created->outcome : "queued")
                : g_strdup(parse_error->message);
        kr_app_toast(app, said);
        if (app->window != NULL)
            kr_window_show_page(app->window, "projects");
        break;
    }
    case LIFE_WORK: {
        g_autofree char *said = kr_lifecycle_message(json, life->fallback);
        kr_app_toast(app, said);
        break;
    }
    case LIFE_PREVIEW: {
        g_autoptr(KrAbandonReport) report = kr_lifecycle_parse_report(json, &parse_error);
        if (report == NULL) {
            kr_app_toast(app, parse_error->message);
        } else if (report->already_abandoned) {
            g_autofree char *said = kr_lifecycle_confirm_text(report);
            kr_app_toast(app, said);
        } else if (app->window != NULL) {
            g_autofree char *said = kr_lifecycle_confirm_text(report);
            kr_window_confirm_unwind(app->window, life->project_id, life->name, said);
        }
        break;
    }
    case LIFE_UNWIND: {
        g_autoptr(KrAbandonReport) report = kr_lifecycle_parse_report(json, &parse_error);
        g_autofree char *said =
            report != NULL
                ? g_strdup_printf("Unwound \"%s\": %u job(s) cancelled, %u gate(s) withdrawn. "
                                  "The work on disk stays.",
                                  life->name, report->cancelled_jobs, report->withdrawn_gates)
                : g_strdup(parse_error->message);
        kr_app_toast(app, said);
        break;
    }
    }
    kr_app_refresh(app);
    life_free(life);
}

static void
life_call(KrApp *app, LifeKind kind, KrHubRoute route, const char *project_id, const char *name,
          const char *fallback, const char *body)
{
    Life *life = g_new0(Life, 1);
    life->app = app;
    life->kind = kind;
    life->project_id = g_strdup(project_id);
    life->name = g_strdup(name != NULL ? name : "that project");
    life->fallback = g_strdup(fallback);
    kr_hub_client_call_async(app->client, route, project_id, NULL, body, app->cancel, on_lifecycle,
                             life);
}

void
kr_app_start_project(KrApp *app, const char *name, const char *intake)
{
    if (life_blocked(app))
        return;
    g_autoptr(GError) error = NULL;
    g_autofree char *body = kr_lifecycle_start_body(name, intake, &error);
    if (body == NULL) {
        kr_app_toast(app, error->message);
        return;
    }
    kr_app_toast(app, "Starting…");
    life_call(app, LIFE_START, KR_HUB_ROUTE_PROJECT_CREATE, NULL, name, NULL, body);
}

void
kr_app_project_work(KrApp *app, const char *project_id, const char *name, gboolean start)
{
    if (life_blocked(app))
        return;
    life_call(app, LIFE_WORK,
              start ? KR_HUB_ROUTE_PROJECT_START_WORK : KR_HUB_ROUTE_PROJECT_PAUSE_WORK,
              project_id, name, start ? "Work started." : "Work paused.", NULL);
}

void
kr_app_unwind_preview(KrApp *app, const char *project_id, const char *name)
{
    if (life_blocked(app))
        return;
    g_autoptr(GError) error = NULL;
    g_autofree char *body = kr_lifecycle_abandon_body(KR_UNWIND_REASON, TRUE, &error);
    if (body == NULL) {
        kr_app_toast(app, error->message);
        return;
    }
    life_call(app, LIFE_PREVIEW, KR_HUB_ROUTE_PROJECT_ABANDON, project_id, name, NULL, body);
}

void
kr_app_unwind(KrApp *app, const char *project_id, const char *name, const char *reason)
{
    if (life_blocked(app))
        return;
    g_autoptr(GError) error = NULL;
    g_autofree char *body = kr_lifecycle_abandon_body(reason, FALSE, &error);
    if (body == NULL) {
        kr_app_toast(app, error->message);
        return;
    }
    life_call(app, LIFE_UNWIND, KR_HUB_ROUTE_PROJECT_ABANDON, project_id, name, NULL, body);
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
    g_clear_pointer(&app->paired, kr_device_credential_free);
    app->awaiting_pairing = FALSE;
    const char *host = app->settings->hub_host;
    guint16 port = app->settings->hub_port;
    g_autoptr(KrHubEndpoint) endpoint = NULL;
    g_autofree char *problem = NULL;
    if (host == NULL) {
        /* This computer's hub is reached with its host token, read where the hub keeps it. */
        g_autofree char *path = kr_hub_token_path(g_getenv("VIBEY_HUB_STATE_DIR"));
        g_autoptr(GError) error = NULL;
        g_autofree char *token = kr_hub_read_token(path, &error);
        if (token == NULL)
            problem = kr_hub_engine_no_token_text(app->settings->hub_autostart);
        endpoint = kr_hub_endpoint_new("http", NULL, port, token);
    } else {
        /* A hub elsewhere is reached as the device paired with it, or not at all. */
        g_autoptr(GError) error = NULL;
        g_autoptr(KrDeviceCredential) credential =
            kr_device_credential_load(app->credential_path, &error);
        if (credential != NULL && kr_device_credential_matches(credential, host, port)) {
            endpoint = kr_device_credential_endpoint(credential);
            app->paired = g_steal_pointer(&credential);
        } else {
            app->awaiting_pairing = TRUE;
            problem = error != NULL && !g_error_matches(error, G_FILE_ERROR, G_FILE_ERROR_NOENT)
                          ? g_strdup(error->message)
                          : g_strdup("This computer is not paired with that hub yet. Type the "
                                     "6-digit code its host shows (vibey hub pair) on the "
                                     "Devices page.");
            endpoint = kr_hub_endpoint_new("https", host, port, NULL);
        }
    }
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

const char *
kr_app_advertised_fingerprint(KrApp *app, const char *host, guint16 port)
{
    if (app->discovery == NULL || host == NULL)
        return NULL;
    guint16 wanted = port != 0 ? port : KR_HUB_DEFAULT_PORT;
    g_autoptr(GPtrArray) services = kr_discovery_services(app->discovery);
    for (guint i = 0; i < services->len; i++) {
        const KrHubService *service = g_ptr_array_index(services, i);
        if (g_ascii_strcasecmp(service->host, host) == 0 && service->port == wanted)
            return service->fingerprint;
    }
    return NULL;
}

static void
on_paired(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    KrApp *app = data;
    g_autoptr(GError) error = NULL;
    g_autoptr(KrDeviceCredential) credential = kr_pairing_claim_finish(result, &error);
    if (credential == NULL) {
        if (!g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED))
            kr_app_toast(app, error->message);
        return;
    }
    /* The key is kept; from here the app speaks as this device, to that hub. */
    g_free(app->settings->hub_host);
    app->settings->hub_host = g_strdup(credential->host);
    app->settings->hub_port = credential->port;
    kr_app_save_settings(app);
    connect_client(app);
    kr_app_refresh(app);
    g_autofree char *said =
        g_strdup_printf("Paired with %s as \"%s\". krypton now signs every request with this "
                        "device's own key.",
                        credential->host, credential->name);
    kr_app_toast(app, said);
}

void
kr_app_pair(KrApp *app, const char *typed)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(KrHubEndpoint) target = NULL;
    g_autofree char *code = NULL;
    g_autofree char *text = g_strstrip(g_strdup(typed != NULL ? typed : ""));
    if (g_str_has_prefix(text, KR_PAIRING_SCHEME ":")) {
        /* The whole address the host shows: where the hub is, its certificate, the code. */
        g_autoptr(KrPairingOffer) offer = kr_pairing_offer_parse(text, &error);
        if (offer != NULL) {
            target = kr_pairing_target(offer->host, offer->port, offer->fingerprint, &error);
            code = g_strdup(offer->code);
        }
    } else {
        code = kr_pairing_code_normalise(text);
        if (code == NULL) {
            kr_app_toast(app, "A pairing code is six digits, or paste the whole vibey-pair:// "
                              "address the host shows.");
            return;
        }
        const char *host = app->settings->hub_host;
        if (host == NULL) {
            kr_app_toast(app, "This computer's hub needs no pairing: krypton uses its token. To "
                              "pair with a hub on another computer, choose it above first.");
            return;
        }
        /* The certificate the chosen hub advertises, shown on the Devices page for a person
         * to compare with the one the host shows; a loopback hub has none and needs none. */
        guint16 port = app->settings->hub_port;
        target = kr_pairing_target(host, port, kr_app_advertised_fingerprint(app, host, port),
                                   &error);
    }
    if (target == NULL) {
        kr_app_toast(app, error->message);
        return;
    }
    g_autofree char *name = kr_pairing_device_name(g_get_host_name());
    kr_app_toast(app, "Pairing…");
    kr_pairing_claim_async(target, code, name, app->credential_path, app->cancel, on_paired, app);
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

/* ---- the hub on this computer (#1186) ------------------------------------------------ */

typedef struct {
    KrApp *app;
    KrHubEngineAction action;
} HubJob;

static const char *
hub_verb(KrHubEngineAction action)
{
    switch (action) {
    case KR_HUB_ENGINE_STATUS:
        return "check";
    case KR_HUB_ENGINE_STOP:
        return "stop";
    case KR_HUB_ENGINE_START:
    case KR_HUB_ENGINE_ENSURE:
    default:
        return "start";
    }
}

static void
on_hub_engine(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    HubJob *job = data;
    KrApp *app = job->app;
    KrHubEngineAction action = job->action;
    g_free(job);
    g_autoptr(GError) error = NULL;
    g_autoptr(KrHubEngineReport) report = kr_hub_engine_run_finish(result, &error);
    if (g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED))
        return; /* krypton is quitting: the hub is left exactly as it is */
    app->hub_busy = FALSE;
    if (report == NULL) {
        g_autofree char *said = g_strdup_printf("krypton could not %s the hub. %s",
                                                hub_verb(action), error->message);
        g_message("%s", said);
        /* A failed autostart is a quiet note in the connection status, never a pop-up on
         * every start; a failed click is answered where the person clicked. */
        if (action == KR_HUB_ENGINE_ENSURE)
            kr_state_set_connection(app->state, KR_CONNECTION_OFFLINE, said);
        else
            kr_app_toast(app, said);
        return;
    }
    /* A hub that came up, or went away, changes whether the token exists and what answers. */
    connect_client(app);
    kr_app_refresh(app);
    if (action != KR_HUB_ENGINE_ENSURE)
        kr_app_toast(app, report->message);
}

static void
hub_run(KrApp *app, KrHubEngineAction action)
{
    if (app->hub_busy) {
        if (action != KR_HUB_ENGINE_ENSURE)
            kr_app_toast(app, "Still working on the hub. Try again in a moment.");
        return;
    }
    app->hub_busy = TRUE;
    HubJob *job = g_new0(HubJob, 1);
    job->app = app;
    job->action = action;
    kr_hub_engine_run_async(app->hub_engine, action, app->cancel, on_hub_engine, job);
}

/* Start and stop act on this computer's hub: with another computer's chosen, they say so. */
static gboolean
hub_is_elsewhere(KrApp *app)
{
    if (app->settings->hub_host == NULL)
        return FALSE;
    g_autofree char *said = g_strdup_printf(
        "krypton is using the hub on %s. Start or stop that one on its own computer (vibey hub "
        "start | stop), or choose This computer on the Devices page.",
        app->settings->hub_host);
    kr_app_toast(app, said);
    return TRUE;
}

void
kr_app_hub_ensure(KrApp *app)
{
    if (app->settings->hub_host == NULL && app->settings->hub_autostart)
        hub_run(app, KR_HUB_ENGINE_ENSURE);
}

void
kr_app_hub_start(KrApp *app)
{
    if (!hub_is_elsewhere(app))
        hub_run(app, KR_HUB_ENGINE_START);
}

void
kr_app_hub_stop(KrApp *app)
{
    if (!hub_is_elsewhere(app))
        hub_run(app, KR_HUB_ENGINE_STOP);
}

void
kr_app_hub_status(KrApp *app)
{
    hub_run(app, KR_HUB_ENGINE_STATUS);
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

/* ---- the tray ------------------------------------------------------------------------ */

static void
on_tray_action(const char *action, gpointer data)
{
    KrApp *app = data;
    g_action_group_activate_action(G_ACTION_GROUP(app->application), action, NULL);
}

static void
update_tray(KrApp *app)
{
    if (app->tray == NULL)
        return;
    KrTrayModel *model = kr_tray_model_new(app->state, kr_channel_display_name(app->channel));
    if (app->tray_shown != NULL && kr_tray_model_equal(app->tray_shown, model)) {
        kr_tray_model_free(model);
        return;
    }
    kr_tray_show(app->tray, model);
    kr_tray_model_free(app->tray_shown);
    app->tray_shown = model;
}

static void
on_tray_state(KrState *state, KrStateSlice slice, gpointer data)
{
    (void) state;
    (void) slice;
    update_tray(data);
}

static void
start_tray(KrApp *app)
{
    app->tray = kr_tray_new(kr_channel_app_id(app->channel),
                            kr_channel_display_name(app->channel), on_tray_action, app);
    update_tray(app);
}

static void
stop_tray(KrApp *app)
{
    kr_tray_free(app->tray);
    app->tray = NULL;
    kr_tray_model_free(app->tray_shown);
    app->tray_shown = NULL;
}

void
kr_app_set_tray(KrApp *app, gboolean on)
{
    app->settings->tray = on;
    kr_app_save_settings(app);
    if (on && app->tray == NULL) {
        start_tray(app);
    } else if (!on && app->tray != NULL) {
        stop_tray(app);
        /* Nothing is left to bring a hidden window back: show it. */
        g_application_activate(G_APPLICATION(app->application));
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
action_start_project(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    KrApp *app = data;
    g_application_activate(G_APPLICATION(app->application));
    if (app->window != NULL)
        kr_window_start_dialog(app->window);
}

static void
action_about(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    KrApp *app = data;
    g_application_activate(G_APPLICATION(app->application));
    if (app->window != NULL)
        kr_window_about(app->window);
}

static void
action_shortcuts(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    KrApp *app = data;
    g_application_activate(G_APPLICATION(app->application));
    if (app->window != NULL)
        kr_window_shortcuts(app->window);
}

static void
action_start_hub(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    kr_app_hub_start(data);
}

static void
action_stop_hub(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    kr_app_hub_stop(data);
}

static void
action_hub_status(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    kr_app_hub_status(data);
}

static void
action_open(GSimpleAction *action, GVariant *parameter, gpointer data)
{
    (void) action;
    (void) parameter;
    KrApp *app = data;
    g_application_activate(G_APPLICATION(app->application));
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
        {.name = "open", .activate = action_open},
        {.name = "refresh", .activate = action_refresh},
        {.name = "show-gates", .activate = action_show_gates},
        {.name = "settings", .activate = action_settings},
        {.name = "start-project", .activate = action_start_project},
        {.name = "start-hub", .activate = action_start_hub},
        {.name = "stop-hub", .activate = action_stop_hub},
        {.name = "hub-status", .activate = action_hub_status},
        {.name = "shortcuts", .activate = action_shortcuts},
        {.name = "about", .activate = action_about},
        {.name = "quit", .activate = action_quit},
    };
    g_action_map_add_action_entries(G_ACTION_MAP(app->application), actions,
                                    G_N_ELEMENTS(actions), app);
    GtkApplication *gtk = GTK_APPLICATION(app->application);
    /* Every action is a command in the one table, and every command has an action: a mismatch
     * is a programming error, found the first time krypton starts. */
    for (gsize i = 0; i < G_N_ELEMENTS(actions); i++)
        g_assert(kr_command_find(actions[i].name) != NULL);
    gsize command_count = 0;
    const KrCommand *commands = kr_commands(&command_count);
    for (gsize i = 0; i < command_count; i++) {
        g_assert(g_action_map_lookup_action(G_ACTION_MAP(app->application), commands[i].action) !=
                 NULL);
        g_autofree char *name = g_strconcat("app.", commands[i].action, NULL);
        gtk_application_set_accels_for_action(gtk, name, commands[i].accelerators);
    }

    kr_app_apply_theme(app);
    connect_client(app);
    app->hub_engine = kr_hub_engine_new(g_getenv("KRYPTON_VIBEY"), NULL);
    kr_app_hub_ensure(app);
    start_discovery(app);
    kr_state_listen(app->state, on_tray_state, app);
    if (app->settings->tray)
        start_tray(app);
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
    app.credential_path = kr_device_credential_path(app.settings_path);
    app.cancel = g_cancellable_new();

    g_set_application_name(kr_channel_display_name(app.channel));
    app.application = adw_application_new(kr_channel_app_id(app.channel), G_APPLICATION_DEFAULT_FLAGS);
    /* Both channels read the one stylesheet pair, generated from the design tokens. */
    g_application_set_resource_base_path(G_APPLICATION(app.application),
                                         "/io/github/the_vibey_project/krypton");
    g_signal_connect(app.application, "startup", G_CALLBACK(on_startup), &app);
    g_signal_connect(app.application, "activate", G_CALLBACK(on_activate), &app);
    g_signal_connect(app.application, "shutdown", G_CALLBACK(on_shutdown), &app);
    int status = g_application_run(G_APPLICATION(app.application), argc, argv);

    g_object_unref(app.application);
    stop_tray(&app);
    kr_discovery_free(app.discovery);
    kr_hub_client_free(app.client);
    kr_hub_engine_free(app.hub_engine);
    kr_device_credential_free(app.paired);
    g_free(app.credential_path);
    kr_state_free(app.state);
    kr_settings_free(app.settings);
    g_free(app.settings_path);
    g_free(app.discovery_problem);
    g_object_unref(app.cancel);
    return status;
}
