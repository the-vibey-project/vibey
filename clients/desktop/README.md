# krypton desktop

The desktop app for vibey, for Linux and macOS. It is written in C17 on GTK 4 and
libadwaita, and it talks to a vibey hub (`vibey serve`, [ADR-0068](../../docs/architecture/decisions/0068-the-hub.md))
over the [hub API](../../docs/reference/hub-api.md). It never touches vibey's database.

## What it shows

| Place | What you get |
|---|---|
| Projects | Every project, its phase and cycle, and how many gates wait on it. |
| Gates | Every gate waiting on you, with the controls its kind takes: a verdict or choice as buttons, a new bound for a grant, a retry, or a free-form answer. It warns you before an answer that can spend money. A desktop notification tells you when a new gate is raised. |
| Lanes | The lanes running on the hub's computer. The krypton mark in the sidebar glows while one runs. |
| Loops and effort | The loops, their engines and the effort ladder, up to ULTRA. |
| Budgets | What the chosen project has spent this cycle, against its caps. |
| Doctor | The checks the hub runs itself. |
| Run on GitHub | A vibey command run on the repository's GitHub-hosted runners, as `vibey -w` runs it ([ADR-0085](../../docs/architecture/decisions/0085-vibey-on-the-workflows.md)). Type the command as it would follow `vibey -w` (`status --json`; double quotes keep spaces), and krypton sends it through the hub, asks every ten seconds where it is (queued, running, done or failed) for up to an hour, links its GitHub run, and shows its exit code and what it printed, selectable, in monospace. The paired device needs the `workflows` scope, and the scopes of what the command itself does; a hub with the workflows switched off, or a command the hub never runs (`migrate`, `budget set`), is said as such. |
| Devices | Hubs found on your network (`_vibey._tcp`) with the certificate each advertises, this computer's hub, the hub this device is paired with and each scope it holds, in words, and pairing by the host's 6-digit code or its `vibey-pair://` address. |
| Settings | Light, Dark or System (the default, which follows your desktop live), notifications and sounds. |

Keyboard: `Ctrl+R` or `F5` refreshes, `Ctrl+G` opens Gates, `Ctrl+,` opens Settings, and
`Ctrl+Q` quits. On a narrow window the sidebar folds into one pane with back navigation.

## Connecting

On the computer that runs the hub, krypton reads the hub's token the way the hub keeps it:
`~/.local/state/vibey/hub/token` on Linux, `~/Library/Application Support/vibey/hub/token`
on macOS, or `$VIBEY_HUB_STATE_DIR/token`. The file must be yours alone (mode 0600) and
not a symlink, or krypton refuses it, just as the hub does.

A hub on another computer is found on the network, but being on the network proves
nothing (SD-01). krypton reaches it only as a device the host has paired, never with the
host's token:

1. On the hub's computer, the host offers a code: `vibey hub pair --scope view` (add the
   scopes this device may use: `--scope workflows` lets it run commands on GitHub from the
   Run on GitHub page). It prints a 6-digit code, valid once for two minutes, and
   beneath it the pairing address, `vibey-pair://<host>:<port>?fp=<certificate>&code=…`.
2. In krypton's Devices page, either choose the hub krypton found, compare the certificate
   shown under it with the one `vibey hub pair` printed, and type the 6-digit code; or paste
   the whole `vibey-pair://` address, which names the hub and its certificate itself.
3. krypton claims the code (`POST /api/v1/pairing/claim`, ADR-0068 and ADR-0071). The hub answers, once,
   with this device's id and its own key. From then on krypton signs every request with that
   key (HMAC-SHA256, the form the hub checks); the key itself is never sent.

A hub on the LAN serves its own certificate, and krypton trusts that one certificate and no
other: its SHA-256 fingerprint is pinned at pairing, and a hub that shows any other
certificate is refused before anything is sent to it, the code included. A code typed for a
hub on another computer is accepted only when krypton knows its certificate; without one,
krypton asks for the `vibey-pair://` address instead.

Every refusal is said as it is: a wrong, spent or expired code; pairing not enabled on that
hub; too many attempts; no hub answering; a certificate other than the paired one.

**Where the key is kept.** In `paired-hub.ini` beside krypton's settings
(`$XDG_CONFIG_HOME/krypton/`, by default `~/.config/krypton/` on Linux and macOS alike;
`krypton-nightly` for the nightly channel), written as mode 0600 in a 0700 directory and
refused when it is a symlink or readable by anyone else. That is how the hub keeps its own
token and its devices' keys, and no stronger: anyone who can read the file can act as this
device. A keyring (libsecret, the macOS Keychain) is not used yet. krypton keeps one pairing
at a time; pairing with another hub replaces it, and the host revokes a device with
`vibey hub revoke <device>`.

## Building

You need Meson 1.1 or newer, GLib 2.74, json-glib, libsoup 3, GTK 4.12 and libadwaita 1.4,
and glib-networking at run time to reach a hub on the LAN over TLS. Discovery uses Avahi on
Linux and `dns_sd.h` on macOS.

```bash
meson setup build
meson compile -C build
meson test -C build          # the core's GLib tests
./build/src/app/krypton-desktop
```

With no GTK installed (a bare macOS, say), `meson setup build -Dgui=disabled` still builds
and tests the core. json-glib is fetched from its wrap when the system has none.

On macOS, Homebrew provides everything:
`brew install $(python3 ../../scripts/macos_app_bundle.py brew-packages)`. The app that
build makes runs against Homebrew. A self-contained `krypton.app` in a `.dmg`, the one each
release attaches, is made from it by `scripts/macos_app_bundle.py` (see
[PACKAGING.md](PACKAGING.md#macos)). On macOS, discovery finds hubs over Bonjour.

| Option | Default | Meaning |
|---|---|---|
| `-Dchannel=stable\|nightly` | `stable` | Nightly installs beside stable, as "krypton nightly" with its own app id and data directory. |
| `-Dgui=` | `auto` | Build the GTK app, not only the core. |
| `-Dhub_transport=` | `auto` | The libsoup hub client. |
| `-Ddiscovery=` | `auto` | Avahi or dns_sd. |

## How it is built

- **`src/core/`: libkryptondesktop, pure C with no GTK.** Each module is a header, its
  interface, and a `.c`, which is ADR-0016 in C:
  - `kr-model`: the hub's documents as structs;
  - `kr-hub` and `kr-hub-client`: routes, the token, a paired device's request signature,
    the certificate pin and the libsoup transport;
  - `kr-answer`: which answer each gate kind takes, mirroring `src/vibey/cli/gate_answers.py`;
  - `kr-state`: what the app knows, and which gates are new;
  - `kr-format`: money, durations and phases in words;
  - `kr-settings`: themes and channels;
  - `kr-pairing` and `kr-pairing-client`: the pairing code and address, the claim, the
    device's key and where it is kept;
  - `kr-discovery`, with its Avahi and dns_sd backends;
  - `kr-workflows` and `kr-workflows-client`: a command run on the repository's GitHub-hosted
    runners through the hub (`/api/v1/workflows/runs`): the typed command line in words, the
    request, the run in each state, every refusal in words, and the poller that follows a run
    to its end (every 10 s, for up to 60 minutes, cancellable).
- **`src/app/`: thin GTK views.** They read the state and redraw the slice that changed.
  Colours come from the design tokens (ADR-0066): `design/dist/c/vibey_tokens.h` for the
  mark, and the generated `design/dist/gtk` stylesheets, which libadwaita loads as the
  app's `style.css` and `style-dark.css`.
- **`tests/`: GLib tests over the core.** They include the hub client against a real
  loopback HTTP server, and pairing over real TLS with a certificate made at build time
  (openssl) and pinned. HTTPS needs GIO's TLS backend, glib-networking. The CI job `desktop` builds everything with `-Werror` under ASan
  and UBSan on Ubuntu, Arch and macOS, and gates the core's coverage with gcovr. On macOS
  it also bundles the app and runs it with Homebrew unreadable.

Every release attaches a Flatpak bundle, an Ubuntu build and a macOS `.dmg`
([downloads](../../docs/guides/downloads.md)). No store carries krypton yet. See
[PACKAGING.md](PACKAGING.md).
