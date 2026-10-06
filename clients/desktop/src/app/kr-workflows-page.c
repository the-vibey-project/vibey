/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-workflows-page.h"

#include "kr-workflows-client.h"

/* How a host grants a device the scope, as `vibey hub pair` takes it. */
#define PAIR_WITH_WORKFLOWS "vibey hub pair --scope view --scope " KR_WORKFLOWS_SCOPE

typedef struct {
    KrApp *app;
    AdwEntryRow *command;
    AdwActionRow *scope; /* why this device may not run commands there, when it may not */
    GtkWidget *run;
    GtkWidget *stop;
    AdwActionRow *status;
    GtkWidget *pill;
    AdwActionRow *link_row;
    GtkWidget *link;
    AdwActionRow *exit_row;
    GtkTextBuffer *output;
    GCancellable *cancel; /* the run being followed, or NULL */
    char *url;            /* the GitHub run of the latest run, once GitHub shows it */
} Page;

static Page *
page_of(GtkWidget *widget)
{
    return g_object_get_data(G_OBJECT(widget), "kr-workflows-page");
}

/* A page that goes away stops following its run; the run itself goes on. */
static void
page_free(gpointer data)
{
    Page *self = data;
    if (self->cancel != NULL)
        g_cancellable_cancel(self->cancel);
    g_clear_object(&self->cancel);
    g_free(self->url);
    g_free(self);
}

/* ---- saying where it is ---------------------------------------------------------------- */

static GtkWidget *
row(const char *title, const char *subtitle)
{
    GtkWidget *widget = adw_action_row_new();
    adw_preferences_row_set_use_markup(ADW_PREFERENCES_ROW(widget), FALSE);
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(widget), title);
    if (subtitle != NULL)
        adw_action_row_set_subtitle(ADW_ACTION_ROW(widget), subtitle);
    return widget;
}

static GtkWidget *
boxed_list(void)
{
    GtkWidget *list = gtk_list_box_new();
    gtk_list_box_set_selection_mode(GTK_LIST_BOX(list), GTK_SELECTION_NONE);
    gtk_widget_add_css_class(list, "boxed-list");
    return list;
}

/* The status row: a title, a line beneath it, and a pill in a design-token colour class. */
static void
say(Page *self, const char *title, const char *subtitle, const char *pill, const char *css)
{
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(self->status), title);
    adw_action_row_set_subtitle(self->status, subtitle != NULL ? subtitle : "");
    gtk_label_set_text(GTK_LABEL(self->pill), pill);
    const char *classes[] = {"caption-heading", css, NULL};
    gtk_widget_set_css_classes(self->pill, classes);
    gtk_widget_set_visible(self->pill, TRUE);
}

static void
set_running(Page *self, gboolean running)
{
    gtk_widget_set_sensitive(self->run, !running);
    gtk_widget_set_visible(self->stop, running);
}

static void
show_link(Page *self, const char *url)
{
    gtk_widget_set_visible(GTK_WIDGET(self->link_row), url != NULL);
    if (url == NULL)
        return;
    adw_action_row_set_subtitle(self->link_row, url);
    gtk_link_button_set_uri(GTK_LINK_BUTTON(self->link), url);
    g_free(self->url);
    self->url = g_strdup(url);
}

static void
append(GtkTextBuffer *buffer, const char *heading, const char *text)
{
    GtkTextIter end;
    gtk_text_buffer_get_end_iter(buffer, &end);
    if (gtk_text_buffer_get_char_count(buffer) > 0)
        gtk_text_buffer_insert(buffer, &end, "\n", -1);
    gtk_text_buffer_insert_with_tags_by_name(buffer, &end, heading, -1, "heading", NULL);
    gtk_text_buffer_insert(buffer, &end, "\n", -1);
    gtk_text_buffer_insert(buffer, &end, text, -1);
}

static const char *
state_css(const KrWorkflowRun *run)
{
    switch (run->state) {
    case KR_WORKFLOW_QUEUED:
        return "dim-label";
    case KR_WORKFLOW_RUNNING:
        return "accent";
    case KR_WORKFLOW_DONE:
        return run->has_exit_code && run->exit_code != 0 ? "warning" : "success";
    case KR_WORKFLOW_FAILED:
    default:
        return "error";
    }
}

static void
render(Page *self, const KrWorkflowRun *run)
{
    g_autofree char *summary = kr_workflow_run_summary(run);
    g_autofree char *request = g_strdup_printf("request %s", run->request_id);
    say(self, summary, request, kr_workflow_state_name(run->state), state_css(run));
    show_link(self, run->url);
    gtk_widget_set_visible(GTK_WIDGET(self->exit_row), run->has_exit_code);
    if (run->has_exit_code) {
        g_autofree char *code = g_strdup_printf("%" G_GINT64_FORMAT, run->exit_code);
        adw_action_row_set_subtitle(self->exit_row, code);
    }
    if (!kr_workflow_run_finished(run))
        return;
    gtk_text_buffer_set_text(self->output, "", -1);
    if (run->output != NULL)
        append(self->output, "stdout", run->output);
    if (run->errors != NULL)
        append(self->output, "stderr", run->errors);
    if (run->state == KR_WORKFLOW_FAILED)
        append(self->output, "why the run failed",
               run->detail != NULL ? run->detail : "the run ended without a report");
    if (run->has_exit_code) {
        g_autofree char *code = g_strdup_printf("%" G_GINT64_FORMAT, run->exit_code);
        append(self->output, "exit code", code);
    }
}

/* ---- running it ------------------------------------------------------------------------ */

static void
on_progress(const KrWorkflowRun *run, gpointer data)
{
    render(data, run);
}

static const char *
refusal_title(const GError *error)
{
    if (error->domain != KR_WORKFLOWS_ERROR)
        return "It could not be followed";
    switch (error->code) {
    case KR_WORKFLOWS_ERROR_COMMAND:
        return "Not sent";
    case KR_WORKFLOWS_ERROR_REFUSED:
        return "The hub refused it";
    case KR_WORKFLOWS_ERROR_UNREACHABLE:
        return "No hub answered";
    case KR_WORKFLOWS_ERROR_FINGERPRINT:
        return "That is not the hub krypton paired with";
    case KR_WORKFLOWS_ERROR_RESPONSE:
    default:
        return "The hub's answer could not be read";
    }
}

static void
on_finished(GObject *source, GAsyncResult *result, gpointer data)
{
    (void) source;
    g_autoptr(GError) error = NULL;
    g_autoptr(KrWorkflowRun) run = kr_workflows_run_finish(result, &error);
    /* Stopped, or the page is gone: either way nothing more is said, and `data` may be gone. */
    if (g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED))
        return;
    Page *self = data;
    g_clear_object(&self->cancel);
    set_running(self, FALSE);
    if (run != NULL) {
        render(self, run);
        return;
    }
    if (g_error_matches(error, KR_WORKFLOWS_ERROR, KR_WORKFLOWS_ERROR_TIMEOUT)) {
        say(self, "Still going on GitHub", error->message, "running", "accent");
        return;
    }
    say(self, refusal_title(error), error->message, "refused", "error");
}

static void
run_command(Page *self)
{
    if (self->cancel != NULL)
        return;
    KrApp *app = self->app;
    if (app->awaiting_pairing) {
        say(self, "Not sent",
            "Pair this computer with the hub first, on the Devices page. Its host grants the "
            "scope with: " PAIR_WITH_WORKFLOWS,
            "not sent", "warning");
        return;
    }
    g_autoptr(GError) error = NULL;
    g_auto(GStrv) argv =
        kr_workflows_split(gtk_editable_get_text(GTK_EDITABLE(self->command)), &error);
    if (argv == NULL) {
        say(self, "Not sent", error->message, "not sent", "warning");
        return;
    }
    gtk_text_buffer_set_text(self->output, "", -1);
    gtk_widget_set_visible(GTK_WIDGET(self->link_row), FALSE);
    gtk_widget_set_visible(GTK_WIDGET(self->exit_row), FALSE);
    g_clear_pointer(&self->url, g_free);
    g_autofree char *line = g_strjoinv(" ", argv);
    g_autofree char *sending = g_strdup_printf("vibey -w %s", line);
    say(self, "Sending it to GitHub", sending, "sending", "dim-label");
    self->cancel = g_cancellable_new();
    set_running(self, TRUE);
    kr_workflows_run_async(kr_hub_client_endpoint(app->client), (const char *const *) argv, NULL,
                           on_progress, self, self->cancel, on_finished, self);
}

static void
on_run_clicked(GtkButton *button, gpointer data)
{
    (void) button;
    run_command(data);
}

static void
on_command_activated(AdwEntryRow *entry, gpointer data)
{
    (void) entry;
    run_command(data);
}

static void
on_stop_clicked(GtkButton *button, gpointer data)
{
    (void) button;
    Page *self = data;
    if (self->cancel == NULL)
        return;
    g_cancellable_cancel(self->cancel);
    g_clear_object(&self->cancel);
    set_running(self, FALSE);
    g_autofree char *where =
        self->url != NULL ? g_strdup_printf("It goes on at %s", self->url)
                          : g_strdup("It goes on GitHub; krypton no longer follows it.");
    say(self, "Stopped watching", where, "stopped", "dim-label");
}

/* ---- the page -------------------------------------------------------------------------- */

void
kr_workflows_page_refresh(GtkWidget *page)
{
    Page *self = page_of(page);
    const KrApp *app = self->app;
    const char *title = NULL;
    const char *subtitle = NULL;
    if (app->awaiting_pairing) {
        title = "Pair this computer with the hub first";
        subtitle = "On the Devices page. Its host grants the scope with: " PAIR_WITH_WORKFLOWS;
    } else if (app->paired != NULL &&
               !kr_workflows_scope_held((const char *const *) app->paired->scopes)) {
        title = "This device may not run commands on GitHub";
        subtitle = "Its pairing lacks the " KR_WORKFLOWS_SCOPE " scope. On the hub's computer "
                   "run " PAIR_WITH_WORKFLOWS ", then pair again on the Devices page.";
    }
    gtk_widget_set_visible(GTK_WIDGET(self->scope), title != NULL);
    if (title != NULL) {
        adw_preferences_row_set_title(ADW_PREFERENCES_ROW(self->scope), title);
        adw_action_row_set_subtitle(self->scope, subtitle);
    }
}

static GtkWidget *
output_view(Page *self)
{
    GtkWidget *view = gtk_text_view_new();
    GtkTextView *text = GTK_TEXT_VIEW(view);
    gtk_text_view_set_editable(text, FALSE);
    gtk_text_view_set_cursor_visible(text, FALSE);
    gtk_text_view_set_monospace(text, TRUE);
    gtk_text_view_set_wrap_mode(text, GTK_WRAP_NONE);
    gtk_text_view_set_top_margin(text, 12);
    gtk_text_view_set_bottom_margin(text, 12);
    gtk_text_view_set_left_margin(text, 12);
    gtk_text_view_set_right_margin(text, 12);
    /* The tokens' monospace face (design/dist/gtk: .monospace), on the view's own background. */
    gtk_widget_add_css_class(view, "monospace");
    gtk_accessible_update_property(GTK_ACCESSIBLE(view), GTK_ACCESSIBLE_PROPERTY_LABEL,
                                   "What the command printed", -1);
    self->output = gtk_text_view_get_buffer(text);
    gtk_text_buffer_create_tag(self->output, "heading", "weight", PANGO_WEIGHT_BOLD, NULL);
    gtk_text_buffer_set_text(self->output, "What the command prints appears here once it has run.",
                             -1);

    GtkWidget *scroller = gtk_scrolled_window_new();
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroller), view);
    gtk_scrolled_window_set_min_content_height(GTK_SCROLLED_WINDOW(scroller), 160);
    gtk_widget_set_vexpand(scroller, TRUE);
    gtk_widget_add_css_class(scroller, "card");
    gtk_widget_set_overflow(scroller, GTK_OVERFLOW_HIDDEN);
    return scroller;
}

static GtkWidget *
pill_button(const char *label, const char *css)
{
    GtkWidget *button = gtk_button_new_with_label(label);
    gtk_widget_add_css_class(button, "pill");
    if (css != NULL)
        gtk_widget_add_css_class(button, css);
    return button;
}

GtkWidget *
kr_workflows_page_new(KrApp *app)
{
    Page *self = g_new0(Page, 1);
    self->app = app;

    GtkWidget *intro = gtk_label_new(
        "Runs a vibey command on the repository's GitHub-hosted runners, as vibey -w does, and "
        "shows what it printed. Type it as it would follow vibey -w. This device needs the "
        KR_WORKFLOWS_SCOPE " scope, and the scopes of what the command itself does.");
    gtk_label_set_wrap(GTK_LABEL(intro), TRUE);
    gtk_label_set_xalign(GTK_LABEL(intro), 0.0f);
    gtk_widget_add_css_class(intro, "dim-label");

    /* What to run. */
    GtkWidget *form = boxed_list();
    GtkWidget *command = adw_entry_row_new();
    adw_preferences_row_set_title(ADW_PREFERENCES_ROW(command), "Command, such as: status --json");
    gtk_widget_add_css_class(command, "monospace");
    g_signal_connect(command, "entry-activated", G_CALLBACK(on_command_activated), self);
    self->command = ADW_ENTRY_ROW(command);
    gtk_list_box_append(GTK_LIST_BOX(form), command);
    GtkWidget *scope = row("", NULL);
    adw_action_row_add_prefix(ADW_ACTION_ROW(scope),
                              gtk_image_new_from_icon_name("dialog-warning-symbolic"));
    gtk_widget_set_visible(scope, FALSE);
    self->scope = ADW_ACTION_ROW(scope);
    gtk_list_box_append(GTK_LIST_BOX(form), scope);

    GtkWidget *actions = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_halign(actions, GTK_ALIGN_END);
    self->stop = pill_button("Stop watching", NULL);
    gtk_widget_set_tooltip_text(self->stop, "krypton stops following it; the run goes on");
    gtk_widget_set_visible(self->stop, FALSE);
    g_signal_connect(self->stop, "clicked", G_CALLBACK(on_stop_clicked), self);
    self->run = pill_button("Run on GitHub", "suggested-action");
    g_signal_connect(self->run, "clicked", G_CALLBACK(on_run_clicked), self);
    gtk_box_append(GTK_BOX(actions), self->stop);
    gtk_box_append(GTK_BOX(actions), self->run);

    /* Where it is. */
    GtkWidget *progress = boxed_list();
    GtkWidget *status = row("Not run yet", "Each run is asked after every ten seconds, for up "
                                           "to an hour.");
    self->status = ADW_ACTION_ROW(status);
    self->pill = gtk_label_new(NULL);
    gtk_widget_set_valign(self->pill, GTK_ALIGN_CENTER);
    gtk_widget_set_visible(self->pill, FALSE);
    adw_action_row_add_suffix(self->status, self->pill);
    gtk_list_box_append(GTK_LIST_BOX(progress), status);

    GtkWidget *link_row = row("GitHub run", NULL);
    self->link = gtk_link_button_new_with_label("https://github.com/", "Open");
    gtk_widget_set_valign(self->link, GTK_ALIGN_CENTER);
    adw_action_row_add_suffix(ADW_ACTION_ROW(link_row), self->link);
    gtk_widget_set_visible(link_row, FALSE);
    self->link_row = ADW_ACTION_ROW(link_row);
    gtk_list_box_append(GTK_LIST_BOX(progress), link_row);

    GtkWidget *exit_row = row("Exit code", NULL);
    adw_action_row_set_subtitle_selectable(ADW_ACTION_ROW(exit_row), TRUE);
    gtk_widget_set_visible(exit_row, FALSE);
    self->exit_row = ADW_ACTION_ROW(exit_row);
    gtk_list_box_append(GTK_LIST_BOX(progress), exit_row);

    /* What it printed. */
    GtkWidget *heading = gtk_label_new("Output");
    gtk_widget_add_css_class(heading, "heading");
    gtk_label_set_xalign(GTK_LABEL(heading), 0.0f);

    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 12);
    gtk_box_append(GTK_BOX(box), intro);
    gtk_box_append(GTK_BOX(box), form);
    gtk_box_append(GTK_BOX(box), actions);
    gtk_box_append(GTK_BOX(box), progress);
    gtk_box_append(GTK_BOX(box), heading);
    gtk_box_append(GTK_BOX(box), output_view(self));

    GtkWidget *clamp = adw_clamp_new();
    adw_clamp_set_maximum_size(ADW_CLAMP(clamp), 820);
    adw_clamp_set_child(ADW_CLAMP(clamp), box);
    gtk_widget_set_margin_top(clamp, 18);
    gtk_widget_set_margin_bottom(clamp, 18);
    gtk_widget_set_margin_start(clamp, 12);
    gtk_widget_set_margin_end(clamp, 12);
    gtk_widget_set_vexpand(clamp, TRUE);
    g_object_set_data_full(G_OBJECT(clamp), "kr-workflows-page", self, page_free);
    kr_workflows_page_refresh(clamp);
    return clamp;
}
