---
description: Install vibey with one command on macOS or Linux, set up what it needs by hand if you prefer, add any krypton app, read what vibey doctor reports, and reinstall, copy or remove it.
---

# Install vibey, reinstall it, copy it, or remove the apps

<!-- standard-block:install:start -->
> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** One command installs vibey and gets a new macOS or Linux
> machine ready to run a first project on your own hardware. About 15 minutes, plus the model
> download of roughly 12 GB.
>
> ```bash
> curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --full
> ```
>
> It installs `uv` and Python if you lack them, then vibey with its hub, PostgreSQL, a local
> database, Ollama, the default model, and the connection to your editors, and ends by running
> `vibey doctor`. Each step is announced first and can be skipped (`VIBEY_FULL_POSTGRES=0`,
> `VIBEY_FULL_DATABASE=0`, `VIBEY_FULL_OLLAMA=0`, `VIBEY_FULL_MODEL=0`, `VIBEY_FULL_CONNECT=0`).
> On Linux it asks for your sudo password, and on macOS it needs Homebrew. Run it again to repair
> an install.
>
> **Afterwards, two things are yours:** add the `export VIBEY_PG_URL=...` line it prints to your
> shell profile, and require `scram-sha-256` in `pg_hba.conf` (`vibey doctor` says so until you do).
> Without `--full`, the same command installs only vibey, and `vibey doctor` lists what is missing.
<!-- standard-block:install:end -->

<!-- remove-after-release:start -->
**Until the next release:** `--full` works from the release that follows pull request #1978. Until then the script refuses it as an unknown option; use [the manual path](#without-full-the-manual-path).
<!-- remove-after-release:end -->

This page is for anyone putting vibey on a Mac or a Linux computer, and for anyone adding one of
the krypton apps: the desktop app, the editor extension, the phone app or the browser launcher.
vibey is at version 0.4.0 and held below 1.0, so commands can still change between releases.
Windows is not supported.

**Checked on** macOS against the vibey-engine 0.4.0 source on `develop` (2026-11-24). The
engine-only install was run end to end in a throwaway home folder. The `--full` steps were read
from the script on the branch for #1978 and its tests; they were not run on a fresh machine here.

## The lesson

Daniel had a new laptop open on the bench and a cup of tea going cold beside it.

**Daniel:** Professor, the page says one command. One command for a database, a model and an
engine? That sounds too good.

**Professor Feynman:** Think of moving into a new flat. The removal van brings your furniture.
That is one trip. But the flat also needs the water switched on, the electricity connected and
the post redirected. A good removal firm can arrange all of those for you, if you tick the boxes,
and each one is still a separate job with its own people.

**Daniel:** So the plain command is the van, and `--full` is ticking every box.

**Professor Feynman:** Yes. Without `--full`, the script installs vibey's programs and stops. With
it, the script then runs vibey's own setup commands, one at a time, and tells you each one before
it starts: PostgreSQL, the database, Ollama, the model, and the connection to your chat tools.

**Daniel:** And if one of them fails halfway?

**Professor Feynman:** It stops at that job, says which one, and prints the command that does
that job alone. Run the whole thing again and the jobs already done are left as they are.

**Daniel:** Then why does the page say two things are still mine?

**Professor Feynman:** Because they are about your house rules, not the furniture. Your shell
profile is yours: vibey prints the line, and you decide to keep it. And `pg_hba.conf` is the
lock on the database's front door. vibey will not change a lock it did not fit. That is where my
picture stops working: a removal firm might change your locks if you asked, and vibey never does.
`vibey doctor` keeps saying so until you have.

## Do it

1. **Open a terminal.** On a Mac, hold **Command (⌘)**, press **Space**, type `Terminal` and
   press **Return**. On Linux, press the **Super** key, type `Terminal` and press **Enter**.

2. **Run the one command.**

   ```bash
   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --full
   ```

   You should see each step announced before it runs: installing `vibey-engine[hub]`, then
   "Installing and starting PostgreSQL", "Making the database, its two roles and its
   migrations", Ollama, "Pulling ... into Ollama, roughly 12 GB", and "Plugging vibey into your
   chat and IDE clients". It ends with the `vibey doctor` report, the line `vibey is installed.`
   and a list headed `Still yours to do:`.

3. **Keep the database line.** Copy the `export VIBEY_PG_URL=...` line from `Still yours to do:`
   into `~/.zshrc` (macOS) or `~/.bashrc` (most Linux), then open a new terminal. It looks like
   this, with no password in it (the passwords are in `~/.pgpass`, readable by you alone):

   ```bash
   export VIBEY_PG_URL=postgresql://vibey_app@localhost:5432/vibey
   ```

4. **Lock the database's front door.** Require `scram-sha-256` for every connection in
   PostgreSQL's `pg_hba.conf`. The exact lines are in
   [SECURITY.md, section 7](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md).
   Restart PostgreSQL afterwards.

5. **Check the result.**

   ```bash
   vibey doctor
   ```

   You should see one line per check. Read it with [the doctor table](#read-what-vibey-doctor-says)
   below: a `FAIL` on a local check needs you; a `FAIL` on a paid engine's login does not, unless
   you want that engine.

6. **Use it.** Drive vibey from Claude Code or another chat tool with
   [Let another LLM drive vibey](drive-from-an-llm.md), or from a terminal or an app with
   [Drive a project from anywhere](drive-a-project.md).

## Daniel's teach-back

**Daniel:** The one command always installs vibey's programs, and `uv` and Python if they are
missing. With `--full` it also runs vibey's own setup commands in order: PostgreSQL, the
database, Ollama, the model, and `vibey connect`. Each step can be switched off with its
`VIBEY_FULL_*=0` switch, a failure stops the run and names the command to repeat, and running it
again is safe. Two things stay with me: keeping the `VIBEY_PG_URL` line, and the
`scram-sha-256` lines in `pg_hba.conf`.

**Professor Feynman:** All correct. One addition: `vibey doctor` runs at the end every time, so
the last screen is always the honest list of what is still missing.

## The details

### What `--full` runs, in order

Each step is announced, run with no input from the pipe, and on failure stops the whole run with
the command that repeats it alone. Every step is safe to run twice.

| Step | What it runs | Skip it with | Notes |
|---|---|---|---|
| PostgreSQL | `vibey install --postgres` | `VIBEY_FULL_POSTGRES=0` | Homebrew installs and starts `postgresql@18`. `apt-get` and `dnf` install the distribution's own PostgreSQL through `sudo`, so it asks for your password. Arch's `pacman` is not supported: install PostgreSQL 14 or newer yourself. |
| Database | `vibey install --database` | `VIBEY_FULL_DATABASE=0` | Makes the database `vibey`, its owner role `vibey` and its application role `vibey_app`, keeps their random passwords in `~/.pgpass` (never printed), applies the migrations and prints the `export VIBEY_PG_URL=` line. A role `~/.pgpass` holds no password for, or a database another role owns, is refused rather than taken over. |
| Migrations | `vibey migrate` | `VIBEY_FULL_MIGRATE=0` | Runs only when you skipped the database step and set `VIBEY_PG_MIGRATE_URL` for a database of your own. Otherwise the database step already migrated. |
| Ollama | macOS: `brew install ollama` and `brew services start ollama`. Linux: Ollama's own installer, downloaded first and then run | `VIBEY_FULL_OLLAMA=0` | Skipped when `ollama` is already on your `PATH`. On a Mac without Homebrew it stops and points you at https://ollama.com/download. |
| Model | `vibey install --model` | `VIBEY_FULL_MODEL=0` | Pulls the tag `vibey models --default-tag` prints: the heretic v2 build of GPT-OSS 20B, `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`, 12.1 GB ([ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)). It pulls nothing when the model is there. |
| Clients | `vibey connect --yes` | `VIBEY_FULL_CONNECT=0` | Writes vibey into every chat and editor client it knows. `VIBEY_FULL_CONNECT_CLIENTS="claude_code zed"` limits it to those. Claude Code and VS Code entries go into the folder you ran the installer from. |

When the step needs `sudo` and there is no terminal to ask on, it stops and tells you what to run
instead. `vibey install --database`, `vibey install --model` and `vibey models --default-tag`
ship in the same release as `--full`.

### Every option and switch the installer reads

| Option or variable | Default | What it does |
|---|---|---|
| `--full` | off | Runs the setup steps above after installing. |
| `--with-krypton` | off | Also installs `krypton-app`, which gives you the `krypton` browser launcher. |
| `--from-source DIR` | none | Clones the whole repository into `DIR` (or updates it with `git pull --ff-only`), builds it with `uv sync --extra dev`, and installs the commands from that copy. |
| `--help` | | Prints the usage. Piped through `curl` it works from the release after #1978; before that, run it on a downloaded copy (`sh install.sh --help`). |
| `VIBEY_ENGINE_EXTRAS` | `hub` | The engine's extras. `hub` carries what `vibey serve`, `vibey hub` and the hub `vibey mcp` starts need. Set it empty for the bare engine. From the release after #1978. |
| `VIBEY_ENGINE_PACKAGE` | `vibey-engine` | The package to install. `VIBEY_ENGINE_PACKAGE='vibey-engine==0.4.0'` pins a version. |
| `VIBEY_APPS_PACKAGE` | `krypton-app` | The apps package `--with-krypton` installs. |
| `VIBEY_REPOSITORY` | `https://github.com/the-vibey-project/vibey.git` | What `--from-source` clones. |
| `VIBEY_UV_INSTALLER` | `https://astral.sh/uv/install.sh` | Where `uv` comes from when it is missing. |
| `VIBEY_OLLAMA_INSTALLER` | `https://ollama.com/install.sh` | Ollama's installer on Linux. |
| `VIBEY_FULL_POSTGRES`, `_DATABASE`, `_MIGRATE`, `_OLLAMA`, `_MODEL`, `_CONNECT` | `1` each | `0` skips that step. |
| `VIBEY_FULL_CONNECT_CLIENTS` | every client | Client ids for `vibey connect --client`, separated by spaces or commas. |
| `VIBEY_TTY` | `/dev/tty` | Where a password prompt is read from, since a piped script's input is the script itself. |
| `VIBEY_KRYPTON_UNINSTALLER` | the uninstaller's URL on `main` | The address the closing message names for removing the krypton apps. |

The script needs no Python of its own: `uv` downloads Python 3.12 when none is on your `PATH`.
It installs into `uv`'s tool folder (usually `~/.local/bin`). Every run is a reinstall
(`uv tool install --reinstall`), so it replaces all of vibey's dependencies each time: slower
than an upgrade, and exactly what repairs a broken install
([ADR-0082](../architecture/decisions/0082-install-copy-reinstall-and-a-core-that-stays.md)).

The engine package installs these commands: `vibey`, `claudeloop`, `codexloop`, `gptossloop`,
`qwenloop`, `vibey-gh`, `vibey-skills`, `vibe-skills`, `vibey-bootstrap` and `azbootstrap`. That
is four `*loop` runners; `claudeloop-local` is a profile of `claudeloop`, not a command, and
`cursorloop` and `agyloop` were retired by
[ADR-0078](../architecture/decisions/0078-retire-cursorloop-and-agyloop.md).

### Without `--full`: the manual path { #without-full-the-manual-path }

The same command without `--full` installs only vibey. Then do the rest yourself, in this order.

1. **Install vibey.**

   ```bash
   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh
   ```

   <!-- remove-after-release:start -->
   On the current release this installs the bare engine. The hub needs its `hub` extra, so add
   it (the release after #1978 does this by default):

   ```bash
   uv tool install --reinstall 'vibey-engine[hub]'
   ```
   <!-- remove-after-release:end -->

2. **PostgreSQL 14 or newer.** Use your own, or let vibey install it:

   ```bash
   vibey install --postgres
   ```

   `vibey doctor --install-postgres` does the same when PostgreSQL is missing or stopped.

3. **The database, its two roles and the migrations.**

   ```bash
   vibey install --database
   ```

   It prints the `export VIBEY_PG_URL=...` line to keep and the one-command form of
   `vibey migrate` for later upgrades. Options: `--db-name` (default `vibey`), `--owner-role`
   (`vibey`), `--app-role` (`vibey_app`), `--admin-user` (you with Homebrew, `postgres` through
   `sudo` with `apt-get` or `dnf`).

   <!-- remove-after-release:start -->
   On the current release `vibey install --database` does not exist yet. Create the database with
   PostgreSQL's own `createdb` as an owner role, then let `vibey migrate` create the application
   role and grant it exactly what it needs, giving the owner's address to that one command only
   ([database roles](../reference/configuration.md#database-roles)):

   ```bash
   VIBEY_PG_MIGRATE_URL=postgresql://OWNER@localhost:5432/vibey \
   VIBEY_PG_URL=postgresql://vibey_app:PASSWORD@localhost:5432/vibey \
   vibey migrate
   ```

   Replace `OWNER` with the role that owns the database and `PASSWORD` with a new password of
   your choosing. You should see `ledger guard in force`.
   <!-- remove-after-release:end -->

4. **Keep `VIBEY_PG_URL`** in your shell profile, and require `scram-sha-256` in `pg_hba.conf`
   ([SECURITY.md, section 7](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md)).

5. **Ollama.** On macOS, install the app from https://ollama.com/download and open it once, or
   run `brew install ollama` and `brew services start ollama`. On Linux, run Ollama's installer:

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

6. **The model.**

   ```bash
   vibey install --model
   ```

   <!-- remove-after-release:start -->
   On the current release, pull it with Ollama directly:

   ```bash
   ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE
   ```
   <!-- remove-after-release:end -->

   The stock `gpt-oss:20b` is the opt-in alternative (`VIBEY_SOVEREIGN_MODEL=stock`); see
   [Local models on Ollama](local-models-ollama.md).

7. **Connect your chat and editor clients** (optional), from the folder you will work in:

   ```bash
   vibey connect --yes
   ```

   [Let another LLM drive vibey](drive-from-an-llm.md) explains what this writes and where.

8. **Optional extras.** `vibey searxng install` runs a local search engine so the local model's
   research can search the web ([ADR-0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md)).
   `vibey supervisor install` writes service files that keep the worker running across reboots
   and prints the command that loads them; it never loads them itself. Paid engines are
   optional: `claudeloop` needs you signed in to Claude, and `codexloop` needs the `codex`
   program installed and signed in.

### Install with `uv` directly

```bash
uv tool install 'vibey-engine[hub]'
uv tool install krypton-app
```

`krypton-app` already pulls in `vibey-engine[hub]` inside its own tool folder. `pip` and `pipx`
can install the same packages but are not tested
([system requirements](../reference/system-requirements.md)); those need Python 3.12 or newer.

### Read what `vibey doctor` says { #read-what-vibey-doctor-says }

`vibey doctor` checks this machine and prints one line per check, marked `PASS`, `WARN`, `FAIL`
or `UNKNOWN`. It exits 1 only when a local check fails (for example the database's
authentication, or a hub listening where `vibey.toml` does not allow), or with `--conformance`
when an engine fails it. A paid engine that is not signed in shows `FAIL` and does not change the
exit code. `vibey doctor --json` prints the same as one JSON document.

| What you see | What it means | What to do |
|---|---|---|
| `gptossloop ... auth FAIL ... model ... is not served ...; pull it first` | Ollama answers, but the default model is not in it. | `vibey install --model`, or the `ollama pull` line it names. |
| `postgresql NOT INSTALLED` | No PostgreSQL client tools on your `PATH`. | `vibey install --postgres`. |
| `UNKNOWN ledger-guard`, `db-passwordless`, `gate-notices` with `VIBEY_PG_URL is not set` | The database checks cannot run. | Export the `VIBEY_PG_URL` line, open a new terminal, run it again. |
| `FAIL local-auth` | PostgreSQL still accepts connections without `scram-sha-256`. | Add the `pg_hba.conf` lines from SECURITY.md section 7 and restart PostgreSQL. |
| `claudeloop ... auth FAIL ... no credentials found` | Claude's command line is bundled but not signed in. | Only if you want the paid engine: sign in to Claude. |
| `codexloop ... codex-cli: codex not found` | The Codex program is not installed. | Only if you want the paid engine: install `codex` and run `codex login`. |
| `WARN supervisor-worker` | No service keeps a worker running across reboots. | Optional: `vibey supervisor install`. |
| `WARN claude_code:mcp-server missing ...` (the `llm-tooling` section) | That client has no vibey entry in this folder. | Run the `vibey connect --client ...` command it names. |
| A Sabbath line | From sundown Friday to sundown Saturday, where your machine is, vibey starts no new work by default. | See [The Sabbath](sabbath.md). |

### The krypton apps, platform by platform { #the-krypton-apps-platform-by-platform }

Every ready-built file is attached to each release on
[GitHub Releases](https://github.com/the-vibey-project/vibey/releases), and rebuilt nightly on
[`krypton-nightly`](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly).
[Downloads](downloads.md) lists every file, its signing, and how to check it. Every app talks to
the **hub** (`vibey serve`), so each one needs vibey with its hub, PostgreSQL and `VIBEY_PG_URL`
on the computer that runs the hub.

| Platform | App | Install it |
|---|---|---|
| macOS 15 or newer, Apple silicon | krypton desktop | Download `krypton-desktop-<version>-macos-arm64.dmg`, open it, drag **krypton** to **Applications**. It is ad-hoc signed and not notarised, so clear the quarantine flag once with `xattr -dr com.apple.quarantine /Applications/krypton.app`, or open it once and choose **Open Anyway** in **System Settings → Privacy & Security**. It needs no Homebrew. |
| Ubuntu 24.04 or newer | krypton desktop | Install the libraries, then unpack the tarball into `/`:<br>`sudo apt update && sudo apt install -y libgtk-4-1 libadwaita-1-0 libsoup-3.0-0 libjson-glib-1.0-0 libavahi-client3 libavahi-glib1 glib-networking`<br>`sudo tar -xzf ~/Downloads/krypton-desktop-<version>-linux-x86_64.tar.gz -C /` (or `aarch64`)<br>Launch with `krypton-desktop`. |
| Any Linux with Flatpak (Ubuntu, Fedora, Arch and others) | krypton desktop | `flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo`<br>`flatpak install --user ~/Downloads/krypton-desktop-<version>-linux-x86_64.flatpak` (or `aarch64`)<br>Launch with `flatpak run io.github.the_vibey_project.krypton`. The Flatpak cannot find hubs on the network by itself; pair it by pasting the `vibey-pair://` address `vibey hub pair` prints. |
| Fedora | krypton desktop | The Flatpak above, or build from `clients/desktop/packaging/fedora/krypton-desktop.spec` (needs `meson ninja-build gcc pkgconf-pkg-config gtk4-devel libadwaita-devel libsoup3-devel json-glib-devel avahi-devel avahi-glib-devel glib-networking`). |
| Arch | krypton desktop | The Flatpak above, or build from `clients/desktop/packaging/arch/PKGBUILD`, or install `meson ninja gcc pkgconf gtk4 libadwaita libsoup3 json-glib avahi glib-networking` and run `meson setup build clients/desktop && meson compile -C build && ./build/src/app/krypton-desktop` from a copy of the repository. |
| VS Code (macOS, Linux) | krypton for VS Code | Download `krypton-vscode-<version>.vsix`, then `code --install-extension ~/Downloads/krypton-vscode-<version>.vsix`, or **Extensions → `…` → Install from VSIX…**. |
| VSCodium | krypton for VS Code | From Open VSX: `codium --install-extension the-vibey-project.krypton`. |
| Cursor | krypton for VS Code | `cursor --install-extension ~/Downloads/krypton-vscode-<version>.vsix`, or **Install from VSIX…**. |
| Android | krypton app | Open the release page on the phone, download `krypton-android-<version>.apk`, allow **Install unknown apps** for your browser or Files app, and install. Or from a computer: `adb install ~/Downloads/krypton-android-<version>.apk`. It is signed with Android's debug key: sideload only. |
| iOS | krypton app | The release's `krypton-ios-<version>.ipa` (built only while the project's `EXPO_TOKEN` is set) is the file App Store Connect takes. It does not install by opening it, and the release workflow submits it nowhere, so there is no TestFlight or App Store listing to install from. To run it on an iPhone today you need a copy of the repository and Node: `cd clients/app && npm ci && npx expo start`, then scan the QR code with the Camera app to open it in **Expo Go**. |
| Any browser | krypton web app | Not usable against a hub today: see [the web app](#the-web-app). |
| macOS, Linux | `krypton` browser launcher | `--with-krypton` on the install command, or `uv tool install krypton-app`. See below. |

The editor extension has its own guide: [VS Code extension](vscode-extension.md). The desktop
app's full guide is its
[README](https://github.com/the-vibey-project/vibey/blob/develop/clients/desktop/README.md).
The desktop app and the VS Code extension start the hub on this computer for you
(`vibey hub start`), using the `vibey` they find on this computer.

### The `krypton` browser launcher

```bash
krypton
```

It runs `vibey serve` on `http://127.0.0.1:8765/`, waits until it answers, opens that address in
your browser, and stays in the foreground: press **Ctrl+C** to stop the hub. The page it opens is
the hub's front door. It says the hub is running and where to go next, and it holds no data and
asks for no key. Options: `--host` (default `127.0.0.1`), `--port` (default `8765`),
`--no-browser`, and `--vibey PATH` (default: the `vibey` installed beside `krypton`, else the one
on your `PATH`). The hub needs `VIBEY_PG_URL` in the terminal you start it from.

For a hub that keeps running after you close the terminal, use `vibey hub start` instead: it
starts the hub in the background, does nothing if one already runs, and `vibey hub stop` stops
it.

### Phone and tablet { #phone-and-tablet }

The hub keeps every device out until you pair it. Pairing is how a device proves it is yours:
being on the same Wi-Fi proves nothing.

What exists on the computer side:

1. In your own `vibey.toml` (macOS `~/Library/Application Support/vibey/vibey.toml`, Linux
   `~/.config/vibey/vibey.toml`), declare that the hub may leave this computer, and where
   devices may start projects:

   ```toml
   [hub]
   lan = true
   projects_root = "~/vibey-projects"
   ```

2. Run the hub on your computer's network address, which serves its own certificate. `lan = true`
   alone does not open the network; the address on the command line does. `vibey serve` reads the
   `vibey.toml` of the folder it runs in, so run it from that folder (macOS shown; on Linux,
   `cd ~/.config/vibey`), in a terminal where `VIBEY_PG_URL` is exported. It stays in the
   foreground; stop any `vibey hub start` hub first with `vibey hub stop`.

   ```bash
   cd ~/Library/Application\ Support/vibey
   vibey serve --host 192.168.1.20
   ```

   Replace `192.168.1.20` with your computer's address on your network.

3. Offer a pairing, naming what the device may do (at least one scope; a pairing grants nothing
   by default):

   ```bash
   vibey hub pair --host 192.168.1.20 --scope view --scope answer --scope run
   ```

   You should see a QR code, then `code:` with six digits (valid once, for two minutes),
   `scopes:`, `uri:` and the certificate's fingerprint. The scopes are `view`, `answer`, `run`,
   `spend` and `bump`.

What happens on the phone: the app opens on its **Pair** screen ("Welcome to krypton"), with
**Scan the QR code**, **Type the 6-digit code**, and **Connect with a host token**. In this
version of the app, scanning and typing the code are refused with "This hub cannot pair devices
yet: its pairing routes are still being built" (`clients/app/src/core/pairing.ts`). The hub's
pairing routes do exist, and krypton desktop on another computer pairs with them; the phone app
has not caught up. The only connection the app offers today is the host token, which vibey's own
design keeps on the host computer (the device pairing section of
[SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md), and
[ADR-0071](../architecture/decisions/0071-hub-pairing-and-trust.md)).
We do not recommend copying it to a phone, and we have not verified a phone reaching a LAN hub
end to end. To drive vibey from another computer today, pair krypton desktop.

`vibey hub devices` lists paired devices; `vibey hub revoke DEVICE_ID` refuses one from its next
request.

### The web app { #the-web-app }

The release attaches `krypton-web-<version>.tar.gz`, the app built for a browser. Served from its
own address (for example with `python3 -m http.server` on port 8000), it cannot read the hub's
answers: the hub sends no cross-origin (CORS) headers, by design, so a page from any other
address is refused by the browser (`src/vibey/infrastructure/hub/app.py`). The hub does not serve
the web app from its own address either. We have not run it end to end; this is what the code
says. On a computer, use krypton desktop or the VS Code extension instead.

### Copy the whole codebase

```bash
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --from-source ~/vibey
```

That clones every commit into `~/vibey`, builds it with `uv sync --extra dev`, and installs the
commands from that copy, so what you run is what you can read and change. Add `--with-krypton` to
also install `krypton-app` from the same copy. Run it again and it updates the same copy instead
of making a second one. If the repository's home is ever gone, the
[Rebuild](../continuation/rebuild.md) prompt starts from any surviving copy.

### Reinstall or upgrade

Run the same install command again. It reinstalls the newest published vibey in place. With
`--full`, every setup step is repeated, and each one leaves finished work as it is.

### Remove the krypton interfaces

```bash
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh | sh
```

On its own it changes nothing: it lists what it found. Add `--yes` to remove it:

```bash
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh | sh -s -- --yes
```

It removes the `krypton` command (whether uv, pipx or pip installed it), the editor extension from
every VS Code-family editor that has it (`code`, `code-insiders`, `codium`, `cursor`,
`windsurf`), and krypton desktop: the Flatpak, the four files the Ubuntu tarball put under
`/usr`, and the macOS app, after checking the app really is krypton's. Settings and the desktop's
pairing with a hub are kept unless you add `--purge`; before you do, it prints the
`vibey hub revoke` command that makes the hub forget the device too. It never asks for
administrator rights: a file only root may remove is printed as a `sudo` command for you to run.
The phone app is removed on the phone. To remove only the launcher: `uv tool uninstall krypton-app`.

### What is never uninstalled

vibey-engine's core (the engine, its runners, the `vibey` command and its TUI, its data, its
database, and the models it runs on) has no uninstall script and never will (sub-doctrine 10.m,
[ADR-0082](../architecture/decisions/0082-install-copy-reinstall-and-a-core-that-stays.md)).
It is your machine: you can still remove anything with your own tools, such as
`uv tool uninstall vibey-engine`. The project simply never offers to destroy its core.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `install: unknown option --full (try --help)` | The script on `main` is older than #1978. | Use [the manual path](#without-full-the-manual-path) until the next release. |
| `vibey: command not found` after the installer | `uv`'s tool folder is not on your `PATH` (common when `uv` was already installed elsewhere, or the terminal predates it). | `uv tool update-shell`, then open a new terminal. Or add `export PATH="$(uv tool dir --bin):$PATH"` to your profile. |
| `install: the postgres step failed ...` (or any step) | That step's command failed; the message above it says why. | Fix that, then run the command it names, or the whole installer again. |
| `install: the ... step needs sudo ..., and there is no terminal to ask on` | The script was run where it cannot ask for your password. | Run it from a terminal, or skip that step with its `VIBEY_FULL_*=0` switch and do it by hand. |
| `install: the ollama step uses Homebrew on macOS, and brew is not here` | No Homebrew on this Mac. | Install the Ollama app from https://ollama.com/download, open it once, and run the installer again. |
| `No module named 'fastapi'` from `vibey serve` or `vibey hub start` | The engine was installed without its `hub` extra (the current release's default). | `uv tool install --reinstall 'vibey-engine[hub]'` |
| `DatabaseNotConfigured` | `VIBEY_PG_URL` is not set in this terminal. | Export the line from your profile, or open a new terminal. |
| `vibey --version` says `krypton-app not installed` after `--with-krypton` | The two are installed in separate tool folders, so the engine cannot see the apps package. | Nothing is wrong. `krypton --version` prints the launcher's version. |
| `vibey new` exits 75 | The Sabbath: sundown Friday to sundown Saturday, vibey starts no new work. | Wait, or add `--ignore-sabbath` to that one command ([The Sabbath](sabbath.md)). |
| macOS says krypton "cannot be opened" | Gatekeeper's quarantine flag on an app that is not notarised. | `xattr -dr com.apple.quarantine /Applications/krypton.app` |

## Where next

- [Let another LLM drive vibey](drive-from-an-llm.md): connect Claude Code, Codex, Cursor or Zed
  and run projects from chat.
- [Drive a project from anywhere](drive-a-project.md): start, answer, pause and unwind a project
  from a terminal, VS Code or the desktop app.
- [Local models on Ollama](local-models-ollama.md): the model, its settings, and how to run
  unattended.

## Say it in one line

One command, with `--full`, installs vibey and sets up PostgreSQL, the database, Ollama and the
model; you keep the `VIBEY_PG_URL` line and lock PostgreSQL with scram-sha-256.
