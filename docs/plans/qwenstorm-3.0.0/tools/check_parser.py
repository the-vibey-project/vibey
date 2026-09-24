"""Reading a spec's check block: which lines are checks, where each runs, with what environment.

    parser = CheckParser()
    checks, dropped = parser.parse_checks(issue_text, lane)

Moved out of `lane-publish.py`, which still exposes `parse_checks` and `block_of` for
`lint-specs.py` -- one parser, so the linter and the publisher cannot disagree about which
lines run (10.e). A class with its declaration beside it in
`interfaces/check_parser_interface.py` (ADR-0016, sub-doctrine 9.b), as `lane_environment.py`
and `storm_trust.py` do in this directory; `tests/meta/test_storm_check_parser.py` holds the
class to it method by method. Underscored because it is imported, not run.
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import NamedTuple


class Check(NamedTuple):
    """One command a lane's spec asks for, and the two things that decide what it means."""

    argv: list[str]
    cwd: Path
    env: dict[str, str]
    unset: tuple[str, ...] = ()  # names `env -u` removes, for this command alone


class CheckParser:
    """Turns a spec's check block into runnable checks and a list of every line it dropped."""

    # Commands a lane's check block may name that the publisher will run. Anything else is
    # reported as dropped rather than executed: a spec is written by a model, and a
    # publishing step is not the place to run whatever a model happened to type. `black`
    # and `isort` are here because CI's `tools-lint` checks the gh tenant with both, and
    # `bandit` because CI gates on it -- a check this list does not name never runs, and
    # holds its lane for that.
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

    def block_of(self, text: str) -> str | None:
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
            return "\n".join(
                line for line in section.splitlines() if line.startswith(("    ", "\t"))
            )
        # Everything after the opening fence begins with its info string -- "bash" -- which is
        # not a check. Stripping backticks off the raw line cannot remove it, because by then it
        # no longer looks like a fence.
        inside_fence = section.split("```", 1)[1].split("\n", 1)[-1]
        return inside_fence.split("```", 1)[0] if "```" in inside_fence else inside_fence

    def parse_checks(self, text: str, lane: Path) -> tuple[list[Check], list[tuple[str, str]]]:
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
        block = self.block_of(text)
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
            command = self.ANNOTATION.sub("", line).strip()
            try:
                parts = self.tokens(command)
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
                    dropped.append(
                        (line, f"needs a shell ({shell[0]}) and the lane's tool has none")
                    )
                    continue
                if parts[0] == "export":
                    parts = parts[
                        1:
                    ]  # `export FOO=bar` sets FOO for what follows, and runs nothing
                # `FOO=bar cmd ...` and a bare `export FOO=bar` are the same syntax: leading
                # assignments. 261 `export` lines and 96 `VAR=value cmd` prefixes were dropped
                # for being "not a command", which is true of the first token and not of the line.
                env = dict(scope)
                unset: list[str] = []
                parts, why = self.assigned(parts, env)
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
                        parts, why = self.assigned(parts, env)
                    if why is None and not parts:
                        continue  # `env` with nothing to run changes nothing that persists
                if why is not None:
                    dropped.append((line, why))
                    continue
                if not parts:
                    scope = env  # nothing left to run: it was an `export`, so it persists
                    continue
                if parts[0] == "cd":
                    moved = self.inside(lane, run_from, parts[1]) if len(parts) == 2 else None
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
                if parts[0] in self.SAFE:
                    where_it_runs = (
                        self.where(lane, raw) if self.ANNOTATION.search(raw) else run_from
                    )
                    found.append(Check(parts, where_it_runs, env, tuple(unset)))
                else:
                    dropped.append((line, f"{parts[0]!r} is not a command this runs"))
            if not subshell:
                exported = scope
            if stop:
                break
        return found, dropped

    def tokens(self, command: str) -> list[str]:
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

    def expand(self, value: str, known: dict[str, str]) -> str | None:
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
                return self.PARAMETER.sub(one, fallback)
            return current or ""

        out = self.PARAMETER.sub(one, value)
        return None if "$" in out or "`" in out else out

    def assigned(self, parts: list[str], env: dict[str, str]) -> tuple[list[str], str | None]:
        """Consume leading `NAME=value` words into `env`: what is left, or why it cannot be run."""
        while parts and self.ASSIGNMENT.match(parts[0]):
            name, _, value = parts[0].partition("=")
            expanded = self.expand(value, {**os.environ, **env})
            if expanded is None:
                return parts, f"`{name}=` uses a shell expansion this does not perform"
            env[name] = expanded
            parts = parts[1:]
        return parts, None

    def where(self, lane: Path, raw: str) -> Path:
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
        return self.inside(lane, lane, found.group(1)) or lane if found else lane

    def inside(self, lane: Path, base: Path, target: str) -> Path | None:
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
