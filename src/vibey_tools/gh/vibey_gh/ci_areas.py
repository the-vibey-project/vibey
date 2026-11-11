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
branch. "Unmapped means full" is the runtime rule; the test that every tracked file is
mapped or on the always-full list is what keeps that rule from firing by surprise.

Globs are `*` (anything but `/`), `**` (anything, crossing `/`) and `?` (one character but
`/`), anchored to the whole path. A bare `*.md` therefore matches a root file only, which is
why the root markdown is listed by exact name.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from vibey_gh.config import find_root
from vibey_gh.contributor_setup import SubprocessRunner
from vibey_gh.interfaces.ci_areas_interface import AreaDecision, CiAreasInterface
from vibey_gh.interfaces.command_runner_interface import CommandRunnerInterface

__all__ = ["AreaDecision", "CiAreas", "CiAreasCommand"]

AREAS_FILE = Path(".github/ci-areas.toml")
MATRICES_FILE = Path(".github/ci-matrices.toml")

_DEFAULT_FULL_EVENTS = ("merge_group", "workflow_dispatch", "schedule")
_DEFAULT_DIFF_EVENTS = ("pull_request", "push")
_DEFAULT_FULL_BASE_REFS = ("main",)
# How many paths one kind of reason names before it says "and N more".
_REASON_CAP = 20
_TIERS = ("pr", "full")


class CiAreas(CiAreasInterface):
    """Implements `CiAreasInterface` over the two declared maps."""

    def __init__(self, areas: Mapping[str, Any], matrices: Mapping[str, Any]) -> None:
        declared = areas.get("areas", {})
        self._areas = {
            name: self._globs(spec, f"[areas.{name}]") for name, spec in declared.items()
        }
        self._full = self._globs(areas.get("full", {}), "[full]")
        events = areas.get("events", {})
        self._full_events = tuple(events.get("full", _DEFAULT_FULL_EVENTS))
        self._diff_events = tuple(events.get("diff", _DEFAULT_DIFF_EVENTS))
        self._full_base_refs = tuple(events.get("full_base_refs", _DEFAULT_FULL_BASE_REFS))
        self._jobs = {
            name: spec
            for name, spec in matrices.items()
            if isinstance(spec, dict) and "full" in spec
        }

    @classmethod
    def load(cls, areas_path: Path, matrices_path: Path) -> CiAreas:
        """Read both maps; a missing or malformed file raises, it is never read as empty."""
        with areas_path.open("rb") as handle:
            areas = tomllib.load(handle)
        with matrices_path.open("rb") as handle:
            matrices = tomllib.load(handle)
        return cls(areas, matrices)

    # ------------------------------------------------------------------ globs

    @staticmethod
    def _globs(spec: Mapping[str, Any], where: str) -> tuple[tuple[str, re.Pattern[str]], ...]:
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

        A path under an owner's directory selects that owner. A path an owning job's area
        claims but no owner does selects every owner: it cannot be said which it affects.
        """
        found: set[str] = set()
        for spec in self._jobs.values():
            key = spec.get("owner_key")
            if key is None:
                continue
            every = {row[key] for row in spec["full"]}
            owned = {owner for owner in every if path.startswith(owner + "/")}
            narrowing = set(spec.get("areas", ())) - set(spec.get("select_all_on", ()))
            found |= owned or (every if matched & narrowing else set())
        return found

    # ------------------------------------------------------------------ the matrices

    def rows(self, job: str, tier: str) -> list[dict[str, Any]]:
        """Every row `job` declares at `tier` (`full` or `pr`), copied."""
        if job not in self._jobs:
            raise ValueError(f"no matrix job {job!r}; declared: {', '.join(sorted(self._jobs))}")
        if tier not in _TIERS:
            raise ValueError(f"no tier {tier!r}; choose from {', '.join(_TIERS)}")
        return [dict(row) for row in self._jobs[job][tier]]

    def matrix(self, job: str, decision: AreaDecision) -> Mapping[str, Any]:
        if decision.full:
            return {"include": self.rows(job, "full")}
        rows = self.rows(job, "pr")
        spec = self._jobs[job]
        if not set(spec.get("areas", ())) & decision.areas:
            return {"include": []}
        key = spec.get("owner_key")
        if key and decision.owners and not set(spec.get("select_all_on", ())) & decision.areas:
            # Fail safe: owners that select no row narrow nothing, they never empty the job.
            rows = [row for row in rows if row.get(key) in decision.owners] or rows
        return {"include": rows}

    def outputs(self, decision: AreaDecision) -> dict[str, str]:
        compact = (",", ":")
        out = {
            "areas": json.dumps(sorted(decision.areas), separators=compact),
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


class CiAreasCommand:
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
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            # A broken declaration is a defect, not a doubt about the diff: say so loudly, and
            # still print what a consumer needs to run everything.
            print(f"vibey-gh: ci-areas: {exc}", file=sys.stderr)
            print("full=true\ntier=full")
            return 1
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
        outputs = ci.outputs(decision)
        if fmt == "json":
            print(
                json.dumps(
                    {
                        "areas": sorted(decision.areas),
                        "full": decision.full,
                        "tier": outputs["tier"],
                        "reasons": list(decision.reasons),
                        "outputs": outputs,
                    }
                )
            )
        else:
            for key, value in outputs.items():
                print(f"{key}={value}")
        return 0

    def matrix(self, *, job: str, tier: str, paths: tuple[Path, Path, Path]) -> int:
        """Print `{"include": rows}` for one job at one tier, with no diff involved."""
        _, areas_path, matrices_path = paths
        try:
            rows = CiAreas.load(areas_path, matrices_path).rows(job, tier)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
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
        # NUL-separated, so a path with spaces, quotes or non-ASCII bytes arrives whole.
        return [path for path in done.stdout.split("\0") if path], ""
