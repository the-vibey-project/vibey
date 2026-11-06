# krypton-app

> [!IMPORTANT]
> **Work in progress — not a final product:** `krypton-app` and `vibey` are actively under development and not yet a final product. Features, interfaces, and packaging are still taking shape. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.
>
> **Bottom Line Up Front (BLUF) — Install `krypton` and every krypton interface on any platform:**
>
> - **Install `krypton` (the browser launcher) and `vibey-engine` in one command (macOS & Linux):**
>   ```bash
>   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
>   # Or with uv / pipx / pip:
>   uv tool install krypton-app   # or: pipx install krypton-app / pip install krypton-app
>   ```
> - **Launch it:**
>   ```bash
>   krypton                       # starts `vibey serve` on 127.0.0.1:8765 and opens it in your browser
>   vibey connect --yes           # plugs vibey into Claude Code, Claude Desktop, Codex, Cursor, VS Code & Gemini CLI
>   ```
> - **Install the other krypton apps:**
>   - **krypton desktop (macOS 15+ Apple silicon):** Download `krypton-desktop-<version>-macos-arm64.dmg` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases), drag **krypton** to **Applications**, and run `xattr -dr com.apple.quarantine /Applications/krypton.app`.
>   - **krypton desktop (Linux — any distro via Flatpak, or Ubuntu 24.04+ tarball):** `flatpak install --user krypton-desktop-<version>-linux-x86_64.flatpak` (or `sudo tar -xzf krypton-desktop-<version>-linux-x86_64.tar.gz -C /`).
>   - **krypton for VS Code / VSCodium / Cursor:** `codium --install-extension the-vibey-project.krypton` or `code --install-extension krypton-vscode-<version>.vsix`.
>   - **krypton web & mobile (Browser, Android `.apk`, iOS):** See [docs/guides/install.md](../../docs/guides/install.md) and [docs/guides/downloads.md](../../docs/guides/downloads.md).

krypton is every app and interface of [vibey](https://the-vibey-project.github.io/vibey/).
This package carries them and installs one command, `krypton`.

```bash
pip install krypton-app      # brings vibey-engine[hub] with it: the engine and its web hub
krypton                      # start the local vibey hub and open it in your browser
krypton --help
```

## What `krypton` does today

`krypton` is a launcher. It finds the `vibey` command, starts `vibey serve` on
`127.0.0.1:8765` (change it with `--host` and `--port`), waits until the hub answers, and
opens it in your browser, where the hub's front door says it is running and where to go next
(the desktop app, the VS Code chat, or pairing a phone). `--no-browser` only starts it.

When the installed vibey-engine has no `vibey serve` yet, `krypton` says so plainly, lists
what you can use instead, and exits with status 1. It never pretends a hub is running.

## Releases

Published by `.github/workflows/krypton-app.yml` alone, by trusted publishing: a dev build
to TestPyPI (environment `testpypi`) on each push to `develop` that changes this tree or the
workflow, and a release to PyPI (environment `pypi`) on each such push to `main`. There is no
schedule. A push GitHub skips publishes nothing: a squash merge whose message quotes an old
`[skip ci]` subject skips every push workflow, which is how the 3.0.0 promotion first
published neither package. Merge a promotion by rebase, or edit the squash message. ADR-0069 records why vibey publishes exactly two packages, `vibey-engine` and
`krypton-app`.
