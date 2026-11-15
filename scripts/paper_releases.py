# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The tracked list of releases the paper's figures count (docs/paper_releases.toml).

The paper's release-cadence figure used to read `git tag` at the moment it was checked, so
deleting a release tag on the forge, or cutting a new one, changed what `--check` computed and
turned develop red with no commit to blame. The releases are now a reviewable file: one entry
per release with its version, tag, commit and the instant it was cut. A tag is read exactly
once, by `sync`, to *propose* an entry; after that the file is the record and a tag that is
later deleted, moved or recreated changes nothing the figures say.

    python scripts/paper_releases.py sync     # record every release tag the file does not hold
    python scripts/paper_releases.py check    # exit 1 if the file is malformed or a release is missing

`sync` only ever appends. A release is cut by the Release workflow on `main`, so its entry can
only be written after the release exists: the daily documentation updater runs `sync` and opens
the entry in its refresh pull request, and `check` there fails out loud if the release branch
ships a version that still has no entry. A feature pull request is never held for a version that
has not been released.

Stdlib only, so the self-healer's bare Python can run it (sub-doctrine 12.e).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # The checker sees the interface under the name the repository root resolves; at run time the
    # script directory is on `sys.path`, so the same file is imported as `interfaces.*`.
    from scripts.interfaces.paper_releases_interface import (
        ReleaseAuditorInterface,
        ReleaseCutoffInterface,
        ReleaseLedgerInterface,
        ReleaseTagReaderInterface,
    )
else:
    from interfaces.paper_releases_interface import (
        ReleaseAuditorInterface,
        ReleaseCutoffInterface,
        ReleaseLedgerInterface,
        ReleaseTagReaderInterface,
    )

SCRIPT = "scripts/paper_releases.py"
DEFAULT_RELEASE_LEDGER = "docs/paper_releases.toml"
# Where the repository names its release branch, read from this file rather than assumed.
BRANCHES_CONFIG = ".vibey-gh.toml"
DEFAULT_RELEASE_BRANCH = "main"
DEFAULT_REMOTE = "origin"
_SHA = re.compile(r"[0-9a-f]{40}")
_FAMILY_KEYS = ("package", "tag_prefix", "version_file")
_RELEASE_KEYS = ("package", "version", "tag", "commit", "released")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # push-gate: not a push (reads tags and history for the paper's release ledger)
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)


class PaperReleaseLedger(ReleaseLedgerInterface):
    """The release ledger as the tracked TOML file holds it."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def _load(self) -> dict[str, Any]:
        return tomllib.loads(self._path.read_text(encoding="utf-8"))

    def families(self) -> list[dict[str, str]]:
        return [dict(family) for family in self._load().get("family", [])]

    def releases(self) -> list[dict[str, Any]]:
        found = [dict(release) for release in self._load().get("release", [])]
        return sorted(found, key=lambda r: (r["released"], r["tag"]))

    def problems(self) -> list[str]:
        if not self._path.is_file():
            return [f"{self._path}: the release ledger does not exist"]
        try:
            document = self._load()
        except tomllib.TOMLDecodeError as error:
            return [f"{self._path}: not valid TOML: {error}"]
        found: list[str] = []
        families = document.get("family", [])
        if not families:
            found.append(f"{self._path}: no [[family]] declares a release family")
        prefixes: dict[str, str] = {}
        for family in families:
            missing = [key for key in _FAMILY_KEYS if not isinstance(family.get(key), str)]
            if missing:
                found.append(f"{self._path}: a [[family]] lacks {', '.join(missing)}")
            else:
                prefixes[family["package"]] = family["tag_prefix"]
        seen: set[str] = set()
        for release in document.get("release", []):
            label = release.get("tag", "<no tag>")
            missing = [key for key in _RELEASE_KEYS if key not in release]
            if missing:
                found.append(f"{label}: lacks {', '.join(missing)}")
                continue
            if label in seen:
                found.append(f"{label}: recorded more than once")
            seen.add(label)
            prefix = prefixes.get(release["package"])
            if prefix is None:
                found.append(f"{label}: package {release['package']!r} has no [[family]]")
            elif release["tag"] != f"{prefix}{release['version']}":
                found.append(f"{label}: is not {prefix}{release['version']}")
            if not _SHA.fullmatch(str(release["commit"])):
                found.append(f"{label}: commit {release['commit']!r} is not a full 40-hex SHA")
            released = release["released"]
            if not isinstance(released, datetime) or released.tzinfo is None:
                found.append(f"{label}: released must be a TOML datetime with a UTC offset")
        return found

    def record(self, release: dict[str, Any]) -> bool:
        if any(known["tag"] == release["tag"] for known in self.releases()):
            return False
        text = self._path.read_text(encoding="utf-8")
        entry = (
            "\n[[release]]\n"
            f'package = "{release["package"]}"\n'
            f'version = "{release["version"]}"\n'
            f'tag = "{release["tag"]}"\n'
            f'commit = "{release["commit"]}"\n'
            f"released = {release['released'].isoformat()}\n"
        )
        self._path.write_text(text.rstrip("\n") + "\n" + entry, encoding="utf-8")
        return True


class GitTagReader(ReleaseTagReaderInterface):
    """The release tags a clone holds. Read only to propose entries; no figure reads this."""

    def __init__(self, repo: Path) -> None:
        self._repo = repo

    def read(self, tag_prefix: str, package: str) -> list[dict[str, Any]]:
        done = _git(
            self._repo,
            "for-each-ref",
            "--format=%(refname:short)%09%(objectname)%09%(*objectname)%09%(creatordate:iso-strict)",
            "refs/tags",
        )
        if done.returncode != 0:
            raise RuntimeError(f"git for-each-ref failed: {done.stderr.strip()}")
        found: list[dict[str, Any]] = []
        for line in done.stdout.splitlines():
            name, target, peeled, created = line.split("\t")
            if not name.startswith(tag_prefix) or len(name) == len(tag_prefix):
                continue
            found.append(
                {
                    "package": package,
                    "version": name[len(tag_prefix) :],
                    "tag": name,
                    # An annotated tag names its own object; its commit is the peeled one.
                    "commit": peeled or target,
                    "released": datetime.fromisoformat(created),
                }
            )
        return sorted(found, key=lambda r: (r["released"], r["tag"]))


class ReleaseCutoff(ReleaseCutoffInterface):
    """Which recorded releases existed when a revision was the tip, from the file and the log."""

    def __init__(self, repo: Path) -> None:
        self._repo = repo

    def existed_at(self, release: dict[str, Any], revision: str, tip_time: datetime) -> bool:
        if release["released"] > tip_time:
            return False
        # A release whose commit holds the pin was cut at or after it, so it did not exist when
        # the pin was the tip. A promotion rebase-merges the pin into `main` and stamps every
        # copy with one committer time, so the release cut on that tip carries the very instant
        # the pin's copy does, and the instants alone cannot tell them apart. Where the clone
        # cannot answer (the release's commit is not in it) only the instants are left, and a
        # release cut at the tip's own instant is then left out: it is not known to precede it.
        holds_the_pin = _git(
            self._repo, "merge-base", "--is-ancestor", revision, release["commit"]
        ).returncode
        if holds_the_pin == 0:
            return False
        if holds_the_pin == 1:
            return True
        return bool(release["released"] < tip_time)


class ReleaseAuditor(ReleaseAuditorInterface):
    """Compares what the release branch ships with what the ledger records."""

    def __init__(self, repo: Path, ledger: ReleaseLedgerInterface, release_ref: str) -> None:
        self._repo = repo
        self._ledger = ledger
        self._ref = release_ref

    def released_version(self, family: dict[str, str]) -> str | None:
        shown = _git(self._repo, "show", f"{self._ref}:{family['version_file']}")
        if shown.returncode != 0:
            return None
        version = tomllib.loads(shown.stdout).get("project", {}).get("version")
        return str(version) if version else None

    def unrecorded(self) -> list[str]:
        recorded = {(r["package"], r["version"]) for r in self._ledger.releases()}
        lines = []
        for family in self._ledger.families():
            version = self.released_version(family)
            if version is not None and (family["package"], version) not in recorded:
                lines.append(
                    f"{family['package']} {version} is shipped by {self._ref} but has no entry in "
                    f"{DEFAULT_RELEASE_LEDGER}; run `python {SCRIPT} sync` once its tag "
                    f"{family['tag_prefix']}{version} exists and commit the entry"
                )
        return lines


def _release_ref(repo: Path) -> str:
    branch = DEFAULT_RELEASE_BRANCH
    config = repo / BRANCHES_CONFIG
    if config.is_file():
        branches = tomllib.loads(config.read_text(encoding="utf-8")).get("branches", {})
        branch = str(branches.get("release", branch))
    return f"{DEFAULT_REMOTE}/{branch}"


# A bare function because it is this script's `__main__` entry point (ADR-0016): it parses
# flags, builds the ledger and runs one of the two commands.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("command", choices=("sync", "check"))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--ledger", default=DEFAULT_RELEASE_LEDGER, help="relative to --repo")
    parser.add_argument(
        "--release-ref",
        default=None,
        help="the ref whose version counts as released (default: the release branch's remote ref)",
    )
    args = parser.parse_args(argv)
    ledger = PaperReleaseLedger(args.repo / args.ledger)
    malformed = ledger.problems()
    if malformed:
        for reason in malformed:
            print(f"{SCRIPT}: {reason}", file=sys.stderr)
        return 1

    if args.command == "sync":
        reader = GitTagReader(args.repo)
        added = 0
        for family in ledger.families():
            for release in reader.read(family["tag_prefix"], family["package"]):
                if ledger.record(release):
                    added += 1
                    print(
                        f"{SCRIPT}: recorded {release['tag']} ({release['released'].isoformat()})"
                    )
        print(f"{SCRIPT}: {added} release(s) recorded; the ledger holds {len(ledger.releases())}")
        return 0

    ref = args.release_ref or _release_ref(args.repo)
    auditor = ReleaseAuditor(args.repo, ledger, ref)
    if all(auditor.released_version(family) is None for family in ledger.families()):
        print(
            f"{SCRIPT}: {ref} is not in this clone; the ledger's completeness is not checked here"
        )
        return 0
    missing = auditor.unrecorded()
    for line in missing:
        print(f"{SCRIPT}: {line}", file=sys.stderr)
    if missing:
        return 1
    print(f"{SCRIPT}: every release {ref} ships has an entry in {args.ledger}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
