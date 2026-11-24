# krypton-app: the `krypton` launcher for the vibey hub

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `krypton-app` is a Python package with one command, `krypton`,
> which starts the local vibey hub (`vibey serve` on `127.0.0.1:8765`) and opens it in your
> browser. It brings `vibey-engine[hub]` with it. Install both on macOS or Linux with one command,
> then run `krypton`. The hub reads vibey's database, so set up PostgreSQL and `VIBEY_PG_URL`
> first. The desktop, VS Code, web and mobile apps are separate downloads, listed below.

> [!IMPORTANT]
> **Work in progress — not a final product:** `krypton-app` and `vibey` are actively under development and not yet a final product. Features, interfaces, and packaging are still taking shape. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.

## How to read this page

**Daniel:** Professor, I installed "krypton". Where are the apps?

**Professor Feynman:** This package is the key on the hook by the door, not the house. It starts
the hub and opens its front door in your browser. The desktop and phone apps are other doors to
the same house, and each is downloaded on its own. The quick start is the first block below;
the rest is reference.

## Quick start

1. Install `vibey-engine` and `krypton-app` (macOS and Linux):

   ```bash
   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
   ```

   Or with uv, pipx or pip:

   ```bash
   uv tool install krypton-app   # or: pipx install krypton-app / pip install krypton-app
   ```

   `pip install krypton-app` brings `vibey-engine[hub]` with it: the engine and its web hub.

2. Start the hub and open it:

   ```bash
   krypton
   ```

   `krypton` waits until the hub answers, then opens `http://127.0.0.1:8765/` in your browser.
   The page there, the hub's front door, says it is running and where to go next: the desktop
   app, the VS Code chat, or pairing a phone.

3. Optionally, plug vibey into your chat and coding tools:

   ```bash
   vibey connect --yes           # Claude Code, Claude Desktop, Codex, Cursor, VS Code, Gemini CLI and Zed
   ```

   Run `vibey connect --dry-run` first to see which files it would write. The Claude Code and
   VS Code entries are written in the current directory.

## The other krypton apps

| App | Where | Install |
|---|---|---|
| krypton desktop, macOS 15+ on Apple silicon | `krypton-desktop-<version>-macos-arm64.dmg` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) | Drag **krypton** to **Applications**, then `xattr -dr com.apple.quarantine /Applications/krypton.app` |
| krypton desktop, Linux via Flatpak | `krypton-desktop-<version>-linux-<arch>.flatpak` | `flatpak install --user krypton-desktop-<version>-linux-<arch>.flatpak` |
| krypton desktop, Ubuntu 24.04+ | `krypton-desktop-<version>-linux-<arch>.tar.gz` | `sudo tar -xzf krypton-desktop-<version>-linux-<arch>.tar.gz -C /` |
| krypton for VS Code, VSCodium, Cursor | Open VSX, or `krypton-vscode-<version>.vsix` | `codium --install-extension the-vibey-project.krypton`, or `code --install-extension krypton-vscode-<version>.vsix` |
| krypton web and mobile (browser, Android `.apk`, iOS) | GitHub Releases | See [docs/guides/install.md](../../docs/guides/install.md) and [docs/guides/downloads.md](../../docs/guides/downloads.md) |

Replace `<version>` with the release you downloaded and `<arch>` with `x86_64` or `aarch64`.

## What `krypton` does

`krypton` is a launcher. It finds the `vibey` command (the one installed beside `krypton`, else
`vibey` on `PATH`), starts `vibey serve`, waits until the hub answers, and opens it in your
browser. It never pretends a hub is running.

| Flag | Default | Meaning |
|---|---|---|
| `--host HOST` | `127.0.0.1` | Address to serve on. |
| `--port PORT` | `8765` | Port to serve on. |
| `--no-browser` | off | Start the hub without opening it. |
| `--vibey VIBEY` | the `vibey` beside `krypton`, else on `PATH` | The vibey program to use. |
| `--version` | | Print the version and exit. |

Leaving the loopback address takes two things, both deliberate: `--host <address>` and
`[hub] lan = true` in `vibey.toml` (`src/vibey/cli/serve.py`).

| Exit | Meaning |
|---|---|
| `1` | No `vibey` was found; the installed vibey-engine has no `vibey serve` yet (krypton says so and lists what you can use instead); or nothing answered within 60 seconds. |
| `N` | `vibey serve` exited with status `N` before it answered; krypton passes the status on (1 if it was 0). |
| `130` | Interrupted. |

While the hub runs, `krypton` waits on it and exits with the hub's own status when it stops.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `krypton: the vibey command is not installed, so there is no hub to start.` | No `vibey` beside `krypton` or on `PATH`. | `pip install 'vibey-engine[hub]'`, or name one with `--vibey`. |
| krypton says the local web app is started by `vibey serve` and exits 1 | The installed vibey-engine is too old to serve the hub. | `uv tool install --reinstall vibey-engine`, or re-run the install command above. |
| `krypton: vibey serve exited with status N before it answered.` | The hub could not start. The database not being reachable is one likely cause (not verified here). | Check `VIBEY_PG_URL` and run `vibey doctor`. |
| `krypton: nothing answered at http://127.0.0.1:8765/ within 60s.` | The hub started but never answered; krypton stops it. | Run `vibey serve` yourself to see its output. |
| `vibey --version` prints `krypton-app not installed` after the install script | The script installs krypton-app as a separate uv tool, so vibey's own environment does not see it. | Nothing is wrong; `krypton --version` prints its version. |

## Releases

Published by `.github/workflows/krypton-app.yml` alone, by trusted publishing: a dev build
to TestPyPI (environment `testpypi`) on each push to `develop` that changes this tree or the
workflow, and a release to PyPI (environment `pypi`) on each such push to `main`. There is no
schedule. A push GitHub skips publishes nothing: a squash merge whose message quotes an old
`[skip ci]` subject skips every push workflow, which is how an earlier promotion (under the
retired 3.x numbering, before the reset to 0.x) first published neither package. Merge a
promotion by rebase, or edit the squash message. ADR-0069 records why vibey publishes exactly
two packages, `vibey-engine` and `krypton-app`.

The package supports macOS and Linux (its classifiers) and Python 3.12+.

## Where next

- [Install guide](../../docs/guides/install.md): every krypton interface and the database setup
  the hub needs.
- [Downloads](../../docs/guides/downloads.md): every release file and what it is for.
- [The hub API](../../docs/reference/hub-api.md): what the hub serves.

## Say it in one line

krypton-app installs one command, `krypton`, that starts the local vibey hub and opens it in your
browser; the other krypton apps are separate downloads.
