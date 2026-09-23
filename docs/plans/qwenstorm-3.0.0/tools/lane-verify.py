"""Turn a lane's completion claim into evidence a reviewer can act on.

    python3 lane-verify.py              # every finished, unsettled lane
    python3 lane-verify.py SLUG ...     # just these

A lane is marked `completed` when the model emits the done marker and its verdict fence
carries the CDD labels. qwenloop's own `_has_cdd_evidence` says what that is worth: "a
deterministic protocol check, not a substitute for reviewing the values". It does not run
the spec's check block, so a lane can finish `completed` carrying code that does not import
-- visual-design-provider #324 did exactly that, shipping an interface whose `Sequence`
annotation was never imported.

Sub-doctrine 10.f: a verdict is not evidence. This runs the cheap, decisive checks over only
what the lane actually changed, and writes the answer to `.qwenstorm/verify.json` so a batch
review reads a table instead of 600 diffs. It is deliberately not the full gate suite -- it
is the triage that says which lanes are worth a human's attention first.
"""

import json
import subprocess
import sys
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# and queue.txt exist but lanes/ and integration/ do not -- those are real directories in the
# runtime root alone. Resolving the symlink lands in the worktree and finds no lanes at all.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"
INTEGRATION = STORM / "integration"


def run(argv: list[str], cwd: Path, timeout: int = 180) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    return done.returncode, (done.stdout + done.stderr).strip()


def base_of(lane: Path) -> str:
    """The commit this lane started from.

    A lane is a remote-less clone that fetched one bare SHA, so the name
    `storm/integration` does not exist inside it -- diffing against that name fails, and
    a lane that has committed its work then reads as having changed nothing. Take the SHA
    from the integration clone and ask the lane for the common ancestor, so the answer
    still holds once integration has moved on.
    """
    code, sha = run(["git", "rev-parse", "storm/integration"], INTEGRATION)
    if code or not sha:
        return "HEAD"
    code, merge_base = run(["git", "merge-base", "HEAD", sha.strip()], lane)
    return merge_base.strip() if not code and merge_base.strip() else sha.strip()


def changed(lane: Path) -> list[str]:
    """Every path the lane touched, committed or not, against the commit it started from."""
    # Both commands emit bare paths. `git status --porcelain` prefixes each line with a
    # two-letter code and a space, and slicing that off by hand put a mangled copy of every
    # path beside the real one -- `importlinter` next to `.importlinter`. Nothing here needs
    # the status codes, so nothing here parses them.
    paths: set[str] = set()
    sources = [
        ["git", "diff", "--name-only", base_of(lane)],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    for argv in sources:
        code, out = run(argv, lane)
        if code:
            continue
        paths |= {line.strip() for line in out.splitlines() if line.strip()}
    return sorted(paths)


def module_of(lane: Path, path: str) -> tuple[str, Path] | None:
    """The importable dotted name for a file, and the directory to import it from.

    Derived by walking up while each directory is a package, rather than assuming a layout:
    the workspace tenants nest their own package (src/vibey_tools/bootstrap/vibey_bootstrap/)
    so slicing a fixed `src/` prefix invents `vibey_tools.bootstrap.vibey_bootstrap.db...`,
    which is not what anything imports.
    """
    if not path.endswith(".py"):
        return None
    file = lane / path
    if not file.is_file():
        return None
    parts: list[str] = []
    folder = file.parent
    while (folder / "__init__.py").is_file():
        parts.append(folder.name)
        folder = folder.parent
    parts.reverse()
    if file.stem != "__init__":
        parts.append(file.stem)
    return (".".join(parts), folder) if parts else None


def verify(lane: Path) -> dict[str, object]:
    files = changed(lane)
    python = [f for f in files if f.endswith(".py") and (lane / f).is_file()]
    report: dict[str, object] = {"files": files, "python": len(python), "problems": []}
    problems: list[str] = report["problems"]  # type: ignore[assignment]

    if not files:
        problems.append("the lane finished having changed nothing")
        return report

    interpreter = lane / ".venv/bin/python"
    if not interpreter.is_file():
        problems.append("no .venv in the lane; uv sync failed at setup")
        return report

    # Import is the decisive cheap check: it catches the missing-name class of defect that
    # reads fine in a diff and fails the moment anything loads the module.
    for path in python:
        found = module_of(lane, path)
        if found is None:
            continue
        module, root = found
        # Import from the package's own root, so a tenant whose package is not installed in
        # this lane's venv is still checked rather than reported as a defect it did not cause.
        argv = [
            str(interpreter),
            "-c",
            f"import sys; sys.path.insert(0, {str(root)!r}); import {module}",
        ]
        code, out = run(argv, lane)
        if code:
            last = out.strip().splitlines()[-1] if out.strip() else f"exit {code}"
            problems.append(f"{path}: does not import -- {last}")

    code, out = run([str(interpreter), "-m", "ruff", "check", *python], lane) if python else (0, "")
    if code:
        problems.append(f"ruff: {out.strip().splitlines()[-1] if out.strip() else code}")

    # Files outside the tree the spec works in. installer-catalogue #469 finished `completed`
    # having also written sitecustomize.py -- which Python imports at interpreter startup -- and
    # a second `vibey/` package at the repository root shadowing the real src/vibey. Its own
    # tests passed with and without them, so they were defensive junk rather than a way of
    # faking green; but committed they would change how every interpreter in the tree resolves
    # imports. A lane edits what "Where to change" names, and nothing at the root.
    OWNED = ("src/", "tests/", "docs/", "deploy/", "migrations/", ".github/")
    stray = [
        f
        for f in files
        if not f.startswith(OWNED) and f not in {"pyproject.toml", "uv.lock", ".importlinter"}
    ]
    if stray:
        problems.append(f"wrote outside the spec's tree: {', '.join(stray[:4])}")

    # A spec that names test files under "Tests to write first (TDD)" is stating an
    # obligation, and src/vibey/{domain,application,infrastructure,cli} each sit behind a
    # 100% branch floor: implementation without its tests cannot be integrated at all.
    issue = lane / ".qwenstorm/issue.md"
    if issue.is_file() and "## Tests to write first" in issue.read_text(encoding="utf-8"):
        report["tests_required"] = True
        if not any(f.startswith("test") or "/test" in f for f in files):
            problems.append("the spec names tests under TDD and the lane wrote none")

    code, _ = run(["git", "diff", "--quiet", "--exit-code"], lane)
    dirty = code != 0
    code, out = run(["git", "log", "--oneline", f"{base_of(lane)}..HEAD"], lane)
    commits = len([line for line in out.splitlines() if line.strip()]) if code == 0 else 0
    report["commits"] = commits
    if commits == 0:
        problems.append("nothing committed: the work is only in the working tree")
    if dirty and commits:
        problems.append("uncommitted changes remain beside the commits")
    return report


def main() -> int:
    wanted = [a for a in sys.argv[1:] if not a.startswith("-")]
    settled = set()
    for name in ("integrated.txt", "abandoned.txt"):
        path = STORM / name
        if path.is_file():
            settled |= {line.strip() for line in path.read_text().splitlines() if line.strip()}

    lanes = []
    for lane in sorted(LANES.iterdir()) if LANES.is_dir() else []:
        if not lane.is_dir() or lane.name in settled:
            continue
        if wanted and lane.name not in wanted:
            continue
        result = lane / ".qwenstorm/result.json"
        if result.is_file():
            lanes.append(lane)

    bad = 0
    for lane in lanes:
        claim = json.loads((lane / ".qwenstorm/result.json").read_text())
        report = verify(lane)
        report["claimed"] = bool(claim.get("completed"))
        (lane / ".qwenstorm/verify.json").write_text(json.dumps(report, indent=2))
        problems = report["problems"]
        mark = "ok  " if not problems else "BAD "
        if problems:
            bad += 1
        claimed = "completed" if report["claimed"] else "failed   "
        print(
            f"{mark}{lane.name:42} claim={claimed} files={len(report['files']):3d} "
            f"commits={report.get('commits', 0)}"
        )
        for problem in problems[:4]:
            print(f"      - {problem}")
    print(f"\n{len(lanes)} finished lane(s), {bad} with problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
