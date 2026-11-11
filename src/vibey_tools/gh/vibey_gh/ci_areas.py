# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Turn a diff into the CI areas it touches, a tier and ready-made matrices.

A pull request into the integration branch should run only what its diff can affect, on a
small matrix; the merge queue, promotion and a push to the release branch run everything.
This module is the decision, and nothing else: it reads two declared maps
(`.github/ci-areas.toml`, `.github/ci-matrices.toml`) and prints job outputs. It changes
no workflow and skips nothing by itself.

The design rule is FAIL SAFE. A skipped required check counts as passing on GitHub, so every
doubt resolves to the full tier and never to a skip: a path no area claims, a path on the
always-full list, an empty diff, a diff that could not be computed, an event this code does
not recognise, a pull request or push whose target branch is unknown or is the release
branch, and a map that cannot be read or fails validation. "Unmapped means full" is the
runtime rule; the test that every tracked file is mapped or on the always-full list is what
keeps that rule from firing by surprise.

Globs are `*` (anything but `/`), `**` (anything, crossing `/`) and `?` (one character but
`/`), anchored to the whole path. A bare `*.md` therefore matches a root file only, which is
why the root markdown is listed by exact name.

A matrix job whose rows have an owner (`owner_key`, a package directory) selects, for a
changed path, the owning row AND every row that installs it from the tree. The edges are not
declared: they are read from each row's own `install` string (`pip install -e <path>`,
resolved against the row's directory), so the matrix cannot disagree with itself.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import shlex
import sys
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from vibey_gh.config import find_root
from vibey_gh.contributor_setup import SubprocessRunner
from vibey_gh.interfaces.ci_areas_interface import (
    AreaDecision,
    CiAreasCommandInterface,
    CiAreasInterface,
)
from vibey_gh.interfaces.command_runner_interface import CommandRunnerInterface

__all__ = ["AreaDecision", "CiAreas", "CiAreasCommand"]

AREAS_FILE = Path(".github/ci-areas.toml")
MATRICES_FILE = Path(".github/ci-matrices.toml")

_DEFAULT_FULL_EVENTS = ("merge_group", "workflow_dispatch", "schedule")
_DEFAULT_DIFF_EVENTS = ("pull_request", "push")
_DEFAULT_FULL_BASE_REFS = ("main",)
# How many paths one kind of reason names before it says "and N more". It only caps the
# length of a stderr message and the job summary; it never changes a decision (every path
# still counts toward `full`).
_REASON_CAP = 20
_TIERS = ("pr", "full")
# Options whose next token is a path, and the long forms that attach it with `=`.
_OPERAND_OPTIONS = ("-e", "--editable", "-r", "--requirement")
_LONG_ATTACHED = ("--editable=", "--requirement=")


class CiAreas(CiAreasInterface):
    """Implements `CiAreasInterface` over the two declared maps."""

    def __init__(self, areas: Mapping[str, Any], matrices: Mapping[str, Any]) -> None:
        declared = areas.get("areas", {})
        self._require_table(declared, "[areas]")
        self._areas = {
            name: self._globs(spec, f"[areas.{name}]") for name, spec in declared.items()
        }
        self._full = self._globs(areas.get("full", {}), "[full]")
        events = areas.get("events", {})
        self._require_table(events, "[events]")
        # A string where a list belongs would iterate as characters ("main" -> m, a, i, n)
        # and silently stop a promotion pull request being full: refuse it at load.
        where = "[events]"
        self._full_events = tuple(self._names(events, "full", where, _DEFAULT_FULL_EVENTS))
        self._diff_events = tuple(self._names(events, "diff", where, _DEFAULT_DIFF_EVENTS))
        self._full_base_refs = tuple(
            self._names(events, "full_base_refs", where, _DEFAULT_FULL_BASE_REFS)
        )
        # Validated here, at load, so a broken map is found before a decision depends on it.
        # Every top-level entry is a job: a `[[tools]]` where `[tools]` belongs is refused,
        # not dropped.
        for name, spec in matrices.items():
            self._require_table(spec, f"[{name}]")
        self._jobs = {
            name: self._checked(name, spec, set(self._areas)) for name, spec in matrices.items()
        }
        self._plans = {
            name: self._plan(spec) for name, spec in self._jobs.items() if "owner_key" in spec
        }

    @classmethod
    def load(cls, areas_path: Path, matrices_path: Path) -> CiAreas:
        """Read both maps; a missing or malformed file raises, it is never read as empty."""
        with areas_path.open("rb") as handle:
            areas = tomllib.load(handle)
        with matrices_path.open("rb") as handle:
            matrices = tomllib.load(handle)
        return cls(areas, matrices)

    # ------------------------------------------------------------------ validation

    @staticmethod
    def _require_table(value: Any, where: str) -> None:
        malformed = not isinstance(value, dict)  # a bad map is a ValueError, by contract
        if malformed:
            raise ValueError(f"{where} must be a table")

    @staticmethod
    def _names(
        spec: Mapping[str, Any], key: str, where: str, default: Sequence[str] = ()
    ) -> list[str]:
        value = spec.get(key, list(default))
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{where} `{key}` must be a list of strings")
        return value

    @classmethod
    def _require_string(cls, value: Any, where: str) -> None:
        malformed = not isinstance(value, str)
        if malformed:
            raise ValueError(f"{where} must be a string")

    @classmethod
    def _checked(cls, job: str, spec: dict[str, Any], declared: set[str]) -> dict[str, Any]:
        """Refuse a matrix job that names an undeclared area or lacks what it relies on."""
        where = f"[{job}]"
        for tier in ("full", "pr"):
            malformed = not isinstance(spec.get(tier), list)
            if malformed:
                raise ValueError(f"{where} needs a `{tier}` list of rows")
        if not spec["full"]:
            raise ValueError(f"{where} `full` must not be empty: a full run would run nothing")
        cls._require_string(spec.get("output", job), f"{where} `output`")
        select_on = spec.get("select_on", {})
        cls._require_table(select_on, f"{where} `select_on`")
        named = {
            "areas": cls._names(spec, "areas", where),
            "select_all_on": cls._names(spec, "select_all_on", where),
            "select_on": list(select_on),
        }
        for key, areas in named.items():
            for area in areas:
                if area not in declared:
                    raise ValueError(
                        f"{where} `{key}` names {area!r}, which is not a declared area"
                    )
        keys = [spec["owner_key"], spec.get("name_key")] if "owner_key" in spec else []
        if keys and keys[1] is None:
            raise ValueError(f"{where} has an `owner_key` and needs a `name_key` to name its rows")
        for label, key in zip(("owner_key", "name_key"), keys, strict=False):
            cls._require_string(key, f"{where} `{label}`")
        for tier in ("full", "pr"):
            for row in spec[tier]:
                cls._require_table(row, f"{where} a `{tier}` row")
                for key in keys:
                    if key not in row:
                        raise ValueError(f"{where} a `{tier}` row lacks `{key}`")
                    cls._require_string(row[key], f"{where} `{key}`")
        packages = {row[keys[1]] for row in spec["full"]} if keys else set()
        for area, chosen in select_on.items():
            malformed = not isinstance(chosen, list)
            if malformed:
                raise ValueError(f"{where} `select_on` {area!r} must list package names")
            for package in chosen:
                if package not in packages:
                    raise ValueError(
                        f"{where} `select_on` names {package!r}, which is no row's package"
                    )
        return spec

    # ------------------------------------------------------------------ globs

    @staticmethod
    def _globs(spec: Any, where: str) -> tuple[tuple[str, re.Pattern[str]], ...]:
        CiAreas._require_table(spec, where)
        paths = spec.get("paths")
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            raise ValueError(f"{where} needs `paths`, a list of glob strings")
        return tuple((pattern, CiAreas._regex(pattern)) for pattern in paths)

    @staticmethod
    def _regex(pattern: str) -> re.Pattern[str]:
        out: list[str] = []
        i = 0
        while i < len(pattern):
            if pattern.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
            elif pattern.startswith("**", i):
                out.append(".*")
                i += 2
            elif pattern[i] == "*":
                out.append("[^/]*")
                i += 1
            elif pattern[i] == "?":
                out.append("[^/]")
                i += 1
            else:
                out.append(re.escape(pattern[i]))
                i += 1
        return re.compile("".join(out), re.DOTALL)

    @staticmethod
    def _first(globs: tuple[tuple[str, re.Pattern[str]], ...], path: str) -> str | None:
        for pattern, regex in globs:
            if regex.fullmatch(path):
                return pattern
        return None

    # ------------------------------------------------------------------ the dependency edges

    @staticmethod
    def _install_paths(install: Any) -> list[str] | None:
        """Every path an install command reaches into: the operand of `-e`/`--editable`/`-r`/
        `--requirement` (spaced or attached, `--editable=../x`, `-e../x`) and any positional
        token that looks like a path (a slash, a dot-dot or `.`). None when it cannot be read.
        """
        if not isinstance(install, str):
            return None
        try:
            tokens = shlex.split(install)
        except ValueError:
            return None
        paths: list[str] = []
        index = 0
        while index < len(tokens):
            token = tokens[index]
            index += 1
            operand: str | None = None
            if token in _OPERAND_OPTIONS:
                if index >= len(tokens):
                    return None
                operand = tokens[index]
                index += 1
            elif token.startswith(_LONG_ATTACHED):
                operand = token.split("=", 1)[1]
            elif token[:2] in ("-e", "-r") and not token.startswith("--") and len(token) > 2:
                operand = token[2:]
            elif not token.startswith("-"):
                # `.[dev]` is the row's own package with extras: drop the extras.
                bare = re.sub(r"\[[^\]]*\]$", "", token)
                if bare == "." or "/" in bare or ".." in bare:
                    operand = bare
            if operand is not None:
                paths.append(re.sub(r"\[[^\]]*\]$", "", operand))
        return paths

    @classmethod
    def _edges(cls, spec: Mapping[str, Any]) -> tuple[dict[str, set[str]], set[str]]:
        """(directory -> the directories it installs from the tree, directories that widen).

        A row whose install cannot be read, or reaches a path that is inside no row's
        directory, widens: it cannot say what it depends on, so a change to ANY package
        selects it. A path inside another row's directory is an edge to that row.
        """
        key = spec["owner_key"]
        dirs = {row[key] for row in spec["full"]}
        deps: dict[str, set[str]] = {directory: set() for directory in dirs}
        wide: set[str] = set()
        for row in spec["full"]:
            here = row[key]
            targets = cls._install_paths(row.get("install", ""))
            if targets is None:
                wide.add(here)
                continue
            for target in targets:
                resolved = posixpath.normpath(posixpath.join(here, target))
                if "://" in target:
                    # A URL is a path to nothing in the tree: it cannot be resolved.
                    wide.add(here)
                elif resolved == here or resolved.startswith(here + "/"):
                    continue
                owner = next(
                    (d for d in dirs if resolved == d or resolved.startswith(d + "/")), None
                )
                if owner is None:
                    wide.add(here)
                else:
                    deps[here].add(owner)
        return deps, wide

    def _plan(
        self, spec: Mapping[str, Any]
    ) -> tuple[frozenset[str], dict[str, frozenset[str]], dict[str, frozenset[str]]]:
        """(every owner directory, directory -> its reverse transitive closure, area -> the
        closed directories `select_on` names for it)."""
        deps, wide = self._edges(spec)
        dirs = frozenset(deps)

        def closure(start: set[str]) -> frozenset[str]:
            selected = set(start) | wide
            grew = True
            while grew:
                grew = False
                for directory in dirs - selected:
                    if deps[directory] & selected:
                        selected.add(directory)
                        grew = True
            return frozenset(selected)

        by_name = {row[spec["name_key"]]: row[spec["owner_key"]] for row in spec["full"]}
        chosen = {
            area: closure({by_name[name] for name in names})
            for area, names in spec.get("select_on", {}).items()
        }
        return dirs, {directory: closure({directory}) for directory in dirs}, chosen

    def dependencies(self, job: str) -> dict[str, set[str]]:
        spec = self._job(job)
        if "owner_key" not in spec:
            return {}
        deps, _ = self._edges(spec)
        label = {row[spec["owner_key"]]: row[spec["name_key"]] for row in spec["full"]}
        return {label[d]: {label[t] for t in targets} for d, targets in deps.items()}

    # ------------------------------------------------------------------ the decision

    def gate(self, event: str, base_ref: str) -> tuple[str, ...]:
        if event in self._full_events:
            return (f"the {event} event always runs the full tier",)
        if event not in self._diff_events:
            return (f"the event {event!r} is not one the declaration recognises",)
        if not base_ref:
            return (
                f"the {event} event names no target branch, so it is not known to be a small one",
            )
        if base_ref in self._full_base_refs:
            return (f"the {event} event targets {base_ref}, which always runs the full tier",)
        return ()

    def full_decision(self, *reasons: str) -> AreaDecision:
        return AreaDecision(frozenset(self._areas), True, tuple(reasons))

    def _matched(self, path: str) -> set[str]:
        return {name for name, globs in self._areas.items() if self._first(globs, path)}

    def unmapped(self, paths: Sequence[str]) -> list[str]:
        """The paths no area claims and the always-full list does not cover."""
        return [
            path
            for path in paths
            if not self._matched(path) and self._first(self._full, path) is None
        ]

    def classify(self, paths: Sequence[str], *, event: str, base_ref: str) -> AreaDecision:
        reasons = list(self.gate(event, base_ref))
        changed = [path for path in paths if path]
        if not changed:
            reasons.append("the diff is empty, so nothing says what it can affect")
        areas: set[str] = set()
        owners: set[str] = set()
        forced: list[str] = []
        for path in changed:
            always = self._first(self._full, path)
            matched = self._matched(path)
            areas |= matched
            owners |= self._owners(path, matched)
            if always is not None:
                forced.append(f"{path} matches the always-full pattern {always}")
        unclaimed = [
            f"{path} is in no area and not on the always-full list"
            for path in self.unmapped(changed)
        ]
        reasons += self._capped(forced) + self._capped(unclaimed)
        return AreaDecision(frozenset(areas), bool(reasons), tuple(reasons), frozenset(owners))

    @staticmethod
    def _capped(lines: list[str]) -> list[str]:
        if len(lines) <= _REASON_CAP:
            return lines
        return [*lines[:_REASON_CAP], f"... and {len(lines) - _REASON_CAP} more"]

    def _owners(self, path: str, matched: set[str]) -> set[str]:
        """The matrix-row owners (package directories) `path` selects, per owning job.

        A path under an owner's directory selects that owner and everything that installs it.
        A path an owning job's area claims but no owner does selects every owner: it cannot
        be said which it affects. `select_on` adds the owners an area is declared to affect.
        """
        found: set[str] = set()
        for job, (dirs, closures, by_area) in self._plans.items():
            spec = self._jobs[job]
            owned = {owner for owner in dirs if path.startswith(owner + "/")}
            selected: set[str] = set().union(*(closures[owner] for owner in owned))
            for area in matched:
                selected |= by_area.get(area, frozenset())
            narrowing = set(spec.get("areas", ())) - set(spec.get("select_all_on", ()))
            if not owned and matched & narrowing:
                selected |= dirs
            found |= selected
        return found

    # ------------------------------------------------------------------ the matrices

    def _job(self, job: str) -> dict[str, Any]:
        if job not in self._jobs:
            raise ValueError(f"no matrix job {job!r}; declared: {', '.join(sorted(self._jobs))}")
        return self._jobs[job]

    def rows(self, job: str, tier: str) -> list[dict[str, Any]]:
        """Every row `job` declares at `tier` (`full` or `pr`), copied."""
        spec = self._job(job)
        if tier not in _TIERS:
            raise ValueError(f"no tier {tier!r}; choose from {', '.join(_TIERS)}")
        return [dict(row) for row in spec[tier]]

    def matrix(self, job: str, decision: AreaDecision) -> Mapping[str, Any]:
        if decision.full:
            return {"include": self.rows(job, "full")}
        rows = self.rows(job, "pr")
        spec = self._jobs[job]
        triggers = set(spec.get("areas", ())) | set(spec.get("select_on", ()))
        if not triggers & decision.areas:
            return {"include": []}
        key = spec.get("owner_key")
        if key and decision.owners and not set(spec.get("select_all_on", ())) & decision.areas:
            # Fail safe: owners that select no row narrow nothing, they never empty the job.
            rows = [row for row in rows if row.get(key) in decision.owners] or rows
        return {"include": rows}

    def outputs(self, decision: AreaDecision) -> dict[str, str]:
        compact = (",", ":")
        # A full decision reports every declared area, whatever made it full, so a consumer
        # testing `contains(areas, X)` never reads a full run as "nothing touched X".
        areas = sorted(self._areas if decision.full else decision.areas)
        out = {
            "areas": json.dumps(areas, separators=compact),
            "full": "true" if decision.full else "false",
            "tier": "full" if decision.full else "pr",
        }
        matrices: dict[str, str] = {}
        for job, spec in self._jobs.items():
            prefix = spec.get("output", job)
            matrix = self.matrix(job, decision)
            # An empty row set is a boolean, never an empty `include`: GitHub aborts a run
            # whose matrix expands to nothing, and a skipped job is what the boolean asks for.
            out[f"{prefix}_any"] = "true" if matrix["include"] else "false"
            if matrix["include"]:
                matrices[f"{prefix}_matrix"] = json.dumps(matrix, separators=compact)
        return {**out, **matrices}


class CiAreasCommand(CiAreasCommandInterface):
    """`vibey-gh ci-areas` and `vibey-gh ci-matrix`."""

    def __init__(self, *, runner: CommandRunnerInterface | None = None) -> None:
        self._runner: CommandRunnerInterface = runner or SubprocessRunner()

    # ------------------------------------------------------------------ declaration

    @staticmethod
    def _common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "--checkout",
            type=Path,
            default=None,
            help="the repository root (default: the nearest directory declaring a project)",
        )
        parser.add_argument(
            "--areas-config",
            type=Path,
            default=None,
            help=f"the area map (default: {AREAS_FILE} under the root)",
        )
        parser.add_argument(
            "--matrices-config",
            type=Path,
            default=None,
            help=f"the matrix map (default: {MATRICES_FILE} under the root)",
        )
        return parser

    @classmethod
    def declare_areas(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--base", default="", help="the base commit of the diff")
        parser.add_argument("--head", default="", help="the head commit of the diff")
        parser.add_argument("--event", default="", help="the GitHub event name")
        parser.add_argument(
            "--base-ref", default="", help="the branch the change merges into or was pushed to"
        )
        parser.add_argument(
            "--format",
            choices=("github-output", "json"),
            default="github-output",
            help="`key=value` lines for $GITHUB_OUTPUT, or one JSON object",
        )
        return cls._common(parser)

    @classmethod
    def declare_matrix(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--job", required=True, help="the matrix job, e.g. `tools`")
        parser.add_argument("--tier", choices=_TIERS, default="full", help="which rows to print")
        return cls._common(parser)

    @classmethod
    def dispatch_areas(cls, args: argparse.Namespace) -> int:
        return cls().areas(
            base=args.base,
            head=args.head,
            event=args.event,
            base_ref=args.base_ref,
            fmt=args.format,
            paths=cls._paths(args),
        )

    @classmethod
    def dispatch_matrix(cls, args: argparse.Namespace) -> int:
        return cls().matrix(job=args.job, tier=args.tier, paths=cls._paths(args))

    @staticmethod
    def _paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
        root = (args.checkout or find_root()).resolve()
        return (
            root,
            args.areas_config or root / AREAS_FILE,
            args.matrices_config or root / MATRICES_FILE,
        )

    # ------------------------------------------------------------------ the commands

    def areas(
        self,
        *,
        base: str,
        head: str,
        event: str,
        base_ref: str,
        fmt: str,
        paths: tuple[Path, Path, Path],
    ) -> int:
        """Print the decision for the diff `base...head`; any doubt prints the full defaults."""
        root, areas_path, matrices_path = paths
        try:
            ci = CiAreas.load(areas_path, matrices_path)
        except Exception as exc:  # noqa: BLE001 - a broken map must widen, never fail the job
            print(f"vibey-gh: ci-areas: {exc}", file=sys.stderr)
            self._emit(self._fallback(areas_path, matrices_path), (str(exc),), fmt)
            return 0
        reasons = ci.gate(event, base_ref)
        if reasons:
            decision = ci.full_decision(*reasons)
        else:
            changed, failure = self._changed(base, head, root)
            if failure:
                decision = ci.full_decision(failure)
            else:
                decision = ci.classify(changed, event=event, base_ref=base_ref)
        for reason in decision.reasons:
            print(f"vibey-gh: ci-areas: full tier: {reason}", file=sys.stderr)
        self._emit(ci.outputs(decision), decision.reasons, fmt)
        return 0

    @staticmethod
    def _emit(outputs: Mapping[str, str], reasons: Sequence[str], fmt: str) -> None:
        """Print `outputs`; paths and reasons never reach stdout as lines of their own."""
        if fmt == "json":
            print(
                json.dumps(
                    {
                        "areas": json.loads(outputs["areas"]),
                        "full": outputs["full"] == "true",
                        "tier": outputs["tier"],
                        "reasons": list(reasons),
                        "outputs": dict(outputs),
                    }
                )
            )
            return
        for key, value in outputs.items():
            print(f"{key}={value}")

    @staticmethod
    def _fallback(areas_path: Path, matrices_path: Path) -> dict[str, str]:
        """The all-full defaults when a map could not be loaded: everything the readable
        parts of the declaration can still say (every area name, every full matrix)."""

        def table(path: Path) -> dict[str, Any]:
            try:
                with path.open("rb") as handle:
                    return tomllib.load(handle)
            except (OSError, ValueError):
                return {}

        declared = table(areas_path).get("areas")
        names = sorted(declared) if isinstance(declared, dict) else []
        compact = (",", ":")
        out = {
            "areas": json.dumps(names, separators=compact),
            "full": "true",
            "tier": "full",
        }
        matrices: dict[str, str] = {}
        for job, spec in table(matrices_path).items():
            rows = spec.get("full") if isinstance(spec, dict) else None
            # Only a job whose full rows are a non-empty list of tables is printed; anything
            # else cannot be stood behind, and its keys stay absent (the workflow's own
            # defaults step supplies them).
            if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
                output = spec.get("output")
                prefix = output if isinstance(output, str) else job
                out[f"{prefix}_any"] = "true"
                matrices[f"{prefix}_matrix"] = json.dumps({"include": rows}, separators=compact)
        return {**out, **matrices}

    def matrix(self, *, job: str, tier: str, paths: tuple[Path, Path, Path]) -> int:
        """Print `{"include": rows}` for one job at one tier, with no diff involved."""
        _, areas_path, matrices_path = paths
        try:
            rows = CiAreas.load(areas_path, matrices_path).rows(job, tier)
        except (OSError, ValueError) as exc:
            print(f"vibey-gh: ci-matrix: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"include": rows}, separators=(",", ":")))
        return 0

    def _changed(self, base: str, head: str, root: Path) -> tuple[list[str], str]:
        """The changed paths of `base...head` (three dots: the merge base, so a pull request
        behind its base is not charged with the base's newer changes), or why they are unknown."""
        if not base or not head or set(base) == {"0"}:
            return [], "the diff has no usable base or head, so what changed is unknown"
        if base.startswith("-") or head.startswith("-"):
            return [], "the base or head looks like an option, not a commit"
        done = self._runner.run(
            ["git", "diff", "--name-only", "--no-renames", "-z", f"{base}...{head}"], root
        )
        if done.returncode:
            return [], f"git diff {base}...{head} failed ({done.returncode}): {done.output}"
        # NUL-separated, so a path with spaces, quotes, newlines or non-ASCII arrives whole.
        return [path for path in done.stdout.split("\0") if path], ""
