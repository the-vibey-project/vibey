# Installation

## As a Claude Code marketplace

The native route. Claude Code reads the marketplace manifest and manages plugins for you.

```bash
# From the Git remote — one marketplace, the whole family
/plugin marketplace add the-vibey-project/vibey

# ...or from a local clone of the monorepo
/plugin marketplace add /path/to/vibey

# Browse, then install what you want
/plugin
/plugin install security-principles@vibey
```

## With the CLI

The same skills ship as a Python package with **no runtime dependencies of its own**.
Useful when you want the skills in a harness other than Claude Code, or you would rather
not clone. The `vibey-skills` command is one of the console scripts the `vibey`
distribution installs — there is no separate `vibey-skills` package any more
(vibey ADR-0037).

```bash
# Install the family, then use the CLI
uv tool install vibey-engine          # or: pipx install vibey-engine / pip install vibey-engine
vibey-skills install --all

# ...or run it once without installing anything permanently
uvx --from vibey vibey-skills install --all
```

Requires Python 3.12 or newer, which is the common floor for `vibey` and every bundled
library. CI tests the supported range through Python 3.14.

!!! note "Upgrading from vibe-engineering-skills or from the vibey-skills package"
    The package was renamed to `vibey-skills` in 2.0.0 and folded into `vibey` in
    vibey 1.0.0. Uninstall whichever you have — `pip uninstall vibe-engineering-skills`
    or `pip uninstall vibey-skills` (or the matching `uv tool uninstall`) — then install
    `vibey` as above. The `vibe-skills` command still works as a deprecated alias;
    `vibe-engineering-skills` (the long command) was removed. If you added the marketplace
    under an old name, re-add it as `the-vibey-project/vibey` and install plugins as
    `<plugin>@vibey`.

## Where skills get installed

`install` copies each skill directory to `~/.claude/skills/<skill-name>/` by default,
creating the directory if it does not exist. Override with `--dest`:

```bash
vibey-skills install --all --dest ./.claude/skills   # project-local instead of user-global
```

Existing directories are **skipped, never overwritten** — see
[Usage](usage.md#conflicts-and-updates).
