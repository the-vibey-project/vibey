---
description: Install vibey in one command, reinstall it by running the same command again, copy the whole codebase in one more, and remove the krypton interfaces cleanly — while vibey-engine's core is never uninstalled.
---
# Install, copy, reinstall, uninstall

**Bottom line:** one command installs vibey; running it again repairs it; one flag copies the
whole codebase; and one script removes the krypton interfaces without ever touching the
engine's core.

## Install (or reinstall, or upgrade)

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh
```

That installs [uv](https://docs.astral.sh/uv/) if it is missing, installs `vibey-engine` with
it, and finishes with `vibey doctor`, which tells you what still needs you (PostgreSQL,
Ollama, an engine login). **Run it again at any time**: it reinstalls in place, so the
command that made an install is also the one that repairs it.

Add the krypton apps (the `krypton` command and its browser interface) with
`--with-krypton`:

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
```

The desktop, mobile and editor clients have their own installers on the
[Downloads](downloads.md) page.

## Copy the whole codebase

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --from-source ~/vibey
```

That clones every commit into `~/vibey`, builds it with `uv sync --extra dev`, and installs
the commands from that copy, so what you run is what you can read and change. Run it again
and it updates the same copy instead of making a second one. If the repository's home is
ever gone, the [Rebuild](../continuation/rebuild.md) prompt starts from any surviving copy.

## Remove the krypton interfaces

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh | sh
```

On its own it changes nothing: it lists what it found. Add `--yes` to remove it:

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh | sh -s -- --yes
```

It removes the `krypton` command (whether uv, pipx or pip installed it), the editor extension
from every VS Code-family editor that has it, and krypton desktop — the Flatpak, the four
files the Ubuntu install put under `/usr`, and the macOS app, after checking the app really is
krypton's. Settings and the desktop's pairing with a hub are kept unless you add `--purge`;
before you do, it prints the `vibey hub revoke` command that makes the hub forget the device
too. It never asks for administrator rights: a file only root may remove is printed as a
`sudo` command for you to run. The phone app is removed on the phone.

## What is never uninstalled

vibey-engine's core — the engine, its runners, the `vibey` command and its TUI, its data, its
database, and the models it runs on — has no uninstall script and never will (sub-doctrine
10.m, [ADR-0082](../architecture/decisions/0082-install-copy-reinstall-and-a-core-that-stays.md)).
It is your machine: you can still remove anything with your own tools. The project simply
never offers to destroy its core.
