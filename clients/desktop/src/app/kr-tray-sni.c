/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The freedesktop tray: a StatusNotifierItem on the session bus, with its menu served as a
 * com.canonical.dbusmenu (a flat list, which is all the model has). It registers with the
 * StatusNotifierWatcher whenever one is on the bus and says it is ready only then: GNOME
 * shows these only with the AppIndicator extension, and a window must not close to a tray
 * nobody can see. */
#include <gio/gio.h>
#include <unistd.h>

#include "kr-tray-host.h"

#define ITEM_PATH "/StatusNotifierItem"
#define MENU_PATH "/MenuBar"
#define WATCHER_NAME "org.kde.StatusNotifierWatcher"

static const char ITEM_XML[] =
    "<node><interface name='org.kde.StatusNotifierItem'>"
    "<property name='Category' type='s' access='read'/>"
    "<property name='Id' type='s' access='read'/>"
    "<property name='Title' type='s' access='read'/>"
    "<property name='Status' type='s' access='read'/>"
    "<property name='WindowId' type='i' access='read'/>"
    "<property name='IconName' type='s' access='read'/>"
    "<property name='AttentionIconName' type='s' access='read'/>"
    "<property name='ToolTip' type='(sa(iiay)ss)' access='read'/>"
    "<property name='ItemIsMenu' type='b' access='read'/>"
    "<property name='Menu' type='o' access='read'/>"
    "<method name='Activate'><arg type='i' direction='in'/><arg type='i' direction='in'/></method>"
    "<method name='SecondaryActivate'><arg type='i' direction='in'/><arg type='i' direction='in'/></method>"
    "<method name='ContextMenu'><arg type='i' direction='in'/><arg type='i' direction='in'/></method>"
    "<method name='Scroll'><arg type='i' direction='in'/><arg type='s' direction='in'/></method>"
    "<signal name='NewTitle'/><signal name='NewStatus'><arg type='s'/></signal>"
    "<signal name='NewToolTip'/><signal name='NewIcon'/>"
    "</interface></node>";

static const char MENU_XML[] =
    "<node><interface name='com.canonical.dbusmenu'>"
    "<property name='Version' type='u' access='read'/>"
    "<property name='TextDirection' type='s' access='read'/>"
    "<property name='Status' type='s' access='read'/>"
    "<property name='IconThemePath' type='as' access='read'/>"
    "<method name='GetLayout'><arg type='i' direction='in'/><arg type='i' direction='in'/>"
    "<arg type='as' direction='in'/><arg type='u' direction='out'/>"
    "<arg type='(ia{sv}av)' direction='out'/></method>"
    "<method name='GetGroupProperties'><arg type='ai' direction='in'/><arg type='as' direction='in'/>"
    "<arg type='a(ia{sv})' direction='out'/></method>"
    "<method name='GetProperty'><arg type='i' direction='in'/><arg type='s' direction='in'/>"
    "<arg type='v' direction='out'/></method>"
    "<method name='Event'><arg type='i' direction='in'/><arg type='s' direction='in'/>"
    "<arg type='v' direction='in'/><arg type='u' direction='in'/></method>"
    "<method name='EventGroup'><arg type='a(isvu)' direction='in'/><arg type='ai' direction='out'/></method>"
    "<method name='AboutToShow'><arg type='i' direction='in'/><arg type='b' direction='out'/></method>"
    "<method name='AboutToShowGroup'><arg type='ai' direction='in'/><arg type='ai' direction='out'/>"
    "<arg type='ai' direction='out'/></method>"
    "<signal name='LayoutUpdated'><arg type='u'/><arg type='i'/></signal>"
    "<signal name='ItemsPropertiesUpdated'><arg type='a(ia{sv})'/><arg type='a(ia{sv})'/></signal>"
    "</interface></node>";

struct KrTray {
    char *app_id;
    char *name;
    KrTrayActivate activate;
    gpointer data;
    KrTrayModel *model; /* what is drawn; never NULL once kr_tray_show has run */
    guint revision;
    GDBusConnection *bus;
    GCancellable *cancel; /* the registration call in flight: it outlives a freed tray otherwise */
    GDBusNodeInfo *item_info;
    GDBusNodeInfo *menu_info;
    guint own_id;
    guint watch_id;
    guint item_registration;
    guint menu_registration;
    char *bus_name; /* what the watcher is told to look for */
    gboolean ready;
};

static void
fire(KrTray *tray, const char *action)
{
    tray->activate(action, tray->data);
}

/* ---- the item ------------------------------------------------------------------------ */

static GVariant *
item_property(GDBusConnection *connection, const char *sender, const char *object_path,
              const char *interface_name, const char *property, GError **error, gpointer data)
{
    (void) connection;
    (void) sender;
    (void) object_path;
    (void) interface_name;
    KrTray *tray = data;
    const KrTrayModel *model = tray->model;
    if (g_str_equal(property, "Category"))
        return g_variant_new_string("ApplicationStatus");
    if (g_str_equal(property, "Id"))
        return g_variant_new_string(tray->app_id);
    if (g_str_equal(property, "Title"))
        return g_variant_new_string(tray->name);
    if (g_str_equal(property, "Status"))
        return g_variant_new_string(model != NULL && model->attention ? "NeedsAttention" : "Active");
    if (g_str_equal(property, "WindowId"))
        return g_variant_new_int32(0);
    if (g_str_equal(property, "IconName") || g_str_equal(property, "AttentionIconName"))
        return g_variant_new_string(tray->app_id); /* the installed hicolor icon */
    if (g_str_equal(property, "ToolTip")) {
        GVariantBuilder pixmaps;
        g_variant_builder_init(&pixmaps, G_VARIANT_TYPE("a(iiay)"));
        return g_variant_new("(sa(iiay)ss)", "", &pixmaps, tray->name,
                             model != NULL ? model->tooltip : "");
    }
    if (g_str_equal(property, "ItemIsMenu"))
        return g_variant_new_boolean(FALSE);
    if (g_str_equal(property, "Menu"))
        return g_variant_new_object_path(MENU_PATH);
    g_set_error(error, G_DBUS_ERROR, G_DBUS_ERROR_UNKNOWN_PROPERTY, "No property %s", property);
    return NULL;
}

static void
item_call(GDBusConnection *connection, const char *sender, const char *object_path,
          const char *interface_name, const char *method, GVariant *parameters,
          GDBusMethodInvocation *invocation, gpointer data)
{
    (void) connection;
    (void) sender;
    (void) object_path;
    (void) interface_name;
    (void) parameters;
    KrTray *tray = data;
    /* A click opens the window; a middle click goes to what is waiting on the person. */
    if (g_str_equal(method, "Activate") || g_str_equal(method, "ContextMenu"))
        fire(tray, "open");
    else if (g_str_equal(method, "SecondaryActivate"))
        fire(tray, "show-gates");
    g_dbus_method_invocation_return_value(invocation, NULL);
}

/* ---- the menu ------------------------------------------------------------------------ */

/* A host may read before the first model is drawn: that is an empty menu, not a crash. */
static guint
entry_count(const KrTray *tray)
{
    return tray->model != NULL ? tray->model->entries->len : 0;
}

static GVariant *
item_properties(const KrTrayEntry *entry)
{
    GVariantBuilder props;
    g_variant_builder_init(&props, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&props, "{sv}", "label", g_variant_new_string(entry->label));
    g_variant_builder_add(&props, "{sv}", "enabled", g_variant_new_boolean(TRUE));
    g_variant_builder_add(&props, "{sv}", "visible", g_variant_new_boolean(TRUE));
    return g_variant_builder_end(&props);
}

static GVariant *
root_properties(void)
{
    GVariantBuilder props;
    g_variant_builder_init(&props, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&props, "{sv}", "children-display", g_variant_new_string("submenu"));
    return g_variant_builder_end(&props);
}

static GVariant *
layout(const KrTray *tray)
{
    GVariantBuilder children;
    g_variant_builder_init(&children, G_VARIANT_TYPE("av"));
    for (guint i = 0; i < entry_count(tray); i++) {
        const KrTrayEntry *entry = g_ptr_array_index(tray->model->entries, i);
        GVariantBuilder none;
        g_variant_builder_init(&none, G_VARIANT_TYPE("av"));
        GVariant *child = g_variant_new("(i@a{sv}av)", (gint32) (i + 1), item_properties(entry), &none);
        g_variant_builder_add(&children, "v", child);
    }
    return g_variant_new("(i@a{sv}av)", 0, root_properties(), &children);
}

static const KrTrayEntry *
entry_for(const KrTray *tray, gint32 id)
{
    if (id < 1 || (guint) id > entry_count(tray))
        return NULL;
    return g_ptr_array_index(tray->model->entries, (guint) id - 1);
}

static void
menu_call(GDBusConnection *connection, const char *sender, const char *object_path,
          const char *interface_name, const char *method, GVariant *parameters,
          GDBusMethodInvocation *invocation, gpointer data)
{
    (void) connection;
    (void) sender;
    (void) object_path;
    (void) interface_name;
    KrTray *tray = data;
    if (g_str_equal(method, "GetLayout")) {
        g_dbus_method_invocation_return_value(
            invocation, g_variant_new("(u@(ia{sv}av))", tray->revision, layout(tray)));
    } else if (g_str_equal(method, "GetGroupProperties")) {
        g_autoptr(GVariant) ids = g_variant_get_child_value(parameters, 0);
        GVariantBuilder out;
        g_variant_builder_init(&out, G_VARIANT_TYPE("a(ia{sv})"));
        GVariantIter iter;
        g_variant_iter_init(&iter, ids);
        gint32 id;
        gboolean any = FALSE;
        while (g_variant_iter_next(&iter, "i", &id)) {
            any = TRUE;
            const KrTrayEntry *entry = entry_for(tray, id);
            if (entry != NULL)
                g_variant_builder_add(&out, "(i@a{sv})", id, item_properties(entry));
        }
        if (!any) /* an empty list asks for all of them */
            for (guint i = 0; i < entry_count(tray); i++)
                g_variant_builder_add(&out, "(i@a{sv})", (gint32) (i + 1),
                                      item_properties(g_ptr_array_index(tray->model->entries, i)));
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(a(ia{sv}))", &out));
    } else if (g_str_equal(method, "GetProperty")) {
        gint32 id;
        const char *name;
        g_variant_get(parameters, "(i&s)", &id, &name);
        const KrTrayEntry *entry = entry_for(tray, id);
        if (entry != NULL && g_str_equal(name, "label"))
            g_dbus_method_invocation_return_value(
                invocation, g_variant_new("(v)", g_variant_new_string(entry->label)));
        else
            g_dbus_method_invocation_return_dbus_error(
                invocation, "org.freedesktop.DBus.Error.InvalidArgs", "No such property");
    } else if (g_str_equal(method, "Event")) {
        gint32 id;
        const char *event;
        g_variant_get(parameters, "(i&sv@u)", &id, &event, NULL, NULL);
        const KrTrayEntry *entry = entry_for(tray, id);
        if (entry != NULL && g_str_equal(event, "clicked"))
            fire(tray, entry->action);
        g_dbus_method_invocation_return_value(invocation, NULL);
    } else if (g_str_equal(method, "EventGroup")) {
        g_autoptr(GVariant) events = g_variant_get_child_value(parameters, 0);
        GVariantIter iter;
        g_variant_iter_init(&iter, events);
        gint32 id;
        const char *event;
        while (g_variant_iter_next(&iter, "(i&svu)", &id, &event, NULL, NULL)) {
            const KrTrayEntry *entry = entry_for(tray, id);
            if (entry != NULL && g_str_equal(event, "clicked"))
                fire(tray, entry->action);
        }
        GVariantBuilder missing;
        g_variant_builder_init(&missing, G_VARIANT_TYPE("ai"));
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(ai)", &missing));
    } else if (g_str_equal(method, "AboutToShow")) {
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(b)", FALSE));
    } else if (g_str_equal(method, "AboutToShowGroup")) {
        GVariantBuilder updates;
        GVariantBuilder missing;
        g_variant_builder_init(&updates, G_VARIANT_TYPE("ai"));
        g_variant_builder_init(&missing, G_VARIANT_TYPE("ai"));
        g_dbus_method_invocation_return_value(invocation,
                                              g_variant_new("(aiai)", &updates, &missing));
    } else {
        g_dbus_method_invocation_return_dbus_error(
            invocation, "org.freedesktop.DBus.Error.UnknownMethod", method);
    }
}

static GVariant *
menu_property(GDBusConnection *connection, const char *sender, const char *object_path,
              const char *interface_name, const char *property, GError **error, gpointer data)
{
    (void) connection;
    (void) sender;
    (void) object_path;
    (void) interface_name;
    (void) data;
    if (g_str_equal(property, "Version"))
        return g_variant_new_uint32(3);
    if (g_str_equal(property, "TextDirection"))
        return g_variant_new_string("ltr");
    if (g_str_equal(property, "Status"))
        return g_variant_new_string("normal");
    if (g_str_equal(property, "IconThemePath")) {
        GVariantBuilder none;
        g_variant_builder_init(&none, G_VARIANT_TYPE("as"));
        return g_variant_builder_end(&none);
    }
    g_set_error(error, G_DBUS_ERROR, G_DBUS_ERROR_UNKNOWN_PROPERTY, "No property %s", property);
    return NULL;
}

/* ---- registering with the watcher ---------------------------------------------------- */

static void
on_registered(GObject *source, GAsyncResult *result, gpointer data)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(GVariant) reply =
        g_dbus_connection_call_finish(G_DBUS_CONNECTION(source), result, &error);
    /* A cancelled call means the tray was freed while this was in flight: `data` is gone. */
    if (g_error_matches(error, G_IO_ERROR, G_IO_ERROR_CANCELLED))
        return;
    KrTray *tray = data;
    tray->ready = reply != NULL;
}

static void
register_with_watcher(KrTray *tray)
{
    g_dbus_connection_call(tray->bus, WATCHER_NAME, "/StatusNotifierWatcher", WATCHER_NAME,
                           "RegisterStatusNotifierItem", g_variant_new("(s)", tray->bus_name),
                           NULL, G_DBUS_CALL_FLAGS_NONE, -1, tray->cancel, on_registered, tray);
}

static void
on_watcher_appeared(GDBusConnection *connection, const char *name, const char *owner,
                    gpointer data)
{
    (void) connection;
    (void) name;
    (void) owner;
    register_with_watcher(data);
}

static void
on_watcher_vanished(GDBusConnection *connection, const char *name, gpointer data)
{
    (void) connection;
    (void) name;
    KrTray *tray = data;
    tray->ready = FALSE;
}

static void
on_name_acquired(GDBusConnection *connection, const char *name, gpointer data)
{
    (void) connection;
    (void) name;
    KrTray *tray = data;
    tray->watch_id = g_bus_watch_name_on_connection(tray->bus, WATCHER_NAME,
                                                    G_BUS_NAME_WATCHER_FLAGS_NONE,
                                                    on_watcher_appeared, on_watcher_vanished, tray,
                                                    NULL);
}

/* ---- the interface ------------------------------------------------------------------- */

gboolean
kr_tray_supported(void)
{
    return TRUE;
}

KrTray *
kr_tray_new(const char *app_id, const char *name, KrTrayActivate activate, gpointer user_data)
{
    g_autoptr(GError) error = NULL;
    g_autoptr(GDBusConnection) bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &error);
    if (bus == NULL)
        return NULL;
    KrTray *tray = g_new0(KrTray, 1);
    tray->app_id = g_strdup(app_id);
    tray->name = g_strdup(name);
    tray->activate = activate;
    tray->data = user_data;
    tray->bus = g_steal_pointer(&bus);
    tray->cancel = g_cancellable_new();
    tray->item_info = g_dbus_node_info_new_for_xml(ITEM_XML, NULL);
    tray->menu_info = g_dbus_node_info_new_for_xml(MENU_XML, NULL);
    const GDBusInterfaceVTable item_vtable = {item_call, item_property, NULL, {0}};
    const GDBusInterfaceVTable menu_vtable = {menu_call, menu_property, NULL, {0}};
    tray->item_registration = g_dbus_connection_register_object(
        tray->bus, ITEM_PATH, tray->item_info->interfaces[0], &item_vtable, tray, NULL, NULL);
    tray->menu_registration = g_dbus_connection_register_object(
        tray->bus, MENU_PATH, tray->menu_info->interfaces[0], &menu_vtable, tray, NULL, NULL);
    if (tray->item_registration == 0 || tray->menu_registration == 0) {
        kr_tray_free(tray);
        return NULL;
    }
    tray->bus_name = g_strdup_printf("org.kde.StatusNotifierItem-%d-1", (int) getpid());
    tray->own_id = g_bus_own_name_on_connection(tray->bus, tray->bus_name,
                                                G_BUS_NAME_OWNER_FLAGS_NONE, on_name_acquired,
                                                NULL, tray, NULL);
    return tray;
}

void
kr_tray_show(KrTray *tray, const KrTrayModel *model)
{
    gboolean first = tray->model == NULL;
    KrTrayModel *old = tray->model;
    KrTrayModel *copy = kr_tray_model_copy(model);
    tray->model = copy;
    tray->revision++;
    if (old != NULL)
        kr_tray_model_free(old);
    if (first)
        return; /* nothing has read it yet: no signal to send */
    g_dbus_connection_emit_signal(tray->bus, NULL, ITEM_PATH, "org.kde.StatusNotifierItem",
                                  "NewStatus",
                                  g_variant_new("(s)", model->attention ? "NeedsAttention" : "Active"),
                                  NULL);
    g_dbus_connection_emit_signal(tray->bus, NULL, ITEM_PATH, "org.kde.StatusNotifierItem",
                                  "NewToolTip", NULL, NULL);
    g_dbus_connection_emit_signal(tray->bus, NULL, MENU_PATH, "com.canonical.dbusmenu",
                                  "LayoutUpdated", g_variant_new("(ui)", tray->revision, 0), NULL);
}

gboolean
kr_tray_ready(const KrTray *tray)
{
    return tray != NULL && tray->ready;
}

void
kr_tray_free(KrTray *tray)
{
    if (tray == NULL)
        return;
    g_cancellable_cancel(tray->cancel);
    g_clear_object(&tray->cancel);
    if (tray->watch_id != 0)
        g_bus_unwatch_name(tray->watch_id);
    if (tray->own_id != 0)
        g_bus_unown_name(tray->own_id);
    if (tray->item_registration != 0)
        g_dbus_connection_unregister_object(tray->bus, tray->item_registration);
    if (tray->menu_registration != 0)
        g_dbus_connection_unregister_object(tray->bus, tray->menu_registration);
    g_clear_pointer(&tray->item_info, g_dbus_node_info_unref);
    g_clear_pointer(&tray->menu_info, g_dbus_node_info_unref);
    g_clear_object(&tray->bus);
    kr_tray_model_free(tray->model);
    g_free(tray->bus_name);
    g_free(tray->app_id);
    g_free(tray->name);
    g_free(tray);
}
