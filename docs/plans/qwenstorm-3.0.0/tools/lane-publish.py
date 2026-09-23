"""Publish the lanes that have actually earned it: commit, push, open a pull request.

    python3 lane-publish.py                  # report what is ready; write nothing
    python3 lane-publish.py --publish        # commit, push and open a PR for each ready lane
    python3 lane-publish.py --publish --only rmq-r03-amqp-dependency
    python3 lane-publish.py --watch 600      # re-check every 600s, publishing as lanes ripen

Never merges. A pull request is where a human looks; this stops there, and `--publish` is
required before anything leaves the machine.

REPORT MODE WRITES NOTHING
--------------------------
Without `--publish` this records nothing: not a commit, not a branch, and not a lane's
`verify.json`. It used to shell out to `lane-verify.py`, whose whole job is to write that
file, so every "report; change nothing" pass rewrote the verdict of every unsettled lane --
a report that edits the evidence it reports on. Report mode now asks lane-verify's own
`verify()` for the answer in-process and keeps it; only `--publish` has lane-verify record
it. What report mode still does is RUN each lane's checks, because that is the measurement;
the tools those checks invoke may leave their usual caches inside the lane.

WHY THE GATE IS NOT THE LANE'S OWN VERDICT
------------------------------------------
qwenloop marks a run `completed` when the model emits the done marker and its verdict fence
carries the CDD labels. Its own `_has_cdd_evidence` is candid -- "a deterministic protocol
check, not a substitute for reviewing the values" -- and nothing in the runner executes the
spec's check block. On 2026-09-22, of eleven finished lanes:

  rmq-r02-wakeup-composition   claimed completed, shipped `SyntaxError: unmatched '}'`
  visual-design-provider       claimed completed, shipped a NameError that broke a package
  installer-catalogue          claimed completed, wrote sitecustomize.py into the repo root
  chart-operator-forgejo-p1    claimed completed, shipped an unterminated string literal

Exactly one -- rmq-r03-amqp-dependency -- was genuinely mergeable. So a claim opens the
question and settles nothing (sub-doctrine 10.f). Every gate below is evidence this script
gathers itself, and a lane passes only if all of them hold.

WHAT IT REFUSES
---------------
Anything lane-verify reports a problem for; anything whose spec named tests it never wrote;
anything that touched a path its spec does not own; anything whose own check block fails when
run. A lane that fails any gate is left exactly as it is, for a human, and the reason is
printed. Silence is never taken for success.
"""

import argparse
import functools
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

import storm_forge
import storm_paths

# .absolute(), never .resolve(): tools/ is a symlink into the planning worktree, where specs/
# resolve but lanes/ and integration/ exist only in the runtime root.
STORM = Path(__file__).absolute().parent.parent
LANES = STORM / "lanes"
INTEGRATION = STORM / "integration"

# Declared in storm.toml, derived from the tree when it is silent -- never a literal
# in this file. One operator's home directory compiled into five tools is a decision
# taken away from the next adopter, and it fails by reporting an empty tree (12.h).
MAIN = storm_paths.repo(STORM)
WORKTREES = STORM.parent / "publish"
REPO = "the-vibey-project/vibey"
BASE = "develop"

# Commands a lane's check block may name that this script will run. Anything else in a check
# block is reported and skipped rather than executed: a spec is written by a model, and a
# publishing step is not the place to run whatever a model happened to type.
# `black` and `isort` are here because the gh tenant is checked by both in CI's `tools-lint`
# job, and a check this list does not name is a check that silently does not run.
SAFE = (
    "uv",
    "python",
    "python3",
    "pytest",
    "ruff",
    "mypy",
    "black",
    "isort",
    "lint-imports",
    "bandit",
    "grep",
    "git",
)


def run(
    argv: list[str],
    cwd: Path,
    timeout: int = 900,
    extra: dict[str, str] | None = None,
    drop: tuple[str, ...] = (),
) -> tuple[int, str]:
    # VIRTUAL_ENV is inherited from whatever shell started this, and `uv run` obeys it: a lane's
    # checks would then run against the environment of the checkout this script was launched
    # from rather than the lane's own, and pass or fail for reasons that have nothing to do with
    # the lane. Drop it and let uv resolve the environment from the lane it is standing in.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    # What the spec set with `export` or a `NAME=value` prefix. Applied last, because a
    # check that names a variable means its value, not the launching shell's.
    env.update(extra or {})
    # And what it unset with `env -u NAME`, which removes the name from the environment
    # the check runs in rather than setting it to an empty string.
    for name in drop:
        env.pop(name, None)
    try:
        done = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env
        )
    except FileNotFoundError:
        return 127, f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return done.returncode, (done.stdout + done.stderr).strip()


def why_failed(out: str) -> str:
    """The line a person needs, not the last line printed.

    `uv run` ends with installer chatter and warnings, so the final line of a failed check is
    usually "Installed 4 packages in 15ms" -- true, irrelevant, and the reason a report can
    look like nonsense.

    MATCH THE SHAPE, NOT THE SUBSTRING
    ----------------------------------
    This used to scan for the words "error", "failed", "assert" and the like anywhere in a
    lowercased line, and every one of them appears in output that is not a failure. A
    coverage table lists `vibey_gh/errors.py ... 100%`, which contains "error"; a test file
    named `test_failed_handoff.py` contains "failed"; and `"e   "` matches any line with an
    `e` followed by three spaces. So a lane whose real failure was two named tests was
    reported as failing at a line saying its coverage was complete -- true about the text,
    and the opposite of what it meant.

    Tools emit recognisable shapes instead, so the shapes are what is matched, in the order
    a person would want them: the named test first, then the assertion under it, then the
    type or lint error, then the gate that was missed. Only when none of those appear does
    the last line stand in, and it says so by simply being the last line.
    """
    lines = [line.rstrip() for line in out.splitlines() if line.strip()]
    for pattern in (
        r"^(FAILED|ERROR) \S",  # pytest's short summary: names the test
        r"^E\s{3}\S",  # pytest's assertion detail, under the failing test
        r"(^|\s)error:\s",  # mypy `path:line: error:`, ruff and uv `error:`
        r"^##\[error\]",  # a GitHub Actions step
        r"^\w*(Error|Exception):\s",  # the last line of a traceback
        r"Required test coverage of .* not reached",
        r"^(FAIL|Coverage failure)\b",
    ):
        for line in reversed(lines):
            if re.search(pattern, line):
                return line.strip()
    return lines[-1].strip() if lines else "no output"


def settled() -> set[str]:
    out: set[str] = set()
    for name in ("integrated.txt", "abandoned.txt"):
        path = STORM / name
        if path.is_file():
            out |= {line.strip() for line in path.read_text().splitlines() if line.strip()}
    return out


def issue_of(slug: str) -> int | None:
    """The lane's issue number, from queue.txt -- the runner's own mapping."""
    queue = STORM / "queue.txt"
    if not queue.is_file():
        return None
    for line in queue.read_text().splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[0] == slug and parts[1].isdigit():
            return int(parts[1])
    return None


# "(run in `src/vibey_tools/gh`)" or "(in src/vibey_tools/gh)" -- prose the spec already uses
# in its acceptance criteria, read here and removed before the command is split.
ANNOTATION = re.compile(r"\(\s*(?:run\s+)?in\s+`?[\w./-]+`?\s*\)")
# A leading `NAME=value`, the one piece of shell syntax that needs no shell to honour.
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# The parameter expansions an assignment's value may use: `$NAME`, `${NAME}`, and the
# defaulted `${NAME:-fallback}` / `${NAME-fallback}`. Anything else a shell can do inside
# `${...}` is refused by name rather than passed through as literal text.
PARAMETER = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:?)-([^}]*))?\}|\$([A-Za-z_][A-Za-z0-9_]*)"
)


def expand(value: str, known: dict[str, str]) -> str | None:
    """An assignment's value as a shell would have expanded it, or None if it cannot be.

    `os.path.expandvars` used to do this, and it leaves anything it does not understand
    exactly as written. orm-bootstrap-async-engine's spec sets
    `VIBEY_TEST_DATABASE_URL=${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@...}`, and the
    test would have received that text, braces and all, as its database URL: a check that
    runs and means nothing. An unset `$NAME` is empty, as in a shell; a form this does not
    honour leaves a `$` or a backtick behind, and the line is reported rather than run.
    """

    def one(match: re.Match[str]) -> str:
        braced, colon, fallback, bare = match.groups()
        current = known.get(braced or bare)
        if fallback is not None and (current is None or (colon and current == "")):
            return PARAMETER.sub(one, fallback)
        return current or ""

    out = PARAMETER.sub(one, value)
    return None if "$" in out or "`" in out else out


def tokens(command: str) -> list[str]:
    """A command split the way a shell splits it, unquoted parentheses as tokens of their own.

    `shlex.split` returns `(cd` and `pytest)` for a subshell, which cannot be told apart from
    a quoted argument that happens to hold a parenthesis. Split with `(` and `)` as
    punctuation, an unquoted one arrives alone while `"print(1)"` stays whole inside its
    quotes -- so a subshell is recognised by its structure, not by guessing at the first and
    last characters of a line.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars="()")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    return list(lexer)


class Check(NamedTuple):
    """One command a lane's spec asks for, and the two things that decide what it means."""

    argv: list[str]
    cwd: Path
    env: dict[str, str]
    unset: tuple[str, ...] = ()  # names `env -u` removes, for this command alone


def where(lane: Path, raw: str) -> Path:
    """The directory a check runs in: the lane, or the tenant its spec names.

    A workspace tenant's suite cannot be run from the repository root. Its coverage floor,
    its ini options and its package layout all live in the tenant's own pyproject, so
    `python -m pytest -q` means something different there than here -- and the paths a tenant
    spec names (`test/test_platform.py`, `vibey_gh`) do not exist from the root at all. Those
    checks reported "no tests ran" and held the lane, which is a check that runs, reports, and
    means nothing.

    This is the explicit form -- "(run in `src/vibey_tools/gh`)", prose the spec already uses
    in its acceptance criteria. `inside()` reads the other form, the `cd` the block itself
    carries. An annotation on the line is the more specific statement, so it wins.
    """
    found = re.search(r"\(\s*(?:run\s+)?in\s+`?([\w./-]+)`?\s*\)", raw)
    return inside(lane, lane, found.group(1)) or lane if found else lane


def inside(lane: Path, base: Path, target: str) -> Path | None:
    """`base/target`, or None when that is not a real directory within the lane.

    Every path a check block names is resolved through here, so a spec can move a check
    around inside its own lane and nowhere else. `..` is allowed precisely because it is
    checked afterwards: `cd ../../..` out of a tenant lands back on the lane root, which is
    the whole point, while one `..` too many lands outside and is refused.
    """
    candidate = (base / target).resolve()
    root = lane.resolve()
    if candidate != root and root not in candidate.parents:
        return None
    return candidate if candidate.is_dir() else None


def resolve(lane: Path, argv: list[str]) -> list[str]:
    """The same command, run with the LANE's tools rather than the publisher's.

    Substituting only the interpreter was enough while `python -m black` was the only
    spelling anyone used. It stopped being enough the moment bare `black` and `isort` became
    runnable checks: `run()` drops VIRTUAL_ENV and never puts the lane's `.venv/bin` on
    PATH, so a bare console script resolves to whatever environment launched this, or to
    nothing at all. Either way the formatter gate would report on a tree other than the
    lane's -- which is precisely the mistake that gate was added to catch.

    A lane without a built venv is left alone: the check then runs against whatever is on
    PATH and says so by failing, rather than being silently skipped.
    """
    interpreter = lane / ".venv/bin/python"
    if argv[0] in {"python", "python3", "pytest"} and interpreter.is_file():
        return [str(interpreter), *(["-m"] if argv[0] == "pytest" else []), *argv[1:]]
    script = lane / ".venv/bin" / argv[0]
    return [str(script), *argv[1:]] if script.is_file() else list(argv)


def checks_of(lane: Path) -> list[Check]:
    """The commands the lane's own spec says must pass.

    The lane's shell runs argv with no shell at all, so a check block is a list of argv lines:
    `&&`, pipes and redirects are literal arguments there and are literal here too. A line
    carrying any of them is not something this script can honestly run, so it is skipped and
    reported rather than guessed at.

    A SPEC IS A SCRIPT, AND A SCRIPT REMEMBERS WHERE IT IS
    ------------------------------------------------------
    `cd` used to be on that list, and dropping it was the same mistake in a third costume:
    true about the line, wrong about the block. split-332-1's spec opens `cd src/vibey_tools/gh`
    and closes `cd ../../..`, because a tenant's suite cannot run from the repository root --
    its coverage floor, its ini options and its package layout live in the tenant's own
    pyproject, and the paths it names (`test/test_platform.py`, `vibey_gh`) do not exist from
    the root at all. Drop the `cd` and every following line still runs, still reports, and
    measures the wrong tree: from the root, `import vibey_gh` resolved to a stale copy in
    another checkout's site-packages, so two tests failed against a module that had never
    received the lane's changes, while the same files from the tenant passed 2512 at 100%.

    So `cd` is honoured -- it sets where the rest of the block runs, exactly as it would in
    the shell the author had in mind. Every target is resolved through `inside()`, so it can
    only move within the lane. A `cd` that cannot be honoured stops the block instead of
    quietly relocating it: the remaining checks are not the checks the spec wrote, and a
    check that means something other than what it says is worse than one that is off.

    SPLIT THE WAY A SHELL WOULD, THEN RUN WITHOUT ONE
    -------------------------------------------------
    `shlex.split`, never `str.split`. Specs are written the way a person types a command, so
    the quoting is real: 378 of the 643 specs carry `--include='src/vibey/domain/*'`, quoted
    because a shell would otherwise glob it. `str.split` keeps those apostrophes inside the
    argument, and with no shell in the path nothing ever strips them -- coverage received a
    literal `--include='src/vibey/domain/*'`, matched no file, and answered "No data to
    report" on every lane that had a coverage gate.

    The damage was not that the check failed. It is that the check stopped meaning anything
    while still being counted: installer-catalogue's real answer, from the same data and the
    same command split correctly, is 99% against a 100% floor -- a genuine failure with a
    genuine fix, hidden behind a message about missing data. A gate that cannot pass is not a
    gate, and one that reports the wrong reason is worse than one that is simply off.
    """
    issue = lane / ".qwenstorm/issue.md"
    if not issue.is_file():
        return []
    return parse_checks(issue.read_text(encoding="utf-8"), lane)[0]


def block_of(text: str) -> str | None:
    """The check block of a spec or a lane's issue.md, or None when it has none.

    Stops at the CLOSING fence, not at the next heading. Every spec follows its block with a
    sentence or two of advice ("If black or isort reports a file you touched, run ..."), and
    those are prose about the checks rather than checks. Running them is harmless -- nothing
    in them is a command this would run -- but reporting them as checks that never run is
    noise in exactly the report that has to stay worth reading.
    """
    if "## Checks the lane must run" not in text:
        return None
    section = text.split("## Checks the lane must run", 1)[1].split("\n## ", 1)[0]
    if "```" not in section:
        # An indented block, which has no closing marker to find -- but Markdown says what it
        # is: the indented lines. An unindented line is prose, and read as a command it was
        # worse than noise. orm-bootstrap-async-engine's block is followed by "...the
        # tenant's own\npytest `addopts`, so a partial run needs `--no-cov`", and the second
        # line begins with `pytest`: it ran as a check, failed, and held the lane on a command
        # its spec never wrote, while the block's four real checks were never read at all.
        return "\n".join(line for line in section.splitlines() if line.startswith(("    ", "\t")))
    # Everything after the opening fence begins with its info string -- "bash" -- which is
    # not a check. Stripping backticks off the raw line cannot remove it, because by then it
    # no longer looks like a fence.
    inside_fence = section.split("```", 1)[1].split("\n", 1)[-1]
    return inside_fence.split("```", 1)[0] if "```" in inside_fence else inside_fence


def parse_checks(text: str, lane: Path) -> tuple[list[Check], list[tuple[str, str]]]:
    """The checks this can run, and every line it had to drop, with the reason why.

    The dropped list is the point of the split. `lint-specs.py` reports it, so a spec author
    is told which of their check lines will never run -- by this parser, not by a second
    copy of its rules that can drift from it (10.e). A gate nobody knows is off is the
    cheapest way to ship an unverified lane, and the storm shipped several.

    EVERY LINE IS EITHER RUN, CLASSIFIED, OR REPORTED
    -------------------------------------------------
    There is no fourth outcome. A comment and a fence are classified and passed over; every
    other line becomes a check or lands in the dropped list with its reason, and
    `ready()` holds a lane for any dropped line (10.f: a check that never ran is not a check
    that passed). The silent fourth outcome is what hid 80 subshell lines in 28 specs: lines
    beginning `(` were skipped with the comments, so `(cd src/vibey_runners/qwen && uv run
    python -m pytest -q)` never ran, and harness-T20a and T20c were reported READY on the
    strength of `ruff` alone. A subshell is now a chained line -- its `cd` scoped to itself,
    which is exactly what the parentheses meant -- and a list item is reported, not skipped.
    """
    block = block_of(text)
    if block is None:
        return [], []
    found: list[Check] = []
    dropped: list[tuple[str, str]] = []
    here = lane
    exported: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip().strip("`")
        if not line or line.startswith(("#", "```")):
            continue  # a comment or a fence: classified, and nothing to run
        if line.startswith(("-", "*")):
            dropped.append((line, "a list item, not a command"))
            continue
        # The directory annotation is prose for a person, not an argument for the command --
        # `where()` has already read it. And comments are stripped: a check written as
        # `python -m pytest -q # whole suite` otherwise hands pytest `#`, `whole` and `suite`
        # as paths, which is a large part of why tenant checks answered "no tests ran".
        command = ANNOTATION.sub("", line).strip()
        try:
            parts = tokens(command)
        except ValueError:
            # Unbalanced quotes: the line is not a command anybody could run, and guessing
            # where the quote was meant to close would be inventing the check.
            dropped.append((line, "unbalanced quotes"))
            continue
        if not parts:
            continue
        # `( ... )` around the whole line is a subshell: run it, with any `cd` inside it
        # scoped to the line. A parenthesis anywhere else -- or one left unclosed -- stays in
        # the tokens and is refused below as the shell syntax it is.
        subshell = len(parts) > 2 and parts[0] == "(" and parts[-1] == ")"
        if subshell:
            parts = parts[1:-1]
        if "(" in parts or ")" in parts:
            # Refused for the whole line, not one segment of it: an unclosed or nested group
            # changes what every command on the line means, so none of them is the check the
            # author wrote.
            dropped.append((line, "needs a shell (a parenthesis) and the lane's tool has none"))
            continue
        # SPLIT ON `&&` AFTER shlex, NEVER BEFORE
        # 555 of 643 specs -- 86% -- carried a check line joined with `&&`, and every one of
        # them was dropped whole for "needing a shell". It does not: `A && B` is "run A, then
        # B, and both must pass", which is what this list already means, so it is two checks.
        # Splitting the TOKENS rather than the text is what makes it safe -- shlex has
        # already consumed the quotes, so a literal `&&` inside `grep 'a && b'` stays inside
        # its one token and is never mistaken for a separator.
        segments: list[list[str]] = [[]]
        for token in parts:
            if token == "&&":
                segments.append([])
            else:
                segments[-1].append(token)
        # A `cd` ON ITS OWN LINE sets the directory for the block; a `cd` INSIDE a chain sets
        # it for that line alone. Both idioms are in these specs, and CLAUDE.md itself writes
        # the second as `(cd src/vibey_tools/gh && ...)` -- a subshell, deliberately scoped.
        # Treating a chained `cd` as persistent compounds them, so a spec visiting two tenants
        # on two lines goes looking for `gh/src/vibey_runners/qwen`; 71 specs lost every check
        # after their first tenant line that way.
        chained = len(segments) > 1 or subshell
        run_from = here
        # What `export` sets inside a subshell ends with it, as it would in a shell; on a
        # plain line it persists for the rest of the block.
        scope = exported
        stop = False
        for parts in segments:
            if not parts:
                continue
            shell = [t for t in ("||", "|", ">", "<", "$(") if any(t in p for p in parts)]
            if shell:
                # `||` is a fallback, not a sequence: `python -c "import x" || pip install x`
                # means "try, and if it fails do something else", which is a decision this
                # cannot make on the author's behalf. Reported, never guessed.
                dropped.append((line, f"needs a shell ({shell[0]}) and the lane's tool has none"))
                continue
            if parts[0] == "export":
                parts = parts[1:]  # `export FOO=bar` sets FOO for what follows, and runs nothing
            # `FOO=bar cmd ...` and a bare `export FOO=bar` are the same syntax: leading
            # assignments. 261 `export` lines and 96 `VAR=value cmd` prefixes were dropped
            # for being "not a command", which is true of the first token and not of the line.
            env = dict(scope)
            unset: list[str] = []
            parts, why = assigned(parts, env)
            if why is None and parts and parts[0] == "env":
                # `env -u NAME ... NAME=value ... cmd`: the same leading assignments, plus
                # names to remove. fakes-harness-decouple's suite line began this way and was
                # dropped as "'env' is not a command", so its whole-suite gate never ran.
                parts = parts[1:]
                while len(parts) > 1 and parts[0] in ("-u", "--unset"):
                    unset.append(parts[1])
                    env.pop(parts[1], None)
                    parts = parts[2:]
                if parts and parts[0].startswith("-"):
                    why = f"`env {parts[0]}` is not an option this honours"
                else:
                    parts, why = assigned(parts, env)
                if why is None and not parts:
                    continue  # `env` with nothing to run changes nothing that persists
            if why is not None:
                dropped.append((line, why))
                continue
            if not parts:
                scope = env  # nothing left to run: it was an `export`, so it persists
                continue
            if parts[0] == "cd":
                moved = inside(lane, run_from, parts[1]) if len(parts) == 2 else None
                if moved is None:
                    # `cd` with no argument means home, `cd -` means the last directory, and
                    # a path that leaves the lane or is not there means the author was
                    # describing a tree this is not. Whatever the rest of it was meant to
                    # check, it belongs somewhere this cannot reach -- so it is abandoned
                    # rather than run in the wrong place, for the line or for the block
                    # depending on which the `cd` governed.
                    reach = "this line" if chained else "every check after it"
                    dropped.append((line, f"cannot be honoured, so {reach} is dropped"))
                    stop = not chained
                    break
                run_from = moved
                if not chained:
                    here = moved
                continue
            if parts[0] in SAFE:
                where_it_runs = where(lane, raw) if ANNOTATION.search(raw) else run_from
                found.append(Check(parts, where_it_runs, env, tuple(unset)))
            else:
                dropped.append((line, f"{parts[0]!r} is not a command this runs"))
        if not subshell:
            exported = scope
        if stop:
            break
    return found, dropped


def assigned(parts: list[str], env: dict[str, str]) -> tuple[list[str], str | None]:
    """Consume leading `NAME=value` words into `env`: what is left, or why it cannot be run."""
    while parts and ASSIGNMENT.match(parts[0]):
        name, _, value = parts[0].partition("=")
        expanded = expand(value, {**os.environ, **env})
        if expanded is None:
            return parts, f"`{name}=` uses a shell expansion this does not perform"
        env[name] = expanded
        parts = parts[1:]
    return parts, None


@functools.cache
def verifier():
    """`lane-verify.py`, imported by path because its name is not an identifier.

    For its `verify()`, which answers without writing. Its `main()` is what writes
    `verify.json`, and report mode must not; asking the same function in-process gives the
    same verdict from the same code without the write (10.e -- one verifier, not two).
    """
    spec = importlib.util.spec_from_file_location(
        "lane_verify", Path(__file__).absolute().with_name("lane-verify.py")
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def verify(slug: str, record: bool) -> tuple[bool, list[str]]:
    """lane-verify's own verdict for one lane, re-run now rather than read from a stale file.

    "nothing committed" is not a reason to refuse: a lane's runner never commits, so every
    lane reads that way, and committing is this script's own first act. Requiring it to be
    absent made publishing impossible -- the one lane that ever passed had been committed by
    hand first. Every other problem still holds the lane.

    `record` is the acting mode's alone: lane-verify runs as itself and writes the lane's
    `verify.json`. Without it the verdict is computed in-process and nothing is written.
    """
    if record:
        code, out = run(
            [sys.executable, str(STORM / "tools/lane-verify.py"), slug], STORM, timeout=900
        )
        report = LANES / slug / ".qwenstorm/verify.json"
        if not report.is_file():
            return code == 0, [] if code == 0 else [
                out.strip().splitlines()[-1] if out else "no report"
            ]
        found = json.loads(report.read_text()).get("problems", [])
    else:
        try:
            found = verifier().verify(LANES / slug).get("problems", [])
        except Exception as exc:  # noqa: BLE001 -- one lane's crash must not end the sweep
            # Run as a subprocess, a crash in lane-verify was one lane's failed verdict. In
            # process it would take the whole report down with it, and every other lane's
            # verdict with it. It is still a verdict, and the lane is held on it.
            return False, [f"lane-verify could not judge it: {type(exc).__name__}: {exc}"]
    problems = [p for p in found if not p.startswith("nothing committed")]
    return not problems, list(problems)


def already_published(slug: str, prs: list[storm_forge.PullRequest]) -> str | None:
    """Whether this lane is already out for review.

    Without this the sweep republishes anything it published on the previous pass: the gates
    keep passing, so `ready` keeps saying yes. Idempotence has to come from the forge, not
    from remembering -- a local note would be wrong the moment a PR is opened or closed
    anywhere else.

    `prs` is the forge's whole list, read once per sweep (`storm_forge`). A pull request
    claims this lane if it was opened from the lane's own branch, or if its body CLOSES the
    lane's issue under any branch name: a lane published by hand will not be sitting on
    `lane/<slug>`, and rmq-r03-amqp-dependency went out as `feat/amqp-dependency` exactly
    this way. It asked GitHub's full-text search for that second case until 2026-09-23, and
    search answers pull requests that merely mention the words and the number -- four lanes
    were held "already published" on pull requests that close something else, and their
    check blocks never ran.
    """
    branch = f"lane/{slug}"
    for pr in prs:
        if pr.head == branch:
            return f"#{pr.number} ({pr.state.lower()})"
    code, _ = run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], MAIN, 120)
    if code == 0:
        return "a branch is already pushed"
    issue = issue_of(slug)
    for pr in storm_forge.closing(prs, issue):
        return f"#{pr.number} ({pr.state.lower()}) already closes issue #{issue}"
    return None


def ready(slug: str, prs: list[storm_forge.PullRequest], record: bool) -> tuple[bool, list[str]]:
    lane = LANES / slug
    result = lane / ".qwenstorm/result.json"
    if not result.is_file():
        return False, ["still running"]
    out_already = already_published(slug, prs)
    if out_already:
        return False, [f"already published: {out_already}"]
    clean, problems = verify(slug, record)
    if not clean:
        return False, problems
    issue = lane / ".qwenstorm/issue.md"
    ran, dropped = (
        parse_checks(issue.read_text(encoding="utf-8"), lane) if issue.is_file() else ([], [])
    )
    if not ran and not dropped:
        return False, ["its spec names no check block this script can run"]
    failures = []
    for check in ran:
        argv = resolve(lane, check.argv)
        code, out = run(argv, check.cwd, extra=check.env, drop=check.unset)
        if code:
            failures.append(f"check failed: {' '.join(argv)[:55]} -- {why_failed(out)[:110]}")
    # Last, so a real failure is the first reason a person reads -- but always, because a
    # check that never ran is not a check that passed (10.f). Before this the dropped list
    # reached lint-specs and nobody else, and a lane whose tenant suite never ran could be
    # published on the strength of the lines around it.
    failures += [f"check never runs -- {why}: {line[:70]}" for line, why in dropped]
    if not ran:
        failures.append("its spec names no check this script can run")
    return (not failures), failures


def provenance_trailer() -> str:
    """The `Made-With:` trailer, from the family's own command rather than a copy here.

    The commit below runs with `core.hooksPath=/dev/null`, because a lane's worktree carries
    the repository's hooks and a publish must not pay the full suite twice before it has even
    pushed. But the commit-msg hook is exactly what normally appends this trailer, so turning
    the hooks off silently removed it -- and `Provenance` fails every such commit on the
    forge, which is where it was finally noticed. Disabling a hook means taking on what the
    hook did (10.e: the family already ships `vibey-gh trailer`; this asks it rather than
    hard-coding the text, which would rot the moment the author line changes).
    """
    code, out = run(["vibey-gh", "trailer"], MAIN, timeout=120)
    if code or not out.strip():
        code, out = run([sys.executable, "-m", "vibey_gh", "trailer"], MAIN, timeout=120)
    line = out.strip().splitlines()[-1] if out.strip() else ""
    return line if line.startswith("Made-With:") else ""


def publish(slug: str, dry: bool) -> str:
    lane = LANES / slug
    issue = issue_of(slug)
    title = (lane / ".qwenstorm/title.txt").read_text().strip()
    branch = f"lane/{slug}"
    if dry:
        return f"would publish as {branch} (closes #{issue})"

    if (
        run(["git", "diff", "--quiet"], lane)[0]
        or run(["git", "diff", "--cached", "--quiet"], lane)[0]
        or run(["git", "ls-files", "--others", "--exclude-standard"], lane)[1]
    ):
        run(["git", "add", "-A"], lane)
        trailer = provenance_trailer()
        if not trailer:
            # NOT `if trailer:` skipping it. This script commits with the hooks disabled,
            # so nothing downstream will add the trailer that the provenance gate requires
            # -- treating the lookup's failure as "no trailer needed" would quietly rebuild
            # the trailerless commit this exists to prevent, and the lane would travel all
            # the way to a red gate to find out. Missing provenance stops the publication.
            return "could not derive the provenance trailer, so the commit would fail the gate"
        body = f"{title}\n\nWritten by a sovereign lane (gpt-oss:20b) for issue #{issue}.\n"
        body += f"\n{trailer}\n"
        code, out = run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", body], lane)
        if code:
            return f"commit failed: {out[:120]}"

    WORKTREES.mkdir(parents=True, exist_ok=True)
    tree = WORKTREES / slug
    if tree.exists():
        run(["git", "worktree", "remove", "--force", str(tree)], MAIN)
    run(["git", "fetch", "-q", "origin", BASE], MAIN)
    code, out = run(["git", "worktree", "add", str(tree), "-b", branch, f"origin/{BASE}"], MAIN)
    if code:
        return f"worktree failed: {out[:120]}"
    run(["git", "fetch", "-q", str(lane), f"storm/{slug}"], tree)
    code, head = run(["git", "rev-parse", "FETCH_HEAD"], tree)
    code, out = run(["git", "cherry-pick", head.strip()], tree)
    if code:
        # The lane's commit is being replayed onto develop as it is right now, so a conflict
        # here is the lane's work disagreeing with what landed while it ran -- the same
        # question lane-refresh.py asks, and it gets the same answer from the same code.
        # lane-resolve.py aborts the cherry-pick itself when it refuses, so the state is read
        # back from git rather than from its exit code.
        run(
            [
                sys.executable,
                str(STORM / "tools/lane-resolve.py"),
                "--resolve",
                "--repo",
                str(tree),
            ],
            STORM,
            timeout=1200,
        )
        unresolved = run(["git", "diff", "--name-only", "--diff-filter=U"], tree)[1].strip()
        picking = run(["git", "rev-parse", "-q", "--verify", "CHERRY_PICK_HEAD"], tree)[0] == 0
        if unresolved or picking:
            run(["git", "cherry-pick", "--abort"], tree)
            return f"cherry-pick failed: {out[:120]}"
    # Not `run(...)` discarding the code. A fresh worktree has no venv, and this is what
    # builds it; the pre-push hook then runs the gates inside it. When the sync failed the
    # push failed a second later with `Could not find package 'vibey'`, pytest rejecting
    # `--cov=vibey`, and pip-audit missing -- and this reported "push refused (the gates run
    # on push)", which names the wrong source. The gates never judged the code: the bench
    # they run on had not been built. A status claim names its real source (10.f).
    code, out = run(["uv", "sync", "-q", "--extra", "dev"], tree, timeout=900)
    if code:
        return f"could not build the tree's venv, so the gates never ran: {out.strip()[-140:]}"
    code, out = run(["git", "push", "-u", "origin", branch], tree, timeout=1800)
    if code:
        return f"push refused (the gates run on push): {out.strip().splitlines()[-1][:140]}"
    body = (
        f"Closes #{issue}.\n\nWritten by a sovereign lane (gpt-oss:20b) and gated at review by "
        f"`tools/lane-verify.py` plus the lane's own check block, both run again immediately "
        f"before this branch was pushed.\n\nA lane's `completed` flag is a protocol check and "
        f"not evidence (10.f), so it was not used as the gate.\n\n"
        f"🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
    )
    code, out = run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            REPO,
            "--base",
            BASE,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ],
        tree,
        timeout=300,
    )
    return f"published: {out.strip().splitlines()[-1]}" if not code else f"pr failed: {out[:120]}"


def sweep(dry: bool, only: list[str] | None) -> int:
    done = settled()
    slugs = (
        sorted(d.name for d in LANES.iterdir() if d.is_dir() and d.name not in done)
        if LANES.is_dir()
        else []
    )
    if only:
        slugs = [s for s in slugs if s in only]
    if not slugs:
        print("\n0 unsettled lane(s), 0 ready")
        return 0
    try:
        prs = storm_forge.pull_requests(MAIN, REPO, storm_forge.limit(STORM))
    except storm_forge.Unreadable as exc:
        # Not "nothing is published": nobody could find out. Publishing on that would open a
        # second pull request for work already out for review, so every lane is held.
        print(f"cannot read the forge -- {exc}")
        print(f"\n{len(slugs)} unsettled lane(s) held: which are already published is unknown")
        return 0
    published = 0
    for slug in slugs:
        ok, why = ready(slug, prs, record=not dry)
        if ok:
            print(f"READY  {slug}\n       {publish(slug, dry)}")
            published += 1
        else:
            print(f"hold   {slug}")
            for reason in why[:4]:
                print(f"       - {reason}")
            if len(why) > 4:
                print(f"       - ...and {len(why) - 4} more")
    print(f"\n{len(slugs)} unsettled lane(s), {published} ready")
    return published


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="actually commit, push and open PRs")
    parser.add_argument("--only", action="append")
    parser.add_argument("--watch", type=int, metavar="SECONDS")
    args = parser.parse_args()
    while True:
        sweep(dry=not args.publish, only=args.only)
        if not args.watch:
            return 0
        time.sleep(args.watch)


if __name__ == "__main__":
    raise SystemExit(main())
