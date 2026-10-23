* **krypton desktop starts, pauses and unwinds projects, and has an app menu, an About dialog and a tray item:** the
  same four hub routes the phone and the VS Code extension use (ADR-0091), a dry run before any unwind, and a tray
  (menu bar on macOS, StatusNotifierItem elsewhere) that shows waiting gates and lets the window close to it. The
  Linux tray is compile-checked, not run against a bus.
