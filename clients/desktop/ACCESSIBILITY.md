<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# krypton desktop: screen readers and keyboard

What krypton does for a person using a screen reader or only the keyboard, what is checked
automatically, and what has been checked by a person. An unrun check is unknown, never passed
(ADR-0040).

## What the code does

- **Every command has a name and a key in one place.** `src/core/kr-commands.c` is the table
  the header menu, the Keyboard shortcuts dialog (`Ctrl+?`) and the registered accelerators
  read. `Ctrl+,` is Preferences and `Ctrl+Q` is Quit.
- **Icon-only controls are named.** Refresh, Main menu, Start a project and each project's
  actions menu are given an explicit accessible name through `kr_a11y_name` (`src/app/kr-a11y.h`),
  with the tooltip as the description where it carries the key. The warning marks beside a
  row are named "Warning"; the row's own text says what is wrong.
- **Widgets from libadwaita** (rows, switches, entries, dialogs, the About dialog) bring their
  own roles and names from their titles.

## What is checked automatically, and how far that goes

| Check | What it proves | What it does not |
|---|---|---|
| `tests/test-commands.c` | Every command has an action, a label and a group; no action or key is listed twice. | That a label reads well aloud. |
| `krypton-desktop` start-up | Every registered action is in the table and every table entry has an action, or krypton aborts at start. | Nothing about what a screen reader says. |
| `tests/test-accessible-names.c` | A **heuristic over the source**: each `gtk_button_new_from_icon_name` and `gtk_menu_button_set_icon_name` is followed, in the same function, by a name for that same variable. It fails when one is not. | A control built another way; that a name is a good one; anything about the running window. The views need a display and a screen reader cannot run in CI. |

## What a person has checked

Run the checklist below with the assistive technology on a real session, then fill in the
table. A row left "not run" means nobody has looked.

1. Tab reaches every control in the main window, in an order that follows the layout.
2. Every control is announced with a name and a role (the header buttons, the sidebar places,
   the project rows and their menus, the gate answer controls).
3. The Gates page can be read and a gate answered with the keyboard alone.
4. The header menu opens from the keyboard and each item announces its shortcut.
5. The Keyboard shortcuts and About dialogs are readable, and Escape closes them.
6. The tray menu is operable from the keyboard (Linux: needs a StatusNotifier host).
7. A change in the number of waiting gates is announced. *Whether the offline banner and the
   gates badge announce to a screen reader is not known.*

| Platform | Assistive technology and version | Date | Run by | Items passed | Items failed | Notes |
|---|---|---|---|---|---|---|
| GNOME | Orca | not run | | | | |
| macOS | VoiceOver | not run | | | | |

## Also not run

- **The Linux tray has never run against a real StatusNotifier host.** It is compile-checked.
  GNOME needs the AppIndicator extension; KDE has a host natively.
- **The menu's shortcut hints** are drawn by GTK from the registered accelerators. The
  Keyboard shortcuts dialog was run headless under Xvfb on GTK 4.14 and libadwaita 1.5 and
  shows the keys; the header menu popover itself was not opened and looked at.
- **There is no macOS menu bar** (`gtk_application_set_menubar`) and no command palette:
  the menu is the header-bar menu on every platform.
