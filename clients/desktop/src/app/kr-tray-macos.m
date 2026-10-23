/* Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). */
/* The macOS tray: an NSStatusItem in the menu bar, with the model's entries as its menu.
 * Compiled with ARC; the item and its target live in the struct as retained CF pointers. */
#import <Cocoa/Cocoa.h>

#include "kr-tray-host.h"

typedef struct {
    KrTrayActivate activate;
    gpointer data;
    char *action;
} Click;

static gboolean
deliver(gpointer data)
{
    Click *click = data;
    click->activate(click->action, click->data);
    g_free(click->action);
    g_free(click);
    return G_SOURCE_REMOVE;
}

@interface KrTrayTarget : NSObject
@property(nonatomic) KrTrayActivate activate;
@property(nonatomic) gpointer data;
- (void)clicked:(NSMenuItem *)menuItem;
@end

@implementation KrTrayTarget
- (void)clicked:(NSMenuItem *)menuItem
{
    NSString *action = menuItem.representedObject;
    if (action == nil)
        return;
    /* The menu runs its own tracking loop; hand the action to GLib's main loop instead of
     * running GTK from inside it. */
    Click *click = g_new0(Click, 1);
    click->activate = self.activate;
    click->data = self.data;
    click->action = g_strdup(action.UTF8String);
    g_idle_add(deliver, click);
}
@end

struct KrTray {
    CFTypeRef item;   /* NSStatusItem, retained */
    CFTypeRef target; /* KrTrayTarget, retained: an NSMenuItem's target is weak */
};

static NSImage *
symbol(NSString *name)
{
    NSImage *image = [NSImage imageWithSystemSymbolName:name accessibilityDescription:@"krypton"];
    [image setTemplate:YES];
    return image;
}

gboolean
kr_tray_supported(void)
{
    return TRUE;
}

KrTray *
kr_tray_new(const char *app_id, const char *name, KrTrayActivate activate, gpointer user_data)
{
    (void) app_id;
    (void) name;
    if (NSApp == nil)
        return NULL;
    NSStatusItem *item =
        [[NSStatusBar systemStatusBar] statusItemWithLength:NSVariableStatusItemLength];
    if (item == nil)
        return NULL;
    KrTrayTarget *target = [[KrTrayTarget alloc] init];
    target.activate = activate;
    target.data = user_data;
    KrTray *tray = g_new0(KrTray, 1);
    tray->item = CFBridgingRetain(item);
    tray->target = CFBridgingRetain(target);
    return tray;
}

void
kr_tray_show(KrTray *tray, const KrTrayModel *model)
{
    NSStatusItem *item = (__bridge NSStatusItem *) tray->item;
    KrTrayTarget *target = (__bridge KrTrayTarget *) tray->target;
    NSStatusBarButton *button = item.button;
    NSImage *image = symbol(model->attention ? @"exclamationmark.bubble.fill" : @"bubble.left");
    if (image != nil) {
        button.image = image;
        button.title = @"";
    } else {
        button.title = model->attention ? @"krypton !" : @"krypton"; /* no SF Symbols before 11 */
    }
    button.toolTip = [NSString stringWithUTF8String:model->tooltip];

    NSMenu *menu = [[NSMenu alloc] init];
    menu.autoenablesItems = NO;
    for (guint i = 0; i < model->entries->len; i++) {
        const KrTrayEntry *entry = g_ptr_array_index(model->entries, i);
        NSMenuItem *menu_item =
            [[NSMenuItem alloc] initWithTitle:[NSString stringWithUTF8String:entry->label]
                                       action:@selector(clicked:)
                                keyEquivalent:@""];
        menu_item.target = target;
        menu_item.representedObject = [NSString stringWithUTF8String:entry->action];
        [menu addItem:menu_item];
    }
    item.menu = menu;
}

gboolean
kr_tray_ready(const KrTray *tray)
{
    return tray != NULL;
}

void
kr_tray_free(KrTray *tray)
{
    if (tray == NULL)
        return;
    NSStatusItem *item = (__bridge NSStatusItem *) tray->item;
    [[NSStatusBar systemStatusBar] removeStatusItem:item];
    CFRelease(tray->item);
    CFRelease(tray->target);
    g_free(tray);
}
