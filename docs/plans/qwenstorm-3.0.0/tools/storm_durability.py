"""Storm work lives on durable storage, and nothing here will put it anywhere else (10.h).

    python3 storm_durability.py status             # the home, the storm root, durable or not
    python3 storm_durability.py check              # the gate: exit 0 durable, 78 volatile
    python3 storm_durability.py check --path lane=/some/where   # ...and these paths too
    python3 storm_durability.py home               # print the declared home
    python3 storm_durability.py worktree NAME      # print <home>/NAME, after the gate
    python3 storm_durability.py check --root DIR   # any command: a storm root other than ours

WHY THIS EXISTS
---------------
On 2026-09-24 at about 09:09 EDT the operator's Mac rebooted in the middle of a storm. macOS
empties /private/tmp at boot, and everything the storm had was under
/private/tmp/claude-501/storm/: every lane worktree, the storm root (queue, run state, lanes,
evidence), the push lock, the benchmark evidence, the scratch probes and the pre-commit
cache. Everything not yet committed went with it -- about an hour and a half of
concurrency-sweep measurements, a paper draft, and three lanes of fixes. Committed work
survived only because it lived in the main repository's refs. ADR-0057.

THE ONE DECLARED HOME
---------------------
All storm work on a machine lives under one directory, the storm HOME:

    <home>/<name>/            a worktree per lane, agent or person (`worktree NAME` prints it)
    <home>/.push-lock         the machine's shared push lock (push_gate.py's default)
    <home>/.push-lock.gate/   its state: sampled CPU, evidence, verdicts, the reap log
    <home>/<storm>/           a storm root: storm.toml, queue, ledgers, lanes/, integration/,
                              scratch/ -- the directory `tools/` is linked into

It is declared, never typed into a tool (12.c, 12.h). The first of these that is set wins:

    VIBEY_STORM_HOME              the environment, for one shell or one scheduler
    [paths] home in storm.toml    the storm root's own declaration; relative to that root
    ~/git/vibey-storm             the default

The default is where the storm moved after the reboot, and where the operator's worktrees are
now. It sits beside the main clone (`~/git/vibey`), where a person looks for checkouts, and it
survives a reboot on macOS and on Arch alike. An XDG data directory
(`~/.local/share/vibey/storm`) was the alternative. It is right for application state, and
vibey-gh keeps its journals under `~/.local/state` for that reason. Worktrees are not
application state: people `cd` into them, open them in an editor and push from them.

"Home", not "root", because "the storm root" already names the directory that holds
`storm.toml` in every tool here. A second meaning for the same two words would be a trap.

THE GATE
--------
A gate, not a judgement (12.d). Every tool that places storm work checks the home, the storm
root and whatever it is about to create. It refuses, with exit 78 (EX_CONFIG, sysexits.h) and a
message naming the key that moves it, when any of them resolves -- through symlinks, so a
/tmp that is really /private/tmp is caught either way -- under a location the operating system
empties:

    /tmp, /private/tmp        emptied at boot on macOS; tmpfs, or cleaned at boot, on most Linux
    /var/tmp                  aged out: macOS's periodic clean-up, systemd-tmpfiles on Linux
    /var/folders              macOS per-user temporary storage ($TMPDIR lives here)
    /dev/shm, /run/user       memory-backed: gone at power-off, or at logout
    $TMPDIR, $XDG_RUNTIME_DIR whatever this session calls temporary

A throwaway storm, such as a test's, is refused like any other unless its own storm.toml says
it is throwaway, with a reason:

    [durability]
    disposable = "a test fixture: the storm is built and discarded by one test"

The declaration covers that storm root and what is inside it, nothing else, and every tool that
passes it prints the reason, so a real storm cannot quietly carry it. The gate never decides for
itself that work is disposable.

WHO CONSULTS IT
---------------
`storm-queue.sh` and `lane-setup.sh` run `check` before they write anything; `storm-cycle.py`
enforces it before a pass; `storm-watch.py` reports it as a health check; the benchmarks gate
their journals with it. `push_gate.py` takes its default lock from the home. It does not call
the gate itself yet, and a lock declared onto volatile storage is still taken there. The class
is here for it to call, as it is for any tool that places work.

Nothing here moves or deletes anything. A storm found on volatile storage is reported and
refused, never "fixed" by a tool behind a person's back.

Underscored, not hyphenated: it is imported as well as run.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import storm_paths

#: The environment variable that declares the home, for one shell or one scheduler.
HOME_ENV = "VIBEY_STORM_HOME"
#: The home when nothing declares one. See the module docstring for why here.
DEFAULT_HOME = "~/git/vibey-storm"
#: EX_CONFIG from sysexits.h: the configuration names a place work cannot be kept.
VOLATILE_EXIT = 78
#: The key a person changes to move the work, named in every refusal.
MOVE_IT = f"{HOME_ENV} (or [paths] home in storm.toml)"

#: Where the operating system discards files, and when. Resolved through symlinks when used.
FIXED_VOLATILE: tuple[tuple[str, str], ...] = (
    ("/tmp", "emptied at boot on macOS; tmpfs or cleaned at boot on most Linux"),
    ("/private/tmp", "emptied at boot on macOS"),
    ("/var/tmp", "aged out by the OS (macOS periodic clean-up, systemd-tmpfiles)"),
    ("/private/var/tmp", "aged out by the OS (macOS periodic clean-up)"),
    ("/var/folders", "macOS per-user temporary storage, emptied at boot and by age"),
    ("/private/var/folders", "macOS per-user temporary storage, emptied at boot and by age"),
    ("/dev/shm", "memory-backed: gone at power-off"),
    ("/run/user", "the per-user runtime directory: memory-backed, gone at logout"),
)
#: Temporary directories this session names for itself.
ENV_VOLATILE: tuple[tuple[str, str], ...] = (
    ("TMPDIR", "this session's temporary directory ($TMPDIR)"),
    ("XDG_RUNTIME_DIR", "this session's runtime directory ($XDG_RUNTIME_DIR), gone at logout"),
)
#: A worktree name: one path component, no traversal, not hidden (the home's own dot-files
#: are the push lock and its state).
WORKTREE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _resolved(path: Path) -> Path:
    """`path` through every symlink, as far as it exists. Module-level: pure, no state.

    `Path.resolve(strict=False)` follows the links of the part that exists and keeps the rest
    as written, so a lock not yet taken is judged by where it would be made.
    """
    return path.expanduser().resolve(strict=False)


def _within(path: Path, root: Path) -> bool:
    """True when `path` is `root` or under it. Module-level with `_resolved`, for the same reason."""
    return path == root or root in path.parents


class VolatileLocations:
    """Where the operating system discards files: at boot, by age, or when a session ends."""

    def __init__(
        self,
        environ: Mapping[str, str],
        fixed: Iterable[tuple[str, str]] = FIXED_VOLATILE,
    ) -> None:
        home = _resolved(Path(environ.get("HOME") or Path.home()))
        found: dict[Path, str] = {}
        for raw, why in fixed:
            found.setdefault(_resolved(Path(raw)), why)
        for name, why in ENV_VOLATILE:
            value = environ.get(name)
            if not value:
                continue
            where = _resolved(Path(value))
            # TMPDIR=/ or TMPDIR=$HOME would make every path volatile, which says nothing
            # about any of them. Such a value is a misconfiguration of its own; it is not
            # evidence about where work is.
            if where == Path(where.anchor) or _within(home, where):
                continue
            found.setdefault(where, why)
        self._roots = tuple(sorted(found.items(), key=lambda item: -len(item[0].parts)))

    def roots(self) -> tuple[tuple[Path, str], ...]:
        """Every volatile location, resolved, with why it is volatile. Longest first."""
        return self._roots

    def containing(self, path: Path) -> tuple[Path, str] | None:
        """The volatile location `path` resolves under, and why; None when it is durable."""
        where = _resolved(path)
        for root, why in self._roots:
            if _within(where, root):
                return root, why
        return None


class StormHome:
    """The one declared durable directory all storm work on this machine lives under."""

    def __init__(self, environ: Mapping[str, str], storm_root: Path | None = None) -> None:
        self._environ = environ
        self._root = storm_root

    def resolve(self) -> tuple[Path, str]:
        """The home, and where it was declared: the environment, storm.toml, or the default."""
        declared = self._environ.get(HOME_ENV)
        if declared:
            path = Path(declared).expanduser()
            if not path.is_absolute():
                # Relative to what? The answer would change with the directory a tool was
                # started from, and two tools would then disagree about where the lock is.
                raise SystemExit(f"{HOME_ENV}={declared!r} must be an absolute path (or ~/...)")
            return path, HOME_ENV
        if self._root is not None:
            written = storm_paths.declared(self._root, "paths", "home")
            if written is not None:
                path = Path(written).expanduser()
                return (
                    path if path.is_absolute() else self._root / path,
                    f"[paths] home in {self._root}",
                )
        home = self._environ.get("HOME")
        default = Path(home) / DEFAULT_HOME[2:] if home else Path(DEFAULT_HOME).expanduser()
        return default, "default"

    def worktree(self, name: str) -> Path:
        """Where the worktree called `name` lives: directly under the home."""
        if not WORKTREE_NAME.match(name) or ".." in name:
            raise SystemExit(
                f"{name!r} is not a worktree name: one path component of letters, digits, "
                "'.', '_' or '-', not starting with a dot"
            )
        return self.resolve()[0] / name

    def push_lock(self) -> Path:
        """The machine's shared push lock: one per home, so every lane and person shares it."""
        return self.resolve()[0] / ".push-lock"


@dataclass(frozen=True)
class VolatileHit:
    """One named path found on volatile storage."""

    name: str
    path: Path
    resolved: Path
    location: Path
    why: str


class DurabilityGate:
    """Refuses to let storm work be placed where the operating system will discard it."""

    def __init__(self, locations: VolatileLocations, disposable_root: Path | None = None) -> None:
        self._locations = locations
        self._disposable_root = disposable_root

    def disposable(self) -> str | None:
        """The reason the storm root gives for being throwaway, or None when it gives none."""
        if self._disposable_root is None:
            return None
        path = self._disposable_root / storm_paths.CONFIG
        if not path.is_file():
            return None
        try:
            found = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            raise SystemExit(f"{path} could not be read: {exc}") from exc
        section = found.get("durability", {})
        if not isinstance(section, dict) or "disposable" not in section:
            return None
        reason = section["disposable"]
        if not isinstance(reason, str) or not reason.strip():
            # A bare flag is how a real storm would quietly come to carry it. The reason is the
            # declaration; without one there is nothing declared.
            raise SystemExit(
                f"{path}: [durability] disposable must say why this storm is throwaway, "
                f"not {reason!r}"
            )
        return reason.strip()

    def inspect(self, named: Mapping[str, Path]) -> list[VolatileHit]:
        """Every named path that resolves under a volatile location, in the order given."""
        exempt = self.disposable()
        inside = _resolved(self._disposable_root) if self._disposable_root else None
        hits = []
        for name, path in named.items():
            found = self._locations.containing(path)
            if found is None:
                continue
            resolved = _resolved(path)
            if exempt is not None and inside is not None and _within(resolved, inside):
                continue
            hits.append(VolatileHit(name, path, resolved, found[0], found[1]))
        return hits

    def refusal(self, hits: list[VolatileHit], key: str) -> str:
        """The message a refusal prints: what, where it really is, why that is lost, the key."""
        lines = ["storm-durability: refused: storm work would live on storage the OS empties."]
        width = max(len(hit.name) for hit in hits)
        for hit in hits:
            shown = str(hit.path)
            if hit.resolved != hit.path:
                shown += f" -> {hit.resolved}"
            lines.append(f"  {hit.name:<{width}}  {shown}")
            lines.append(f"  {'':<{width}}  under {hit.location}: {hit.why}")
        lines.append(
            f"Move it to durable storage with {key}, e.g. {DEFAULT_HOME}. Everything not yet "
            "committed and pushed is lost at the next reboot. Sub-doctrine 10.h; ADR-0057."
        )
        return "\n".join(lines)

    def enforce(self, named: Mapping[str, Path], key: str) -> None:
        """Return when every named path is durable; otherwise print why and exit 78."""
        hits = self.inspect(named)
        if hits:
            print(self.refusal(hits, key), file=sys.stderr, flush=True)
            raise SystemExit(VOLATILE_EXIT)
        reason = self.disposable()
        if reason is not None:
            print(
                f"storm-durability: {self._disposable_root} is a DISPOSABLE storm "
                f"([durability] disposable): {reason}",
                file=sys.stderr,
                flush=True,
            )


def _named(root: Path, home: Path, extra: Iterable[str]) -> dict[str, Path]:
    """The paths a check covers: the home, the storm root, and each NAME=PATH given.

    Module-level: the command line's argument parsing, which holds no state.
    """
    named = {"storm home": home, "storm root": root}
    for item in extra:
        name, sep, raw = item.partition("=")
        if not sep or not name or not raw:
            raise SystemExit(f"--path takes NAME=PATH, not {item!r}")
        named[name] = Path(raw)
    return named


def main(argv: list[str] | None = None) -> int:
    """The command line. Module-level because a script's entry point is one by definition."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, help="the storm root holding storm.toml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "status", parents=[common], help="the home, the storm root, and whether each is durable"
    )
    check = commands.add_parser("check", parents=[common], help="exit 0 durable, 78 volatile")
    check.add_argument("--path", action="append", default=[], metavar="NAME=PATH")
    commands.add_parser("home", parents=[common], help="print the declared home")
    worktree = commands.add_parser(
        "worktree", parents=[common], help="print <home>/NAME, after the gate"
    )
    worktree.add_argument("name")
    args = parser.parse_args(argv)

    root = (args.root or storm_paths.storm(__file__)).absolute()
    environ = dict(os.environ)
    home, source = StormHome(environ, root).resolve()
    locations = VolatileLocations(environ)
    gate = DurabilityGate(locations, disposable_root=root)

    if args.command == "home":
        print(home)
        return 0
    if args.command == "status":
        named = _named(root, home, ())
        blocking = {hit.name for hit in gate.inspect(named)}
        print(f"storm home  {home}  (declared by {source}; move it with {MOVE_IT})")
        for name, path in named.items():
            found = locations.containing(path)
            if found is None:
                state = "durable"
            elif name in blocking:
                state = f"VOLATILE: under {found[0]}, {found[1]}"
            else:
                state = f"volatile, inside a DISPOSABLE storm root: {gate.disposable()}"
            print(f"  {name:<11} {path}  {state}")
        return VOLATILE_EXIT if blocking else 0
    if args.command == "check":
        gate.enforce(_named(root, home, args.path), MOVE_IT)
        return 0
    target = StormHome(environ, root).worktree(args.name)
    gate.enforce({"storm home": home, "worktree": target}, MOVE_IT)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
