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

And, since the sweep of 2026-09-23, two shapes of module that will not import -- because on
that sweep six of fifteen finished lanes were held by exactly this, and four of the ten
failures were debris sitting on top of working code rather than the code being wrong:

  a lone `}` on its own line. Python has no closing brace, so it was never part of the
  program. rmq-r01-queue-config and rmq-r02-wakeup-composition both finished `completed`
  carrying one.

  a name used but never imported, where this tree already imports it in exactly one way --
  `pytest` in a test file, `field` beside `dataclass`. The import is read out of the lane, not
  from a table here, so it matches what the surrounding code actually does.

Every such repair is verified by importing the file afterwards, and a file that still will not
import is restored byte for byte. A partial repair is the worst result available: it changes
the error, so the next person debugs the repair instead of the defect.

SUBSTANTIVE, and never touched. A module importing a sibling nobody wrote. An unterminated
string, where fixing it means deciding what the string was going to say. A spec that named
tests the lane never wrote. These are the lane's actual work being incomplete, and a script
that "fixed" them would be writing the lane's code while claiming to tidy it -- then a human
would review a diff nobody wrote deliberately. They are reported and left.

The distinction is the whole point, and it is not "hard vs easy": adding the import the file
next door already uses is bookkeeping, while supplying the definition that import was supposed
to find is the work. Everything repaired here is debris; every judgement is left for a person.
"""

import argparse
import json
import re
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


def module_of(lane: Path, path: str) -> tuple[str, Path] | None:
    """The importable dotted name for a file, and the directory to import it from.

    The same walk lane-verify.py does, and deliberately so: a repair is only worth anything
    if it is judged by the check that was holding the lane, not by a second opinion invented
    here that happens to be easier to satisfy.
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


def import_error(lane: Path, path: str) -> str | None:
    """None if the file imports, else the last line of why it does not."""
    found = module_of(lane, path)
    if found is None:
        return None
    module, root = found
    interpreter = lane / ".venv/bin/python"
    if not interpreter.is_file():
        return None
    code, out = run(
        [
            str(interpreter),
            "-c",
            f"import sys; sys.path.insert(0, {str(root)!r}); import {module}",
        ],
        lane,
        timeout=180,
    )
    if not code:
        return None
    return out.strip().splitlines()[-1] if out.strip() else f"exit {code}"


def canonical_import(lane: Path, name: str) -> str | None:
    """How this tree already imports `name`, or None when it does not say unambiguously.

    Read out of the lane rather than kept in a table here. A table is a guess that ages: it
    would have to know that this repository writes `from collections.abc import Sequence` and
    not `from typing import Sequence`, for every name anyone might miss, forever. The tree
    already answers the question for the names that actually occur, and when it answers with
    two different sources the honest move is to decline rather than pick one.
    """
    sources: set[str] = set()
    for file in lane.rglob("*.py"):
        if ".venv" in file.parts or ".git" in file.parts:
            continue
        try:
            text = file.read_text(errors="replace")
        except OSError:
            continue
        if name not in text:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if re.fullmatch(rf"import {re.escape(name)}(\s+as\s+\w+)?", stripped):
                sources.add(f"import {name}")
            found = re.fullmatch(r"from ([\w.]+) import (.+)", stripped)
            if found and name in [n.strip().split(" as ")[0] for n in found.group(2).split(",")]:
                sources.add(f"from {found.group(1)} import {name}")
    return sources.pop() if len(sources) == 1 else None


def insertion_point(lines: list[str]) -> int:
    """After the last top-level import, or after the docstring when there are none."""
    last = None
    for index, line in enumerate(lines):
        if re.match(r"(import |from )\S", line):
            last = index
    if last is not None:
        return last + 1
    for index, line in enumerate(lines):
        if line.strip() and not line.lstrip().startswith("#"):
            return index
    return 0


def mechanical_fix(lane: Path, path: str, reason: str) -> str | None:
    """Apply one provable fix for one import failure. Returns what it did, or None.

    Only two shapes qualify, and both are debris rather than code:

      a lone `}` -- Python has no closing brace, so a line that is nothing but one was never
      part of the program. EDITING-RULES.md rule 11 tells the model this and it still happens;
      rmq-r01-queue-config and rmq-r02-wakeup-composition both finished `completed` on it.

      a name with exactly one import in this tree -- `pytest` in a test file that never
      imported it, `field` used beside `dataclass`. Adding the import the surrounding code
      already uses is not writing the lane's logic; inventing a *definition* would be, and
      that is the line this refuses to cross.

    Everything else is left: a module that imports a sibling nobody wrote needs that sibling
    written, and an unterminated string needs someone to decide what the string was going to
    say. Those are the lane's work being incomplete, not debris on top of it.
    """
    file = lane / path
    try:
        text = file.read_text(errors="replace")
    except OSError:
        return None
    lines = text.splitlines(keepends=True)

    if "unmatched '}'" in reason or "unmatched '}'" in reason.replace('"', "'"):
        kept = [line for line in lines if line.strip() != "}"]
        if len(kept) == len(lines):
            return None
        file.write_text("".join(kept))
        return f"removed {len(lines) - len(kept)} stray '}}' line(s)"

    missing = re.search(r"name '([A-Za-z_]\w*)' is not defined", reason)
    if missing:
        name = missing.group(1)
        statement = canonical_import(lane, name)
        if statement is None:
            return None
        at = insertion_point([line.rstrip("\n") for line in lines])
        lines.insert(at, statement + "\n")
        file.write_text("".join(lines))
        return f"added `{statement}`"
    return None


def repair_imports(lane: Path, problems: list[str], dry: bool) -> list[str]:
    """Make the flagged files import again, or put every one of them back as it was.

    All-or-nothing per file and verified by importing it, not by the fix having been applied.
    A file that still will not import after its mechanical fixes is restored exactly, because
    a partial repair is the worst outcome available here: it changes the error, so the next
    person debugs the repair instead of the defect.
    """
    done: list[str] = []
    for problem in problems:
        if ": does not import -- " not in problem:
            continue
        path, reason = problem.split(": does not import -- ", 1)
        if not (lane / path).is_file():
            continue
        if dry:
            preview = mechanical_fix_preview(lane, path, reason)
            done.append(f"{path}: {preview}" if preview else f"{path}: left alone ({reason[:50]})")
            continue
        original = (lane / path).read_text(errors="replace")
        applied: list[str] = []
        for _ in range(4):  # a file may carry both shapes; each pass fixes at most one
            current = import_error(lane, path)
            if current is None:
                break
            did = mechanical_fix(lane, path, current)
            if did is None:
                break
            applied.append(did)
        if import_error(lane, path) is None and applied:
            done.append(f"{path}: {', '.join(applied)} -- imports now")
        elif applied:
            (lane / path).write_text(original)
            done.append(f"{path}: reverted, still would not import ({reason[:45]})")
        else:
            done.append(f"{path}: left alone, not mechanical ({reason[:45]})")
    return done


def mechanical_fix_preview(lane: Path, path: str, reason: str) -> str | None:
    if "unmatched '}'" in reason:
        return "would remove stray '}' line(s)"
    missing = re.search(r"name '([A-Za-z_]\w*)' is not defined", reason)
    if missing:
        statement = canonical_import(lane, missing.group(1))
        return f"would add `{statement}`" if statement else None
    return None


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

    # 2. make the flagged files import again, where the reason is debris rather than logic
    done.extend(repair_imports(lane, before, dry))

    # 3. what ruff will fix itself -- after the imports, so it formats what they inserted
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
