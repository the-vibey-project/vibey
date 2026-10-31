# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the managed hooks learn which `vibey_gh` source to run: local git config (#1292).

The hooks used to read `[install] self_source` from the tracked `.vibey-gh.toml` and fall back
to `.`. A tracked file is branch content, so a branch chose what the hook executed: one that
added a root `pyproject.toml` named `vibey-gh` beside a `vibey_gh/` directory had its own code
run when a developer committed or pushed on that checkout.

The hooks now read `vibey-gh.self-source` from this clone's local git config, which a checkout
cannot change, and an unset key means "not self-hosted". The declaration stays in the
repository (`[install] self_source`, sub-doctrine 12.c); `vibey-gh install` copies it into
local config and `installed(local=True)` says out loud when the two disagree (12.e).

The key is spelled with a hyphen because git rejects an underscore in a variable name
(`error: invalid key: vibey-gh.self_source`). It is never overwritten once set: replacing a
value an operator chose is the hole this closes, so a difference is reported with the exact
command, not applied.
"""

from __future__ import annotations

import shlex
import subprocess

from vibey_gh.config import GhConfig
from vibey_gh.interfaces.hooks_self_source_interface import HooksSelfSourceInterface

__all__ = ["KEY", "HooksSelfSource"]

KEY = "vibey-gh.self-source"


class HooksSelfSource(HooksSelfSourceInterface):
    """Implements `HooksSelfSourceInterface`."""

    def declared(self, cfg: GhConfig) -> str | None:
        return cfg.self_source if cfg.self_source_declared else None

    def local(self, cfg: GhConfig) -> str | None:
        done = self._git(cfg, "config", "--local", "--get", KEY)
        value = done.stdout.strip()
        return value if done.returncode == 0 and value else None

    def reconcile(self, cfg: GhConfig) -> str:
        declared = self.declared(cfg)
        if declared is None:
            return "unchanged"
        current = self.local(cfg)
        if current == declared:
            return "unchanged"
        if current is not None:
            return (
                f"differs: kept {current!r}, the repository declares {declared!r}; "
                f"to change it run `git config --local {KEY} {shlex.quote(declared)}`"
            )
        done = self._git(cfg, "config", "--local", KEY, declared)
        return "installed" if done.returncode == 0 else f"failed: {done.stderr.strip()}"

    def problems(self, cfg: GhConfig) -> list[str]:
        declared = self.declared(cfg)
        current = self.local(cfg)
        if declared is not None and current is None:
            return [f"{KEY} is not set — run `vibey-gh install`"]
        if declared is not None and current != declared:
            return [
                (
                    f"{KEY} is {current!r} but [install] self_source declares {declared!r} — "
                    f"run `git config --local {KEY} {shlex.quote(declared)}`"
                )
            ]
        if declared is None and current is not None:
            return [
                (
                    f"{KEY} is {current!r} but .vibey-gh.toml declares no [install] "
                    f"self_source — declare it, or run `git config --local --unset {KEY}`"
                )
            ]
        return []

    @staticmethod
    def _git(cfg: GhConfig, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=cfg.root, capture_output=True, text=True, check=False
        )
