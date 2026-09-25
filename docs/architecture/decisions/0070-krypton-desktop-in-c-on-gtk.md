# 0070 — Krypton desktop in C, on GTK 4 and libadwaita

**Status:** accepted · **Date:** 2026-09-25 · **Supersedes in part:** runbook 08-clients (its Tauri desktop) · **Cites:** sub-doctrine 9.b, 12.c, SD-01 v1.0 · **Related:** ADR-0016, ADR-0062, ADR-0065, ADR-0066, ADR-0068 · **Evidence:** `develop` at `0823cdfd`, read 2026-09-25

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`. All are done in the change that
carries it.

## Context

The 3.0.0 client suite includes a desktop app for macOS, Ubuntu and Arch. Runbook
08-clients had planned it in Tauri. On 2026-09-25 the operator chose C on GTK 4 and
libadwaita instead. The app is one of the Krypton surfaces (ADR-0065). It must:

- reach vibey only through the hub (ADR-0068), never the database;
- wear the design tokens (ADR-0066);
- offer Light, Dark and System (ADR-0062);
- ship a stable and a nightly channel side by side.

Two rules shape the code:

- **Every class has an interface beside it** (ADR-0016, 9.b). C has no classes. It does
  have headers and translation units.
- **Being on the network proves nothing** (SD-01). A hub found by mDNS is still a stranger
  until it pairs.

## Decision

1. **A pure-C core and thin views.** `clients/desktop/src/core` builds
   libkryptondesktop. It depends only on GLib, json-glib, libsoup 3 and the mDNS library,
   and never on GTK. It holds the models, the hub client, the state, formatting, settings,
   pairing and discovery. `src/app` holds the GTK views. They read the state and redraw
   the slice that changed, and they never speak HTTP themselves.
2. **ADR-0016 in C: a header per module is its interface.** `kr-<module>.h` declares, and
   `kr-<module>.c` implements. A module with more than one implementation, such as
   discovery (Avahi on Linux, `dns_sd.h` on macOS), declares a table of function pointers
   in its header. The implementations provide it, and a test provides a fake.
3. **One contract with the CLI.** The core parses the documents the hub returns, which are
   the CLI's `--json` documents. The answer shape for each gate kind mirrors
   `src/vibey/cli/gate_answers.py`. A test parses the CLI's own golden
   `tests/cli/golden/vibey-loops.json`, so a change there that the desktop cannot read
   fails the desktop's build.
4. **The token is kept the way the hub keeps it.** The desktop reads the host token only
   from a regular file that is not a symlink and is readable by its owner alone. It checks
   this on the open descriptor, as the hub does. It sends the token only as a bearer
   header, and it never follows a redirect.
5. **The pairing contract is the client's half, and provisional.** A pairing offer is
   `vibey-pair://host:port?code=<6 digits>&fp=<SHA-256 of the hub certificate>`. The
   fingerprint is pinned once paired. The hub's pairing change may amend this. Until it
   lands, the desktop checks a code and says that the hub cannot take it yet. It never
   pretends to pair.
6. **The design tokens are consumed, never copied.** The mark's colours come from
   `design/dist/c/vibey_tokens.h`. The generated `design/dist/gtk` stylesheets are
   compiled in unchanged as the application's `style.css` and `style-dark.css`, which
   libadwaita loads. The theme mode is the tokens' own `VibeyThemeMode`, mapped onto
   `AdwStyleManager`.
7. **Channels are a build option, not a fork.** `-Dchannel=nightly` changes the app id,
   the name people see and the settings directory. The two install side by side.
8. **Quality gates.** CI builds with `-Wall -Wextra -Werror` and ASan and UBSan, on Ubuntu
   and on Arch. GLib tests cover the core, including the hub client against a real
   loopback server. gcovr gates the core's coverage. The desktop entry and the AppStream
   metadata are validated. Packaging (PKGBUILD, Flatpak) is declared only: nothing is
   published until the operator decides (12.d).

## Why C on GTK, and not Tauri

GTK 4 with libadwaita is the native toolkit on the GNOME desktops Ubuntu and Arch users
run. It gives adaptive layouts, the platform's own dark style and its accessibility tree
without an embedded browser. The cost is a macOS bundle that carries the GTK runtime, and
the C discipline this ADR's interfaces and sanitizers pay for. The mobile and web app covers the surfaces where a browser engine is native.

## Consequences

- The C core has no GTK in it, so a future macOS-native shell could reuse it whole.
- The coverage gate starts below the 100% the Python layers carry. The mDNS backends need
  a daemon a CI runner does not have, and a few error paths have no test yet. Both are
  said in the CI job, and the gate is raised as they gain tests.
- The following are follow-ups, each its own change:
  - the Broadway-backend UI smoke tests and screenshot gallery;
  - libFuzzer over the JSON parsers;
  - the macOS UNUserNotificationCenter and Keychain shims;
  - GSound playback, from the one notifications-and-sounds system;
  - the tray item;
  - the live feed, once `feat/hub-live` lands.
