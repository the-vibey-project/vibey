"""Repair the mechanical defects in a lane's work, and refuse to touch the rest.

    python3 lane-repair.py                    # report what could be repaired; change nothing
    python3 lane-repair.py --repair           # repair every lane it safely can
    python3 lane-repair.py --repair --only installer-catalogue

Between a lane finishing and a lane being publishable sit two kinds of defect, and they want
opposite treatment.

MECHANICAL, and repaired here. A ruff violation that ruff itself will fix. A file the lane
wrote outside the tree its spec owns, where that file is recognisable junk -- a verdict
dropped in the repository root, a `sitecustomize.py` injecting a path, a second package at the
root shadowing the real one under src/. installer-catalogue #469 finished with all thirteen of
its own tests passing and was held only by 49 fixable ruff findings and four such files.

SUBSTANTIVE, and never touched. A module that imports a name nothing defines. A file that does
not parse. A spec that named tests the lane never wrote. These are the lane's actual work being
wrong, and a script that "fixed" them would be writing the lane's code while claiming to tidy
it -- then a human would review a diff nobody wrote deliberately. They are reported and left.

The distinction is the whole point: everything repaired here is something a formatter or a
delete could do, and every judgement is left for a person.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"

# Files a lane writes outside its spec's tree that are safe to delete: each is a by-product of
# the model working, never a deliverable, and none is ever named in a "Where to change".
JUNK_NAMES = {"qwenloop_verdict.txt", "sitecustomize.py", ".DS_Store"}
# A package directory at the repository root shadowing the real one under src/. installer-
# catalogue created `vibey/__init__.py` and `vibey/domain/__init__.py` beside the real
# src/vibey, which changes how every interpreter in the tree resolves the name.
SHADOW_ROOTS = {"vibey", "vibey_gh", "vibey_bootstrap", "qwenloop"}


def run(argv: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, (done.stdout + done.stderr).strip()


def verify(slug: str) -> list[str]:
    run([sys.executable, str(STORM / "tools/lane-verify.py"), slug], STORM, timeout=900)
    report = LANES / slug / ".qwenstorm/verify.json"
    if not report.is_file():
        return ["no verify report"]
    return list(json.loads(report.read_text()).get("problems", []))


def strays(problems: list[str]) -> list[str]:
    for problem in problems:
        if problem.startswith("wrote outside the spec's tree:"):
            return [p.strip() for p in problem.split(":", 1)[1].split(",") if p.strip()]
    return []


def repairable(path: str) -> bool:
    """Only recognisable by-products, never something that might be the lane's deliverable."""
    name = Path(path).name
    if name in JUNK_NAMES:
        return True
    head = Path(path).parts[0] if Path(path).parts else ""
    return head in SHADOW_ROOTS and not path.startswith("src/")


def repair(slug: str, dry: bool) -> list[str]:
    lane = LANES / slug
    done: list[str] = []
    before = verify(slug)
    if not before:
        return ["already clean"]

    # 1. the files the lane left outside its spec's tree
    for path in strays(before):
        if not repairable(path):
            done.append(f"left alone (not recognisable junk): {path}")
            continue
        target = lane / path
        if not target.exists():
            continue
        if dry:
            done.append(f"would delete {path}")
            continue
        if target.is_dir():
            run(["rm", "-rf", str(target)], lane)
        else:
            target.unlink()
        done.append(f"deleted {path}")
    # a shadow package leaves its directory behind once its files are gone
    if not dry:
        for head in SHADOW_ROOTS:
            stray_dir = lane / head
            if stray_dir.is_dir() and not any(stray_dir.rglob("*.py")):
                run(["rm", "-rf", str(stray_dir)], lane)

    # 2. what ruff will fix itself
    if any(p.startswith("ruff:") for p in before):
        interpreter = lane / ".venv/bin/python"
        if interpreter.is_file():
            if dry:
                done.append("would run ruff --fix and ruff format")
            else:
                run([str(interpreter), "-m", "ruff", "check", "--fix", "."], lane)
                run([str(interpreter), "-m", "ruff", "format", "."], lane)
                done.append("ran ruff --fix and ruff format")

    if dry:
        return done or ["nothing this script can repair"]

    after = verify(slug)
    done.append(f"{len(before)} problem(s) -> {len(after)}")
    for problem in after:
        done.append(f"still held: {problem}")
    return done


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    settled: set[str] = set()
    for name in ("integrated.txt", "abandoned.txt"):
        path = STORM / name
        if path.is_file():
            settled |= {line.strip() for line in path.read_text().splitlines() if line.strip()}
    slugs = sorted(
        d.name
        for d in LANES.iterdir()
        if d.is_dir() and d.name not in settled and (d / ".qwenstorm/result.json").is_file()
    )
    if args.only:
        slugs = [s for s in slugs if s in args.only]
    for slug in slugs:
        print(slug)
        for line in repair(slug, dry=not args.repair):
            print(f"    {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
