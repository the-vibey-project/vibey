/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-inspector.h"
#include "kr-a11y.h"
#include "kr-format.h"

typedef struct {
    KrApp *app;
    GtkLabel *host_label;
    GtkLabel *repo_label;
    GtkLabel *branch_label;
    GtkLevelBar *context_bar;
    GtkLabel *context_pct;
    GtkLabel *changes_pill;
    GtkWidget *remote_switch;
} InspectorWidgets;

static void
on_create_pr_clicked(GtkButton *btn, gpointer data)
{
    (void) btn;
    InspectorWidgets *self = data;
    kr_app_toast(self->app, "PR workflow enqueued through merge train.");
}

GtkWidget *
kr_inspector_new(KrApp *app)
{
    InspectorWidgets *self = g_new0(InspectorWidgets, 1);
    self->app = app;

    GtkWidget *root = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_size_request(root, 280, -1);
    gtk_widget_set_margin_top(root, 12);
    gtk_widget_set_margin_bottom(root, 12);
    gtk_widget_set_margin_start(root, 8);
    gtk_widget_set_margin_end(root, 12);
    g_object_set_data_full(G_OBJECT(root), "kr-inspector", self, g_free);

    /* 1. Environment Card */
    GtkWidget *env_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(env_box, "inspector-card");

    GtkWidget *env_title_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    GtkWidget *env_title = gtk_label_new("Environment");
    gtk_widget_add_css_class(env_title, "inspector-card-title");
    gtk_widget_set_hexpand(env_title, TRUE);
    gtk_label_set_xalign(GTK_LABEL(env_title), 0.0f);
    gtk_box_append(GTK_BOX(env_title_box), env_title);
    gtk_box_append(GTK_BOX(env_box), env_title_box);

    /* Host row */
    GtkWidget *host_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_append(GTK_BOX(host_row), gtk_image_new_from_icon_name("computer-symbolic"));
    GtkWidget *host_lbl = gtk_label_new("This computer");
    gtk_widget_set_hexpand(host_lbl, TRUE);
    gtk_label_set_xalign(GTK_LABEL(host_lbl), 0.0f);
    self->host_label = GTK_LABEL(host_lbl);
    gtk_box_append(GTK_BOX(host_row), host_lbl);
    GtkWidget *save_lbl = gtk_label_new("Save");
    gtk_widget_add_css_class(save_lbl, "dim-label");
    gtk_box_append(GTK_BOX(host_row), save_lbl);
    gtk_box_append(GTK_BOX(env_box), host_row);

    /* Repo row */
    GtkWidget *repo_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_append(GTK_BOX(repo_row), gtk_image_new_from_icon_name("folder-symbolic"));
    GtkWidget *repo_lbl = gtk_label_new("vibey · ~/git");
    gtk_widget_set_hexpand(repo_lbl, TRUE);
    gtk_label_set_xalign(GTK_LABEL(repo_lbl), 0.0f);
    self->repo_label = GTK_LABEL(repo_lbl);
    gtk_box_append(GTK_BOX(repo_row), repo_lbl);
    gtk_box_append(GTK_BOX(env_box), repo_row);

    /* Branch row */
    GtkWidget *branch_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_append(GTK_BOX(branch_row), gtk_image_new_from_icon_name("network-workgroup-symbolic"));
    GtkWidget *branch_lbl = gtk_label_new("develop");
    gtk_widget_set_hexpand(branch_lbl, TRUE);
    gtk_label_set_xalign(GTK_LABEL(branch_lbl), 0.0f);
    self->branch_label = GTK_LABEL(branch_lbl);
    gtk_box_append(GTK_BOX(branch_row), branch_lbl);
    GtkWidget *wt_lbl = gtk_label_new("Worktree");
    gtk_widget_add_css_class(wt_lbl, "dim-label");
    gtk_box_append(GTK_BOX(branch_row), wt_lbl);
    gtk_box_append(GTK_BOX(env_box), branch_row);

    /* Remote Control toggle */
    GtkWidget *rc_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_append(GTK_BOX(rc_row), gtk_image_new_from_icon_name("network-wireless-symbolic"));
    GtkWidget *rc_lbl = gtk_label_new("Remote Control");
    gtk_widget_set_hexpand(rc_lbl, TRUE);
    gtk_label_set_xalign(GTK_LABEL(rc_lbl), 0.0f);
    gtk_box_append(GTK_BOX(rc_row), rc_lbl);
    GtkWidget *rc_switch = gtk_switch_new();
    gtk_widget_set_valign(rc_switch, GTK_ALIGN_CENTER);
    self->remote_switch = rc_switch;
    gtk_box_append(GTK_BOX(rc_row), rc_switch);
    gtk_box_append(GTK_BOX(env_box), rc_row);

    gtk_box_append(GTK_BOX(root), env_box);

    /* 2. Context Card */
    GtkWidget *ctx_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(ctx_box, "inspector-card");

    GtkWidget *ctx_hdr = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    GtkWidget *ctx_title = gtk_label_new("Context ▸");
    gtk_widget_add_css_class(ctx_title, "inspector-card-title");
    gtk_widget_set_hexpand(ctx_title, TRUE);
    gtk_label_set_xalign(GTK_LABEL(ctx_title), 0.0f);
    gtk_box_append(GTK_BOX(ctx_hdr), ctx_title);

    GtkWidget *ctx_val = gtk_label_new("49%");
    gtk_widget_add_css_class(ctx_val, "dim-label");
    self->context_pct = GTK_LABEL(ctx_val);
    gtk_box_append(GTK_BOX(ctx_hdr), ctx_val);
    gtk_box_append(GTK_BOX(ctx_box), ctx_hdr);

    GtkWidget *bar = gtk_level_bar_new_for_interval(0.0, 1.0);
    gtk_level_bar_set_value(GTK_LEVEL_BAR(bar), 0.49);
    self->context_bar = GTK_LEVEL_BAR(bar);
    gtk_box_append(GTK_BOX(ctx_box), bar);
    gtk_box_append(GTK_BOX(root), ctx_box);

    /* 3. Connectors Card */
    GtkWidget *conn_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_widget_add_css_class(conn_box, "inspector-card");

    GtkWidget *conn_title = gtk_label_new("Connectors (MCP)");
    gtk_widget_add_css_class(conn_title, "inspector-card-title");
    gtk_label_set_xalign(GTK_LABEL(conn_title), 0.0f);
    gtk_box_append(GTK_BOX(conn_box), conn_title);

    struct {
        const char *badge;
        const char *name;
        const char *action;
        gboolean alert;
    } conns[] = {
        {"5", "55ip", "Reconnect", TRUE},
        {"A", "Addepar", "Authenticate", FALSE},
        {"A", "Adobe", "Authenticate", FALSE},
    };

    for (gsize i = 0; i < G_N_ELEMENTS(conns); i++) {
        GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
        GtkWidget *b_lbl = gtk_label_new(conns[i].badge);
        gtk_widget_add_css_class(b_lbl, "dim-label");
        gtk_box_append(GTK_BOX(row), b_lbl);

        GtkWidget *n_lbl = gtk_label_new(conns[i].name);
        gtk_widget_set_hexpand(n_lbl, TRUE);
        gtk_label_set_xalign(GTK_LABEL(n_lbl), 0.0f);
        gtk_box_append(GTK_BOX(row), n_lbl);

        GtkWidget *act_lbl = gtk_label_new(conns[i].action);
        gtk_widget_add_css_class(act_lbl, conns[i].alert ? "warning" : "dim-label");
        gtk_box_append(GTK_BOX(row), act_lbl);
        gtk_box_append(GTK_BOX(conn_box), row);
    }

    GtkWidget *show_more = gtk_button_new_with_label("Show more");
    gtk_widget_add_css_class(show_more, "flat");
    gtk_widget_set_halign(show_more, GTK_ALIGN_START);
    gtk_box_append(GTK_BOX(conn_box), show_more);

    gtk_box_append(GTK_BOX(root), conn_box);

    /* 4. Changes Card */
    GtkWidget *chg_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_add_css_class(chg_box, "inspector-card");

    GtkWidget *chg_title = gtk_label_new("Changes");
    gtk_widget_add_css_class(chg_title, "inspector-card-title");
    gtk_label_set_xalign(GTK_LABEL(chg_title), 0.0f);
    gtk_box_append(GTK_BOX(chg_box), chg_title);

    GtkWidget *chg_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *pill = gtk_label_new("[+] +45,330 -2,358");
    gtk_widget_add_css_class(pill, "caption-heading");
    gtk_widget_add_css_class(pill, "accent");
    gtk_widget_set_hexpand(pill, TRUE);
    gtk_label_set_xalign(GTK_LABEL(pill), 0.0f);
    self->changes_pill = GTK_LABEL(pill);
    gtk_box_append(GTK_BOX(chg_row), pill);

    GtkWidget *pr_btn = gtk_button_new_with_label("Create PR");
    gtk_widget_add_css_class(pr_btn, "suggested-action");
    gtk_widget_add_css_class(pr_btn, "pill");
    g_signal_connect(pr_btn, "clicked", G_CALLBACK(on_create_pr_clicked), self);
    gtk_box_append(GTK_BOX(chg_row), pr_btn);

    gtk_box_append(GTK_BOX(chg_box), chg_row);
    gtk_box_append(GTK_BOX(root), chg_box);

    kr_inspector_refresh(root);
    return root;
}

void
kr_inspector_refresh(GtkWidget *inspector)
{
    InspectorWidgets *self = g_object_get_data(G_OBJECT(inspector), "kr-inspector");
    if (self == NULL || self->app == NULL)
        return;

    const KrProject *proj = kr_state_selected(self->app->state);
    if (proj != NULL) {
        gtk_label_set_text(self->repo_label, proj->repo_path != NULL ? proj->repo_path : proj->name);
        g_autofree char *b_text = g_strdup_printf("%s (cycle %" G_GINT64_FORMAT ")",
                                                  kr_format_phase(proj->phase), proj->cycle);
        gtk_label_set_text(self->branch_label, b_text);
    } else {
        gtk_label_set_text(self->repo_label, "vibey · all projects");
        gtk_label_set_text(self->branch_label, "develop");
    }
}
