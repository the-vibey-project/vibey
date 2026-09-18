# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Derive the release version from what actually changed.

This has to be automatic, not remembered. A PyPI upload with `skip-existing` turns an
unbumped release into a green run that publishes nothing, silently, with no warning — so
a human-maintained version is a silent-failure generator.

    breaking marker        -> MAJOR   the range said so; outranks the two lines below it
    content_paths changed  -> MINOR   the product changed; users receive something new
    only code_paths        -> PATCH   an internal fix
    neither                -> NONE    docs, CI, tooling: nothing an installed user gets
    version already ahead  -> NONE    a deliberate bump is in place; never double it

MAJOR escalates a decision the two lines under it already reached; it never creates one.
A range that reaches no installed user still releases nothing, and writing
`BREAKING-CHANGE:` over a documentation edit does not change that.

`none` is a legitimate and common answer. The promotion still happens; it simply does not
publish, which is correct rather than a failure.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib

from vibey_gh.config import GhConfig
from vibey_gh.flatten import Flattener

VERSION_RE = re.compile(r'^(__version__\s*=\s*")([^"]+)(")', re.MULTILINE)
JSON_VERSION_KEYS = ("version",)
# A TOML `version = "..."`, matched only inside the [project] table — pyproject has
# other tables with a `version` key and bumping the wrong one is worse than not bumping.
TOML_VERSION_RE = re.compile(r'^(version\s*=\s*")([^"]+)(")', re.MULTILINE)
# A Citation File Format `version: X.Y.Z`. Anchored at column zero on purpose: that is
# what distinguishes the software's own version from `cff-version:`, the FORMAT version,
# which sits four lines above it in every CITATION.cff and must never be bumped. Nested
# keys (a `preferred-citation:` block, a `references:` entry) are indented and so cannot
# match either. Left unmanaged, this file is the most visible stale number a project has:
# GitHub renders it as "Cite this repository" and citation managers read it directly --
# vibey's said 0.6.0 through two releases before anything noticed.
CFF_VERSION_RE = re.compile(r"^(version:[ \t]*)(\S+)([ \t]*)$", re.MULTILINE)


def _toml_version(text: str) -> str | None:
    """The [project] version, read with the parser rather than a regex."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    version = data.get("project", {}).get("version")
    return str(version) if version is not None else None


def _project_table(text: str) -> tuple[int, int]:
    """(start, end) character offsets of the [project] table's body."""
    match = re.search(r"^\[project\]\s*$", text, re.MULTILINE)
    if match is None:
        raise RuntimeError("no [project] table")
    start = match.end()
    nxt = re.search(r"^\[", text[start:], re.MULTILINE)
    return start, start + (nxt.start() if nxt else len(text) - start)


def _git(cfg: GhConfig, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cfg.root, capture_output=True, text=True, check=False)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def read_version(cfg: GhConfig) -> str:
    """The working version, from the first configured version file."""
    for rel in cfg.version_files:
        path = cfg.root / rel
        if not path.is_file():
            continue
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("metadata", data)
            for key in JSON_VERSION_KEYS:
                if key in meta:
                    return str(meta[key])
        elif path.suffix == ".toml":
            version = _toml_version(path.read_text(encoding="utf-8"))
            if version is not None:
                return version
        elif path.suffix == ".cff":
            match = CFF_VERSION_RE.search(path.read_text(encoding="utf-8"))
            if match:
                return match.group(2)
        else:
            match = VERSION_RE.search(path.read_text(encoding="utf-8"))
            if match:
                return match.group(2)
    raise RuntimeError("no version found in any configured version file")


def read_version_at(cfg: GhConfig, ref: str) -> str | None:
    for rel in cfg.version_files:
        r = subprocess.run(
            ["git", "show", f"{ref}:{rel}"],
            cwd=cfg.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode:
            continue
        if rel.endswith(".json"):
            try:
                data = json.loads(r.stdout)
            except json.JSONDecodeError:
                continue
            meta = data.get("metadata", data)
            for key in JSON_VERSION_KEYS:
                if key in meta:
                    return str(meta[key])
        elif rel.endswith(".toml"):
            version = _toml_version(r.stdout)
            if version is not None:
                return version
        elif rel.endswith(".cff"):
            match = CFF_VERSION_RE.search(r.stdout)
            if match:
                return match.group(2)
        else:
            match = VERSION_RE.search(r.stdout)
            if match:
                return match.group(2)
    return None


def bump(version: str, level: str) -> str:
    """The next version at `level` — `major`, `minor`, or anything else meaning patch.

    `major` is derived like the other two, not chosen. A version this function cannot
    produce is a version the next release derives from a number the machine does not
    believe in: `decide` reads the working version back, sees it ahead of the released
    one, and answers "a deliberate bump is in place" — once, for that release. The
    release after it derives from the hand-written number as though the tool had written
    it. So the only safe way to reach 1.0.0 is for the deriver to be able to reach it.
    """
    major, minor, patch = (int(p) for p in version.split(".")[:3])
    if level == "major":
        return f"{major + 1}.0.0"
    return f"{major}.{minor + 1}.0" if level == "minor" else f"{major}.{minor}.{patch + 1}"


def breaking_marker(cfg: GhConfig, since: str, head: str) -> str | None:
    """The first breaking-change declaration in `since..head`, verbatim, or None.

    Conventional Commits accepts two ways to say it and this reads both: a
    `BREAKING-CHANGE:` / `BREAKING CHANGE:` footer anywhere in the range, and a `!` before
    the colon of any subject in it. Neither is spelled here. Both are asked of
    `flatten.Flattener`, which already owns them for this package, because THE TWO MUST
    AGREE: `vibey-gh flatten` re-marks the flattened subject with `!` and carries every
    breaking footer forward onto the commit it writes. If this module read the range more
    narrowly than that one writes it, `vibey-gh` would publish a minor over a commit
    `vibey-gh` itself had just marked breaking — one half of this package contradicting
    the other, in the direction nobody notices until somebody's build breaks against a
    version that promised not to.

    Every commit is read, not the first. That is the same lesson `_breaking_footers`
    records: a range routinely breaks something in a later commit than the one whose
    subject survives a flatten.
    """
    log = _git(cfg, "log", "--reverse", "--no-merges", "--format=%B%x1e", f"{since}..{head}")
    for raw in log.split("\x1e"):
        body = raw.strip("\n")
        if not body:
            continue
        subject = body.partition("\n")[0]
        if Flattener._marks_breaking(subject):
            return subject.strip()
        footers = Flattener._breaking_lines(body)
        if footers:
            return footers[0][1]
    return None


def _provenance_only(cfg: GhConfig, since: str, path: str) -> bool:
    """True when every changed line in `path` is a provenance header line.

    The fingerprint header is the one diff this tool can prove is inert: it writes the
    header, knows its exact text — current and superseded alike — and enforces it
    byte-for-byte. Without this filter, adopting the fingerprint or migrating
    `fingerprint.text` counts as a content change and derives a minor release whose entire
    diff is comments. Observed on a live adoption: 181 files gained the header and nothing
    else, and the repository was bumped 0.4.1 -> 0.5.0 for it. Superseded texts count so a
    text MIGRATION (old line out, new line in) is discounted the same as a fresh stamp.

    Only comment forms of the header count. A header line plus any other change keeps the
    file counting, because the file then contains a real change.
    """
    markers = (cfg.text, *cfg.superseded_texts)
    diff = _git(cfg, "diff", "--unified=0", since, "HEAD", "--", path)
    saw_content_line = False
    for line in diff.splitlines():
        if not line or line[0] not in "+-" or line.startswith(("+++", "---")):
            continue
        saw_content_line = True
        body = line[1:].strip()
        # Any comment leader is fine; what identifies the line is the header text itself.
        if not any(marker in body for marker in markers):
            return False
    return saw_content_line


def decide(cfg: GhConfig, since: str) -> tuple[str | None, str]:
    released = read_version_at(cfg, since)
    if released is None:
        return None, f"cannot read a version at {since}; refusing to guess"

    working = read_version(cfg)
    if working != released:
        return None, (
            f"already at {working} while {since} is {released} — "
            "a deliberate bump is in place, leaving it alone"
        )

    return _classify(cfg, since, "HEAD", working)


def owed_at(cfg: GhConfig, since: str, head: str) -> tuple[str | None, str]:
    """What `decide` would say about an arbitrary committed head — the merge-time
    re-derivation (#254). A promotion opened when everything was bumped can gain
    bump-deriving merges before it merges; the merger re-asks this question against
    the CURRENT head, and a non-None answer means the promotion owes a release
    commit and is not ready. Reads committed state only — no working tree."""
    released = read_version_at(cfg, since)
    if released is None:
        return None, f"cannot read a version at {since}; refusing to guess"
    staged = read_version_at(cfg, head)
    if staged is None:
        return None, f"cannot read a version at {head}; refusing to guess"
    if staged != released:
        return None, (
            f"already at {staged} while {since} is {released} — a deliberate bump is in place"
        )
    return _classify(cfg, since, head, staged)


def _classify(cfg: GhConfig, since: str, head: str, working: str) -> tuple[str | None, str]:
    changed = [line for line in _git(cfg, "diff", "--name-only", since, head).splitlines() if line]
    if not changed:
        return None, f"no changes since {since}"
    # Discount files whose entire diff is the provenance header before classifying, so
    # stamping a repository (or re-stamping it after a fingerprint.text change) never
    # manufactures a release by itself. See _provenance_only.
    substantive = [f for f in changed if not _provenance_only(cfg, since, f)]
    discounted = len(changed) - len(substantive)
    changed = substantive
    if not changed:
        return None, (
            f"{discounted} file(s) changed, but every changed line is the provenance "
            "header — comments reach no installed user, so there is nothing to release"
        )
    if any(f.startswith(p) for f in changed for p in cfg.content_paths):
        level, why = "minor", "packaged content changed"
    elif any(f.startswith(p) for f in changed for p in cfg.code_paths):
        level, why = "patch", "only internal code changed"
    else:
        return None, (
            f"{len(changed)} file(s) changed but none reach an installed user "
            "(docs, workflows, tooling) — nothing to release"
        )
    # Asked only once the range has been shown to reach an installed user. A break is a
    # promise about an interface somebody installed, so a range that ships nothing has no
    # interface to break — and a MAJOR derived from a docs-only diff would be a version
    # number asserting an incompatibility that does not exist.
    marker = breaking_marker(cfg, since, head)
    if marker is not None:
        return bump(working, "major"), f"{why}, and the range declares a break: {marker}"
    return bump(working, level), why


def apply_version(cfg: GhConfig, new: str) -> list[str]:
    """Write `new` into every configured version file. All of them, or the tree is
    inconsistent and its own validator will reject it."""
    written = []
    for rel in cfg.version_files:
        path = cfg.root / rel
        if not path.is_file():
            continue
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            target = data.get("metadata") if isinstance(data.get("metadata"), dict) else data
            target["version"] = new
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        elif path.suffix == ".toml":
            text = path.read_text(encoding="utf-8")
            start, end = _project_table(text)
            patched, n = TOML_VERSION_RE.subn(rf"\g<1>{new}\g<3>", text[start:end], count=1)
            if n != 1:
                raise RuntimeError(f"{rel}: expected one [project] version, found {n}")
            path.write_text(text[:start] + patched + text[end:], encoding="utf-8")
        elif path.suffix == ".cff":
            text = path.read_text(encoding="utf-8")
            patched, n = CFF_VERSION_RE.subn(rf"\g<1>{new}\g<3>", text, count=1)
            if n != 1:
                raise RuntimeError(f"{rel}: expected one top-level version:, found {n}")
            path.write_text(patched, encoding="utf-8")
        else:
            text = path.read_text(encoding="utf-8")
            patched, n = VERSION_RE.subn(rf"\g<1>{new}\g<3>", text, count=1)
            if n != 1:
                raise RuntimeError(f"{rel}: expected one __version__ line, found {n}")
            path.write_text(patched, encoding="utf-8")
        written.append(rel)

    # A uv-managed project's lockfile pins its own package at the version just
    # replaced above -- self-referencing, since `uv sync` installs the project
    # editable. Leaving it stale doesn't fail quietly: uv.lock desync on this
    # commit and *only* this commit, then blocks the very promotion that just
    # produced it (`uv lock --check` fails, and CI never runs it any other
    # time). Re-lock whenever a pyproject.toml changed and a lockfile exists.
    if any(rel.endswith("pyproject.toml") for rel in written) and (cfg.root / "uv.lock").is_file():
        r = subprocess.run(
            ["uv", "lock"], cwd=cfg.root, capture_output=True, text=True, check=False
        )
        if r.returncode:
            raise RuntimeError(f"uv lock: {r.stderr.strip()}")
        written.append("uv.lock")

    # The managed workflows are the other artefact derived from this number. With
    # `[install] pin_version` on, each one pins the fallback install to the repository's
    # own `[project] version`, so a bump that does not re-render leaves every deployed
    # workflow pinning the PREVIOUS release -- and the drift check fails on the release
    # commit itself. Exactly the lockfile's failure mode, fixed in the same breath rather
    # than left to a runbook step. Imported here, not at module scope: `install` reads
    # `pyproject.toml` for the pin and must read it AFTER this function has rewritten it.
    from vibey_gh.install import rerender_version_pinned

    written.extend(rerender_version_pinned(cfg))

    return written


def dev_version(cfg: GhConfig, build: str) -> str:
    """`<release>.dev<build>` — distinct per push, PEP 440 valid, and sorting before the
    release it anticipates, which is the correct relationship."""
    digits = re.sub(r"\D", "", str(build)) or "0"
    return f"{read_version(cfg)}.dev{int(digits)}"
