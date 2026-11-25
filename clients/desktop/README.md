---
description: "Reference for krypton desktop, vibey's C and GTK 4 app for macOS and Linux: install, what each page does, shortcuts, pairing, and how to build it."
---

# krypton desktop

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** krypton desktop is vibey's desktop app for macOS 15+ on Apple
> silicon and for Linux, written in C17 on GTK 4 and libadwaita. It opens on **Chat** (`Ctrl+L`),
> starts this computer's vibey hub for you, and shows projects, gates, lanes, budgets and devices.
> Install vibey first, then the `.dmg`, Flatpak or Ubuntu tarball from GitHub Releases. It talks
> only to the hub, never to vibey's database.

> [!IMPORTANT]
> **Work in progress — not a final product:** `krypton desktop` is actively being developed and is not a final product. Features, UI, and packages are still evolving. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.

## How to read this page

Daniel had installed the app and pressed `Cmd+L` on his Mac. Nothing happened.

**Daniel:** Professor, the page I read said Command-L.

**Professor Feynman:** Then the page was wrong, and that is worth knowing. Every shortcut here is
the Control key, on a Mac as well; the table that sets them is one C file, and this page is
checked against it. Install first, using the steps below. The tables after that are for looking
things up when you need them.

## Install

First, make sure the `vibey` engine is installed on your computer:

```bash
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
```

The hub that krypton starts reads vibey's database, so PostgreSQL and `VIBEY_PG_URL` must be set
up too; the [install guide](../../docs/guides/install.md) walks through it. Then pick your
operating system:

- **macOS 15 Sequoia and newer (Apple silicon M1/M2/M3/M4/M5):**
  1. Download **`krypton-desktop-<version>-macos-arm64.dmg`** from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) (or [krypton-nightly](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly)).
  2. Double-click the `.dmg` and drag **krypton** into **Applications** (no Homebrew or extra libraries needed).
  3. Clear macOS Gatekeeper's quarantine flag in Terminal (the `.dmg` is ad-hoc signed while the project's Developer ID signing and notarisation secrets are absent):
     ```bash
     xattr -dr com.apple.quarantine /Applications/krypton.app
     ```
     *(Or open **krypton** once, then click **Open Anyway** in **System Settings → Privacy & Security**.)*
  4. Launch **krypton** from **Applications** or Spotlight. It opens straight into **Chat** (`Ctrl+L`) and starts your local hub automatically.
- **Linux, any distribution with Flatpak** (CI builds and tests the app on Ubuntu, Arch and Fedora; other distributions are not tested):
  1. Download **`krypton-desktop-<version>-linux-x86_64.flatpak`** (or `aarch64`) from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases).
  2. Install and run:
     ```bash
     flatpak install --user ~/Downloads/krypton-desktop-*-linux-*.flatpak
     flatpak run io.github.the_vibey_project.krypton
     ```
- **Linux, Ubuntu 24.04 LTS and newer (native `.tar.gz`):**
  1. Download **`krypton-desktop-<version>-linux-x86_64.tar.gz`** (or `aarch64`) from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases).
  2. Install the system GTK 4 / libadwaita dependencies and unpack into `/`:
     ```bash
     sudo apt update && sudo apt install -y libgtk-4-1 libadwaita-1-0 libsoup-3.0-0 libjson-glib-1.0-0 libavahi-client3 libavahi-glib1 glib-networking
     sudo tar -xzf ~/Downloads/krypton-desktop-*-linux-*.tar.gz -C /
     krypton-desktop
     ```

Want the other krypton interfaces too (VS Code, web, Android, iOS, or `vibey connect` for Claude
Code and Codex)? See [docs/guides/install.md](../../docs/guides/install.md) and
[docs/guides/downloads.md](../../docs/guides/downloads.md).

The desktop app talks to a vibey hub (`vibey serve`, [ADR-0068](../../docs/architecture/decisions/0068-the-hub.md))
over the [hub API](../../docs/reference/hub-api.md). It never touches vibey's database.

## What it shows

| Place | What you get |
|---|---|
| Chat | **The landing page** (`Ctrl+L`), mirroring the Claude Code and Codex desktop apps ([ADR-0100](../../docs/architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces.md)): a session sidebar of every project (plus an *All projects* overview), a conversation transcript of your turns (`POST /api/v1/chat/messages`) with expandable tool-call cards and live ledger narration (`GET /api/v1/projects/{id}/ledger/after`), inline approval cards for waiting gates (with `SPEND GATE` clearly badged whenever answering requires the `spend` scope), quick-action chips, and a bottom composer with `/` slash-command completion (`/projects`, `/status`, `/gates`, `/answer`, `/budget`, `/queue`, `/ledger`, `/loops`, `/lanes`, `/doctor`, `/new`, `/start`, `/pause`, `/abandon`, `/help`). |
| Projects | Every project, its phase and cycle, and how many gates wait on it. **Start a project** (the `+` button or `Ctrl+N`) asks for a name and what to build; each row's menu starts or pauses that project's own worker, or **unwinds** it after a dry run says what it would cancel and that the work on disk stays ([ADR-0091](../../docs/architecture/decisions/0091-devices-may-start-pause-and-unwind-projects.md)). The hub makes the folder; the desktop never names a path. |
| Gates | Every gate waiting on you, with the controls its kind takes: a verdict or choice as buttons, a new bound for a grant, a retry, or a free-form answer. It warns you before an answer that can spend money. A desktop notification tells you when a new gate is raised. |
| Lanes | The lanes running on the hub's computer. The krypton mark in the sidebar glows while one runs. |
| Loops and effort | The loops, their engines and the effort ladder, up to ULTRA. |
| Budgets | What the chosen project has spent this cycle, against its caps. |
| Doctor | The checks the hub runs itself. |
| Run on GitHub | A vibey command run on the repository's GitHub-hosted runners, as `vibey -w` runs it ([ADR-0085](../../docs/architecture/decisions/0085-vibey-on-the-workflows.md)). Type the command as it would follow `vibey -w` (`status --json`; double quotes keep spaces), and krypton sends it through the hub, asks every ten seconds where it is (queued, running, done or failed) for up to an hour, links its GitHub run, and shows its exit code and what it printed, selectable, in monospace. The paired device needs the `workflows` scope, and the scopes of what the command itself does; a hub with the workflows switched off, or a command the hub never runs (`migrate`, `budget set`), is said as such. |
| Devices | Hubs found on your network (`_vibey._tcp`) with the certificate each advertises, this computer's hub, the hub this device is paired with and each scope it holds, in words, and pairing by the host's 6-digit code or its `vibey-pair://` address. |
| Settings | Light, Dark or System (the default, which follows your desktop live), notifications, sounds, starting this computer's hub automatically (on by default), buttons to start, stop and check that hub, and, where the platform has one, keeping krypton running in the tray. |

The header menu holds Start a project, the hub's Start, Stop and Status, Refresh, Preferences, **Keyboard shortcuts**, **About krypton** and Quit. Every command, its label and its keys come from one table (`src/core/kr-commands.c`), so the menu, the shortcuts dialog and the keys cannot disagree. Screen-reader support, and what has and has not been checked with one, is in [ACCESSIBILITY.md](ACCESSIBILITY.md).

**The tray item** (the menu bar on macOS, a StatusNotifierItem elsewhere) shows how many gates wait on you, opens the window, jumps to Gates, starts a project and quits. While it is showing, closing the window hides it instead; if no tray is there to bring it back (GNOME needs the AppIndicator extension), the window closes as a window does. Turn it off in Settings.

### Keyboard shortcuts

Every shortcut uses the Control key, on macOS as well as Linux (`src/core/kr-commands.c`).

| Keys | Command |
|---|---|
| `Ctrl+L` | Open Chat and focus the composer |
| `Ctrl+N` | Start a project |
| `Ctrl+R` or `F5` | Refresh |
| `Ctrl+G` | Answer waiting gates |
| `Ctrl+,` | Preferences (Settings) |
| `Ctrl+?` | List every shortcut |
| `Ctrl+Q` | Quit |

On a narrow window the sidebar folds into one pane with back navigation.

## Connecting

**The hub on this computer is started for you.** There is one hub per user (`vibey serve`
takes a lock, so a second refuses), and closing krypton never stops it. When krypton opens
pointed at *This computer* and no hub runs, it runs `vibey hub start` in the background
(a worker thread; the window never waits on it), then connects. A failure is a note in the
connection status, never a pop-up. Start, Stop and Status are in the header menu, on the
Settings page and, while the tray is showing, in the tray menu (Start when no hub answers,
Stop while one does); they are the only way krypton stops the hub, and quitting is not one.
Turn the automatic start off in Settings (`[hub] autostart=false` in the settings file). With
another computer's hub chosen, krypton starts nothing: the hub there is started and stopped
on that computer (`vibey hub start | stop`).

krypton finds `vibey` on `PATH`, then in `~/.local/bin`, `/opt/homebrew/bin` and
`/usr/local/bin` (a launch from the Dock has a short `PATH`); `KRYPTON_VIBEY` names one
explicitly. It runs the commands from your home directory, so a `vibey.toml` in a project
folder cannot redirect them. It needs a `vibey` that has `vibey hub start | stop | status`,
and says to upgrade when it does not.

On the computer that runs the hub, krypton reads the hub's token the way the hub keeps it:
`~/.local/state/vibey/hub/token` on Linux, `~/Library/Application Support/vibey/hub/token`
on macOS, or `$VIBEY_HUB_STATE_DIR/token`. The file must be yours alone (mode 0600) and
not a symlink, or krypton refuses it, just as the hub does.

### Pairing with a hub on another computer

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

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| macOS says krypton "cannot be opened" or is damaged | Gatekeeper's quarantine flag on an app that is not notarised. | `xattr -dr com.apple.quarantine /Applications/krypton.app`, or **Open Anyway** in Privacy & Security. |
| The connection status notes that the hub could not be started | `vibey hub start` failed, or no `vibey` was found on the short `PATH` a Dock launch gets. | Run `vibey hub start` in a terminal to see why; set `KRYPTON_VIBEY` to the full path of `vibey` if it lives somewhere krypton does not look. |
| krypton says to upgrade vibey | The installed `vibey` has no `vibey hub start \| stop \| status`. | Re-run the install command at the top of this page. |
| krypton refuses the hub's token | The token file is not mode 0600, or it is a symlink. | `chmod 600` the token file named under [Connecting](#connecting). |
| A typed pairing code is refused for a hub on another computer | krypton does not know that hub's certificate. | Paste the whole `vibey-pair://` address `vibey hub pair` printed. |
| Closing the window does not quit | The tray item is showing, so closing hides the window. | Quit from the tray or `Ctrl+Q`, or turn the tray off in Settings. |

## Building

You need Meson 1.1 or newer, GLib 2.74, json-glib, libsoup 3, GTK 4.12 and libadwaita 1.5,
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

Build options (`meson_options.txt`):

| Option | Default | Meaning |
|---|---|---|
| `-Dchannel=stable\|nightly` | `stable` | Nightly installs beside stable, as "krypton nightly" with its own app id and data directory. |
| `-Dgui=` | `auto` | Build the GTK app, not only the core. |
| `-Dhub_transport=` | `auto` | The libsoup hub client. |
| `-Ddiscovery=` | `auto` | Avahi or dns_sd. |
| `-Dtray=auto\|macos\|sni\|none` | `auto` | The tray item: the macOS menu bar, the freedesktop StatusNotifierItem, or none. `auto` picks `macos` on macOS and `sni` elsewhere. |

## How it is built

- **`src/core/`: libkryptondesktop, pure C with no GTK.** Each module is a header, its
  interface, and a `.c`, which is ADR-0016 in C:
  - `kr-model`: the hub's documents as structs;
  - `kr-chat`: the `/` slash-command catalogue and completion, `POST /api/v1/chat/messages`
    request and turn parser, spend-gate badge helper, and live ledger narration parser;
  - `kr-commands`: the one table of commands, labels and keyboard accelerators;
  - `kr-hub` and `kr-hub-client`: routes, the token, a paired device's request signature,
    the certificate pin and the libsoup transport;
  - `kr-answer`: which answer each gate kind takes, mirroring `src/vibey/cli/gate_answers.py`;
  - `kr-state`: what the app knows, and which gates are new;
  - `kr-format`: money, durations and phases in words;
  - `kr-settings`: themes, channels and whether the hub starts with krypton;
  - `kr-hub-engine`: `vibey hub status | start | stop` through `GSubprocess` (never a shell), on
    a worker thread, and the words for a hub that does not answer;
  - `kr-lifecycle`: starting, pausing, resuming and unwinding a project from a device
    (ADR-0091): the name a project may have, the request bodies, the answers, and the words
    before an unwind;
  - `kr-tray`: what the tray item shows and offers, as plain data; the platform shims in
    `src/app/` only draw it;
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
  and UBSan on Ubuntu, Arch, Fedora and macOS, and gates the core's coverage with gcovr. On macOS
  it also bundles the app and runs it with Homebrew unreadable.

Every release attaches a Flatpak bundle, an Ubuntu build and a macOS `.dmg`
([downloads](../../docs/guides/downloads.md)). No store carries krypton yet. See
[PACKAGING.md](PACKAGING.md).

## Where next

- [ADR-0073](../../docs/architecture/decisions/0073-krypton-desktop-in-c-on-gtk.md): why the desktop
  app is C on GTK.
- [ADR-0071](../../docs/architecture/decisions/0071-hub-pairing-and-trust.md): how pairing and trust
  work.
- [PACKAGING.md](PACKAGING.md): how the Flatpak, tarball and `.dmg` are made.

## Say it in one line

krypton desktop is vibey's native app for macOS and Linux: it starts your local hub, opens on
Chat with Ctrl+L, and pairs with a hub elsewhere only by a code you can check.
