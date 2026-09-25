/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
#include "kr-mark.h"

#include <adwaita.h>
#include <math.h>

#include "vibey_tokens.h"

const int kr_mark_shell_electrons[KR_MARK_SHELLS] = {2, 8, 18, 8};

/* One full turn of the innermost shell, in microseconds; outer shells turn slower. */
#define TURN_US (12.0 * G_USEC_PER_SEC)

typedef struct {
    gboolean busy;
    gint64 started;
    guint tick;
} Mark;

static void
colour(GdkRGBA *rgba, const char *light_hex, const char *dark_hex)
{
    gboolean dark = adw_style_manager_get_dark(adw_style_manager_get_default());
    gdk_rgba_parse(rgba, dark ? dark_hex : light_hex);
}

static void
draw(GtkDrawingArea *area, cairo_t *cr, int width, int height, gpointer data)
{
    Mark *mark = data;
    double size = MIN(width, height);
    double cx = width / 2.0;
    double cy = height / 2.0;
    double phase = 0.0;
    if (mark->started != 0 && adw_get_enable_animations(GTK_WIDGET(area)))
        phase = (double) (g_get_monotonic_time() - mark->started) / TURN_US;

    GdkRGBA shell, electron, nucleus;
    colour(&shell, VIBEY_LIGHT_BORDER_STRONG_HEX, VIBEY_DARK_BORDER_STRONG_HEX);
    colour(&electron, VIBEY_LIGHT_ACCENT_DEFAULT_HEX, VIBEY_DARK_ACCENT_DEFAULT_HEX);
    if (mark->busy)
        colour(&nucleus, VIBEY_LIGHT_STATUS_ULTRA_HEX, VIBEY_DARK_STATUS_ULTRA_HEX);
    else
        colour(&nucleus, VIBEY_LIGHT_ACCENT_DEFAULT_HEX, VIBEY_DARK_ACCENT_DEFAULT_HEX);

    cairo_set_line_width(cr, MAX(size / 96.0, 0.75));
    for (int s = 0; s < KR_MARK_SHELLS; s++) {
        double radius = size * (0.16 + 0.1 * s);
        gdk_cairo_set_source_rgba(cr, &shell);
        cairo_new_sub_path(cr);
        cairo_arc(cr, cx, cy, radius, 0, 2 * G_PI);
        cairo_stroke(cr);

        int count = kr_mark_shell_electrons[s];
        double turn = phase / (1.0 + s * 0.6) * (s % 2 == 0 ? 1.0 : -1.0);
        double dot = MAX(size / (count > 8 ? 60.0 : 44.0), 0.9);
        gdk_cairo_set_source_rgba(cr, &electron);
        for (int e = 0; e < count; e++) {
            double angle = 2 * G_PI * ((double) e / count + turn);
            cairo_new_sub_path(cr);
            cairo_arc(cr, cx + radius * cos(angle), cy + radius * sin(angle), dot, 0, 2 * G_PI);
            cairo_fill(cr);
        }
    }

    double core = size * 0.085;
    cairo_pattern_t *glow = cairo_pattern_create_radial(cx, cy, 0, cx, cy, core * 1.8);
    cairo_pattern_add_color_stop_rgba(glow, 0.0, nucleus.red, nucleus.green, nucleus.blue, 1.0);
    cairo_pattern_add_color_stop_rgba(glow, 0.55, nucleus.red, nucleus.green, nucleus.blue, 0.9);
    cairo_pattern_add_color_stop_rgba(glow, 1.0, nucleus.red, nucleus.green, nucleus.blue, 0.0);
    cairo_set_source(cr, glow);
    cairo_arc(cr, cx, cy, core * 1.8, 0, 2 * G_PI);
    cairo_fill(cr);
    cairo_pattern_destroy(glow);
}

static gboolean
on_tick(GtkWidget *widget, GdkFrameClock *clock, gpointer data)
{
    (void) clock;
    (void) data;
    /* Reduced motion: the atom stands still, so there is nothing to redraw. */
    if (adw_get_enable_animations(widget))
        gtk_widget_queue_draw(widget);
    return G_SOURCE_CONTINUE;
}

static void
on_dark_changed(AdwStyleManager *manager, GParamSpec *pspec, gpointer widget)
{
    (void) manager;
    (void) pspec;
    gtk_widget_queue_draw(GTK_WIDGET(widget));
}

GtkWidget *
kr_mark_new(int size)
{
    GtkWidget *area = gtk_drawing_area_new();
    Mark *mark = g_new0(Mark, 1);
    mark->started = g_get_monotonic_time();
    gtk_drawing_area_set_content_width(GTK_DRAWING_AREA(area), size);
    gtk_drawing_area_set_content_height(GTK_DRAWING_AREA(area), size);
    gtk_drawing_area_set_draw_func(GTK_DRAWING_AREA(area), draw, mark, g_free);
    g_object_set_data(G_OBJECT(area), "kr-mark", mark);
    gtk_accessible_update_property(GTK_ACCESSIBLE(area), GTK_ACCESSIBLE_PROPERTY_LABEL,
                                   "Krypton", -1);
    mark->tick = gtk_widget_add_tick_callback(area, on_tick, NULL, NULL);
    g_signal_connect_object(adw_style_manager_get_default(), "notify::dark",
                            G_CALLBACK(on_dark_changed), area, 0);
    return area;
}

void
kr_mark_set_busy(GtkWidget *widget, gboolean busy)
{
    Mark *mark = g_object_get_data(G_OBJECT(widget), "kr-mark");
    if (mark == NULL || mark->busy == busy)
        return;
    mark->busy = busy;
    gtk_widget_queue_draw(widget);
}
