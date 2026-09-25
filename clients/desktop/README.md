# Krypton desktop

The desktop app for vibey, for Linux and macOS. It is written in C17 on GTK 4 and
libadwaita, and it talks to a vibey hub (`vibey serve`, [ADR-0068](../../docs/architecture/decisions/0068-the-hub.md))
over the [hub API](../../docs/reference/hub-api.md). It never touches vibey's database.

## What it shows

| Place | What you get |
|---|---|
| Projects | Every project, its phase and cycle, and how many gates wait on it. |
| Gates | Every gate waiting on you, with the controls its kind takes: a verdict or choice as buttons, a new bound for a grant, a retry, or a free-form answer. It warns you before an answer that can spend money. A desktop notification tells you when a new gate is raised. |
| Lanes | The lanes running on the hub's computer. The Krypton mark in the sidebar glows while one runs. |
| Loops and effort | The loops, their engines and the effort ladder, up to ULTRA. |
| Budgets | What the chosen project has spent this cycle, against its caps. |
| Doctor | The checks the hub runs itself. |
| Devices | Hubs found on your network (`_vibey._tcp`), this computer's hub, and pairing by a 6-digit code. |
| Settings | Light, Dark or System (the default, which follows your desktop live), notifications and sounds. |

Keyboard: `Ctrl+R` or `F5` refreshes, `Ctrl+G` opens Gates, `Ctrl+,` opens Settings, and
`Ctrl+Q` quits. On a narrow window the sidebar folds into one pane with back navigation.

## Connecting

On the computer that runs the hub, Krypton reads the hub's token the way the hub keeps it:
`~/.local/state/vibey/hub/token` on Linux, `~/Library/Application Support/vibey/hub/token`
on macOS, or `$VIBEY_HUB_STATE_DIR/token`. The file must be yours alone (mode 0600) and
not a symlink, or Krypton refuses it, just as the hub does.

A hub on another computer is found on the network, but being on the network proves
nothing (SD-01). A device is trusted only once it has paired with the hub's QR code or
6-digit code. The hub's side of pairing is still to come. Until then, Krypton checks a
code and says plainly that the hub cannot take it yet. The client's half of the pairing
contract is written down in [`src/core/kr-pairing.h`](src/core/kr-pairing.h) and is
marked provisional.

## Building

You need Meson 1.1 or newer, GLib 2.74, json-glib, libsoup 3, GTK 4.12 and libadwaita 1.4.
Discovery uses Avahi on Linux and `dns_sd.h` on macOS.

```bash
meson setup build
meson compile -C build
meson test -C build          # the core's GLib tests
./build/src/app/krypton-desktop
```

With no GTK installed (a bare macOS, say), `meson setup build -Dgui=disabled` still builds
and tests the core. json-glib is fetched from its wrap when the system has none.

| Option | Default | Meaning |
|---|---|---|
| `-Dchannel=stable\|nightly` | `stable` | Nightly installs beside stable, as "Krypton Nightly" with its own app id and data directory. |
| `-Dgui=` | `auto` | Build the GTK app, not only the core. |
| `-Dhub_transport=` | `auto` | The libsoup hub client. |
| `-Ddiscovery=` | `auto` | Avahi or dns_sd. |

## How it is built

- **`src/core/`: libkryptondesktop, pure C with no GTK.** Each module is a header, its
  interface, and a `.c`, which is ADR-0016 in C:
  - `kr-model`: the hub's documents as structs;
  - `kr-hub` and `kr-hub-client`: routes, the token and the libsoup transport;
  - `kr-answer`: which answer each gate kind takes, mirroring `src/vibey/cli/gate_answers.py`;
  - `kr-state`: what the app knows, and which gates are new;
  - `kr-format`: money, durations and phases in words;
  - `kr-settings`: themes and channels;
  - `kr-pairing`;
  - `kr-discovery`, with its Avahi and dns_sd backends.
- **`src/app/`: thin GTK views.** They read the state and redraw the slice that changed.
  Colours come from the design tokens (ADR-0066): `design/dist/c/vibey_tokens.h` for the
  mark, and the generated `design/dist/gtk` stylesheets, which libadwaita loads as the
  app's `style.css` and `style-dark.css`.
- **`tests/`: GLib tests over the core.** They include the hub client against a real
  loopback HTTP server. The CI job `desktop` builds everything with `-Werror` under ASan
  and UBSan on Ubuntu and Arch, and gates the core's coverage with gcovr.

Packaging is declared but not published. See [PACKAGING.md](PACKAGING.md).
