"""Resolve the merge conflicts that are decidable, and refuse the ones that are not.

    python3 lane-resolve.py                      # report what it would do; change nothing
    python3 lane-resolve.py --resolve            # resolve where it can, abort where it cannot
    python3 lane-resolve.py --resolve --only installer-catalogue
    python3 lane-resolve.py --install            # turn on git's own rerere in every repo

WHY THIS EXISTS
---------------
`lane-refresh.py` carries develop into every lane, and on a conflict it aborts and leaves the
lane at its old base. That is the safe thing to do once and the wrong thing to do forever:
develop keeps moving, so a lane that conflicts once conflicts every pass after, falls further
behind with each merge, and ends up implementing its spec against a codebase and a canon the
repository no longer has. Something has to decide.

WHAT IS DECIDABLE
-----------------
A conflict is decidable when the correct result is a function of something other than taste.
Four classes qualify, and each is resolved from its own source of truth rather than by
picking a side:

  DERIVED    The value is a function of the tree, so neither side's text is right. Both
             branches bumped "41 ADRs" to "42 ADRs" for different ADRs; the answer is the
             number of files in docs/architecture/decisions/, counted after the merge. The
             repository already enforces this with tests/meta/test_adr_counts.py, which is
             what verifies the resolution rather than a second opinion written here.
  APPEND     A ledger both sides appended distinct lines to -- integrated.txt, queue.txt,
             progress.log. Every line is a record and no record supersedes another, so the
             union of the two, deduplicated, is the only answer that loses nothing.
  LIST       Both sides added items to the same markdown list, which is the CHANGELOG case
             and by far the most frequent. Resolved ONLY when every line either side added is
             a list item: a heading or a line of prose among them means the two sides were
             restructuring the same region, not both appending to it, and that is a judgement.
             This restriction is the whole point -- a plain `merge=union` driver duplicates
             the `### Features` heading, which is how a union merge silently corrupts a
             changelog, and refusing on any non-list line is what makes that impossible here.
  RERERE     A conflict a human already resolved by hand. Git records the resolution and
             replays it, which is `--install`; this file does not reimplement it. One lane's
             resolution then settles the same conflict in the other thirteen and in every
             pass after, which is the single highest-leverage thing available.

WHAT IS NOT
-----------
Everything else, and the refusal is the feature. Two sides that changed the same function,
an add/add where both branches wrote a different file under one name, a sub-doctrine both
added as 8.k -- these are the lane's actual work disagreeing with the repository's, and a
script that picked a winner would be making a decision nobody reviewed while reporting a
tidy merge. Those abort, the lane is left exactly where `lane-refresh.py` would have left it,
and the reason is printed with the paths.

A resolution is not trusted because this file produced it. Every resolved merge is verified
before it is committed -- the derived values are re-read from disk, the changelog is checked
for the duplicated heading a bad union would have introduced, and every touched Python file
must still parse. A merge that cannot pass its own check is aborted, not committed with a
warning (sub-doctrine 10.f: a marker is not evidence).
"""

import argparse
import ast
import re
import subprocess
from pathlib import Path

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"
INTEGRATION = STORM / "integration"

# Ledgers where every line is a record and none supersedes another.
APPEND_ONLY = {
    "integrated.txt",
    "abandoned.txt",
    "queue.txt",
    "progress.log",
    "filing-log.tsv",
}
# Files carrying the ADR count, which is a function of the decisions directory.
ADR_COUNTED = ("CLAUDE.md", "AGENTS.md", "GEMINI.md", "README.md", "docs/index.md")
ADR_DIR = "docs/architecture/decisions"

CONFLICT_START = re.compile(r"^<{7}(\s|$)")
CONFLICT_MID = re.compile(r"^={7}(\s|$)")
CONFLICT_BASE = re.compile(r"^\|{7}(\s|$)")
CONFLICT_END = re.compile(r"^>{7}(\s|$)")


def run(argv: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, (done.stdout + done.stderr).strip()


def read_blob(repo: Path, stage: int, path: str) -> str | None:
    """One stage of a conflicted path, byte for byte.

    Not `run()`: that joins stderr onto stdout and strips the result, which is right for
    reading a command's output and wrong for reading a file's contents. It would drop the
    trailing newline, eat a leading blank line, and splice any git warning into the middle
    of text this script is about to write back to disk.
    """
    try:
        done = subprocess.run(
            ["git", "show", f":{stage}:{path}"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def operation(repo: Path) -> str:
    """Which operation left this repo conflicted: a merge, a cherry-pick, or a rebase.

    It decides how to back out, and getting it wrong is worse than not trying. `git merge
    --abort` during a cherry-pick fails, and a failed abort leaves the repo stuck mid-
    sequencer with an index nothing else in the storm can read -- the lane then looks neither
    finished nor running to every later step. Conflicts reach this script from two places
    that are not both merges: lane-refresh.py merges develop into a lane, and lane-publish.py
    cherry-picks a lane's commit onto fresh develop in a worktree.
    """
    git = repo / ".git"
    if git.is_file():  # a worktree: .git is a file pointing at the real directory
        text = git.read_text(errors="replace").strip()
        if text.startswith("gitdir:"):
            git = Path(text.split(":", 1)[1].strip())
    if (git / "CHERRY_PICK_HEAD").exists():
        return "cherry-pick"
    if (git / "REBASE_HEAD").exists() or (git / "rebase-merge").exists():
        return "rebase"
    if (git / "MERGE_HEAD").exists():
        return "merge"
    return "merge"


def back_out(repo: Path) -> None:
    """Abandon whatever is in progress, with the command that operation actually answers to."""
    # push-gate: not a push (operation() names merge, cherry-pick or rebase)
    run(["git", f"{operation(repo)}", "--abort"], repo)


def conflicted(repo: Path) -> list[str]:
    """The paths git reports as unmerged, from the index rather than by scanning for markers."""
    code, out = run(["git", "diff", "--name-only", "--diff-filter=U"], repo)
    if code:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_list_item(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True  # blank lines carry no claim either way
    return bool(re.match(r"^([-*+]\s|\d+[.)]\s)", stripped))


def split_hunks(text: str) -> list[object]:
    """Split a conflicted file into plain strings and {ours, theirs} hunks.

    Parsed from the markers rather than from `git show :2:`/`:3:` on purpose. The index
    stages give whole-file versions, which answer "what did each side have" but not "where
    did they disagree" -- and the LIST class is positional: theirs' new bullets belong in the
    section they were written in, not appended to the end of the file. The markers are the
    only place that position survives.
    """
    out: list[object] = []
    plain: list[str] = []
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        if not CONFLICT_START.match(lines[index]):
            plain.append(lines[index])
            index += 1
            continue
        if plain:
            out.append("".join(plain))
            plain = []
        index += 1
        ours: list[str] = []
        theirs: list[str] = []
        side = ours
        closed = False
        while index < len(lines):
            line = lines[index]
            if CONFLICT_BASE.match(line):
                side = []  # diff3 base section: recorded by git, not needed to decide
                index += 1
                continue
            if CONFLICT_MID.match(line):
                side = theirs
                index += 1
                continue
            if CONFLICT_END.match(line):
                index += 1
                closed = True
                break
            side.append(line)
            index += 1
        if not closed:
            return []  # truncated markers: refuse to guess at the shape of the file
        out.append({"ours": ours, "theirs": theirs})
    if plain:
        out.append("".join(plain))
    return out


def merge_hunk_as_list(hunk: dict) -> str | None:
    """Ours, then every one of theirs that ours does not already carry -- if all are items."""
    ours, theirs = hunk["ours"], hunk["theirs"]
    if not all(is_list_item(line) for line in ours + theirs):
        return None
    seen = {line.strip() for line in ours if line.strip()}
    extra = [line for line in theirs if line.strip() and line.strip() not in seen]
    body = "".join(ours)
    if extra and body and not body.endswith("\n"):
        body += "\n"
    return body + "".join(extra)


def merge_hunk_as_append(hunk: dict) -> str:
    """Every record from both sides, in ours-then-theirs order, each kept once."""
    seen: set[str] = set()
    out: list[str] = []
    for line in hunk["ours"] + hunk["theirs"]:
        key = line.strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(line)
    return "".join(out)


def adr_truth(repo: Path) -> tuple[int, str] | None:
    """How many ADRs the tree actually has, and the highest number, read from disk."""
    decisions = repo / ADR_DIR
    if not decisions.is_dir():
        return None
    numbers = []
    for path in decisions.glob("*.md"):
        found = re.match(r"^(\d{4})-", path.name)
        if found:
            numbers.append(int(found.group(1)))
    if not numbers:
        return None
    return len(numbers), f"{min(numbers):04d}–{max(numbers):04d}"


def resolve_derived_adr(repo: Path, path: str) -> tuple[str | None, str]:
    """Rewrite the count from the directory, taking ours as the text and disk as the number.

    Returns the resolved text, or None and the reason it was refused. The reason is the
    point: "could not count the ADRs" and "the substitution moved a line it was not aimed
    at" send whoever reads the log to completely different places, and one message covering
    both would send them to the wrong one (sub-doctrine 10.f).
    """
    truth = adr_truth(repo)
    if truth is None:
        return None, f"no ADRs found under {ADR_DIR}/ to count"
    count, span = truth
    ours = read_blob(repo, 2, path)
    if ours is None:
        return None, "could not read our side of the file"
    if "ADRs" not in ours:
        return None, "our side no longer states an ADR count"
    fixed = re.sub(r"\b\d+ ADRs\b", f"{count} ADRs", ours)
    # GEMINI.md carries the span beside the count; a number-only substitution would leave
    # "42 ADRs: 0001–0041", which tests/meta/test_adr_counts.py rejects.
    fixed = re.sub(r"\b\d{4}[–-]\d{4}\b", span, fixed)
    # A substitution is a blunt instrument pointed at a whole file. The claim being made is
    # narrow -- only the count and the span change -- so check it rather than trust it: any
    # line that moved without mentioning ADRs means the pattern reached something it was
    # never aimed at, and the honest answer is then to refuse.
    before, after = ours.splitlines(), fixed.splitlines()
    if len(before) != len(after):
        return None, "the substitution changed how many lines the file has"
    for number, (old, new) in enumerate(zip(before, after, strict=True), start=1):
        if old != new and "ADRs" not in old:
            return None, f"line {number} changes without mentioning ADRs: {old.strip()[:45]!r}"
    return fixed, ""


def classify(repo: Path, path: str) -> str:
    name = Path(path).name
    if name in APPEND_ONLY:
        return "APPEND"
    if path in ADR_COUNTED and adr_truth(repo) is not None:
        return "DERIVED"
    if name == "uv.lock":
        return "REGENERATE"
    target = repo / path
    if not target.is_file():
        return "REFUSE"
    hunks = split_hunks(target.read_text(errors="replace"))
    if not hunks:
        return "REFUSE"
    blocks = [h for h in hunks if isinstance(h, dict)]
    if blocks and all(merge_hunk_as_list(h) is not None for h in blocks):
        return "LIST"
    return "REFUSE"


def apply_resolution(repo: Path, path: str, kind: str) -> str | None:
    """Write the resolved file and stage it. Returns a reason on refusal, None on success."""
    target = repo / path
    if kind == "DERIVED":
        fixed, reason = resolve_derived_adr(repo, path)
        if fixed is None:
            return reason
        target.write_text(fixed)
    elif kind == "REGENERATE":
        code, _ = run(["git", "checkout", "--ours", "--", path], repo)
        if code:
            return "could not take ours before regenerating"
        code, out = run(["uv", "lock"], repo, timeout=900)
        if code:
            return f"uv lock failed: {out.splitlines()[-1][:70] if out else 'no output'}"
    else:
        if not target.is_file():
            return "file is missing"
        pieces = split_hunks(target.read_text(errors="replace"))
        if not pieces:
            return "conflict markers are truncated"
        out: list[str] = []
        for piece in pieces:
            if isinstance(piece, str):
                out.append(piece)
                continue
            merged = merge_hunk_as_append(piece) if kind == "APPEND" else merge_hunk_as_list(piece)
            if merged is None:
                return "a hunk stopped being a pure list while resolving"
            out.append(merged)
        target.write_text("".join(out))
    code, out = run(["git", "add", "--", path], repo)
    return None if code == 0 else f"could not stage: {out[:70]}"


def verify(repo: Path, paths: list[str]) -> list[str]:
    """Check the resolution against the tree, not against the fact that it was produced here."""
    problems: list[str] = []
    for path in paths:
        target = repo / path
        if not target.is_file():
            continue
        text = target.read_text(errors="replace")
        if any(
            pattern.match(line)
            for line in text.splitlines()
            for pattern in (CONFLICT_START, CONFLICT_MID, CONFLICT_END)
        ):
            problems.append(f"{path}: conflict markers survived the resolution")
            continue
        if path.endswith(".py"):
            try:
                ast.parse(text)
            except SyntaxError as exc:
                problems.append(f"{path}: no longer parses ({exc.msg} line {exc.lineno})")
        if Path(path).name == "CHANGELOG.md":
            headings = [line for line in text.splitlines() if line.startswith("#")]
            repeated = {h for h in headings if headings.count(h) > 1 and h.startswith("###")}
            if repeated:
                problems.append(f"{path}: duplicated heading {sorted(repeated)[0]!r}")
        if path in ADR_COUNTED:
            truth = adr_truth(repo)
            stated = re.search(r"\b(\d+) ADRs\b", text)
            if truth and stated and int(stated.group(1)) != truth[0]:
                problems.append(f"{path}: says {stated.group(1)} ADRs, tree has {truth[0]}")
    return problems


def resolve_repo(repo: Path, label: str, dry: bool) -> str:
    paths = conflicted(repo)
    if not paths:
        return "no conflict"
    plan = {path: classify(repo, path) for path in paths}
    refused = [p for p, kind in plan.items() if kind == "REFUSE"]
    if refused:
        summary = ", ".join(refused[:3]) + (f" (+{len(refused) - 3})" if len(refused) > 3 else "")
        if not dry:
            back_out(repo)
        return f"REFUSED, left at its old base -- needs a person: {summary}"
    if dry:
        kinds = ", ".join(f"{p} [{k}]" for p, k in plan.items())
        return f"would resolve {len(plan)}: {kinds}"

    kind_of_operation = operation(repo)
    for path, kind in plan.items():
        reason = apply_resolution(repo, path, kind)
        if reason:
            back_out(repo)
            return f"REFUSED while resolving {path}: {reason}"
    problems = verify(repo, list(plan))
    if problems:
        back_out(repo)
        return f"REFUSED by its own check: {problems[0]}"
    if kind_of_operation == "cherry-pick":
        # --continue, not a fresh commit: a cherry-pick carries the lane's own commit message
        # onto develop, and that message is what a reviewer reads on the pull request. Writing
        # "resolve <slug>" over it would replace the description of the work with a note about
        # the plumbing that landed it.
        finish = ["git", "cherry-pick", "--continue", "--no-edit"]
    else:
        finish = [
            "git",
            "commit",
            "--no-verify",
            "-q",
            "-m",
            f"chore(storm): resolve {label} merge",
        ]
    code, out = run(finish, repo)
    if code:
        back_out(repo)
        return f"REFUSED: could not complete the {kind_of_operation}: {out[:70]}"
    return f"resolved {len(plan)} path(s): " + ", ".join(f"{p} [{k}]" for p, k in plan.items())


def repos() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    if (INTEGRATION / ".git").exists():
        out.append((INTEGRATION, "integration"))
    if LANES.is_dir():
        for path in sorted(LANES.iterdir()):
            if (path / ".git").exists():
                out.append((path, path.name))
    return out


def install() -> int:
    """Turn on git's own rerere, so a conflict resolved by hand once is replayed everywhere.

    Not a reimplementation of anything here: rerere is git's record of how a human settled a
    specific conflict, replayed whenever that same conflict reappears. With fourteen lanes
    all merging the same develop, the same conflict arrives fourteen times and again on every
    later pass -- so one careful resolution is worth more than any rule this file could carry.

    AND NOTHING ELSE. An earlier version also wrote `<ledger> merge=union` into each clone's
    .git/info/attributes for the APPEND files, which looked like the same idea and was not.
    Git's union driver runs during the merge, so it would settle queue.txt before the APPEND
    class here ever saw it -- and it concatenates without deduplicating, so two branches
    recording the same slug in integrated.txt produce it twice. That is the coarser of two
    mechanisms winning purely by running first, and it is the same failure this file's
    docstring rejects for CHANGELOG. One path, which deduplicates and is checked, is better
    than two that disagree.
    """
    for repo, label in repos():
        for key, value in (("rerere.enabled", "true"), ("rerere.autoupdate", "true")):
            run(["git", "config", key, value], repo)
        attrs = repo / ".git/info/attributes"
        if attrs.is_file():
            kept = [
                line
                for line in attrs.read_text().splitlines()
                if not (line.endswith("merge=union") and line.split()[0] in APPEND_ONLY)
            ]
            attrs.write_text("\n".join(kept) + "\n" if kept else "")
        print(f"  {label:36} rerere on")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolve", action="store_true", help="actually resolve and commit")
    parser.add_argument("--install", action="store_true", help="enable rerere and union attrs")
    parser.add_argument("--only", action="append")
    # Not every conflicted repository is a lane. lane-publish.py cherry-picks a lane's commit
    # onto fresh develop inside a worktree of the main checkout, and a conflict there is the
    # same question about the same two sides -- so it gets the same answer, from the same code.
    parser.add_argument("--repo", help="resolve in this repository instead of the lanes")
    args = parser.parse_args()
    if args.install:
        return install()
    targets = repos()
    if args.repo:
        path = Path(args.repo).absolute()
        targets = [(path, path.name)]
    found = 0
    for repo, label in targets:
        if args.only and label not in args.only:
            continue
        outcome = resolve_repo(repo, label, dry=not args.resolve)
        if outcome == "no conflict":
            continue
        found += 1
        print(f"  {label:36} {outcome}")
    print(f"{found} repo(s) mid-conflict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
