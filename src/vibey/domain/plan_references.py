# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plan's verification may only run or read files something provides.

Measured live on 2026-09-30 (project 893c4fc1, issue #963, a pure insertion into
README.md): DECOMPOSE wrote an item verified by `python generate_toc.py > toc.txt` and
`python anchor_verify.py README.md`. Neither script existed, and no item created them.
The BUILD engine spent its turns searching for them and opening them (`No such file or
directory`) until the turn cap -- four attempts, no deliverable. A plan that names a
file nothing provides is unbuildable as written, and that is decidable before BUILD
starts, from the plan and the checkout alone.

The rule, small enough to explain from the record:

    every file an item's verification command executes or reads must already exist in
    the checkout, or be created by the item itself or an item it depends on (listed in
    its `files_touched_hint`), or be written by an earlier command of the same item.

"Executes or reads" is recognised narrowly, so the check stays conservative: the script
an interpreter runs (`python x.py`, `bash x.sh`, `node x.js` ...), a program named by a
path (`./scripts/check.sh`), a pytest target (`pytest tests/test_x.py::test_a`), a
sourced file, `cat`'s operands and an input redirection (`< x`). A bare command name is
a PATH lookup, not a checkout file; an argument to a script is the script's business;
anything with a variable, a glob or a home directory in it, an absolute path, or a path
outside the checkout is left alone; and a command the shell grammar cannot split is
skipped. A missed reference leaves the plan as it was before this check; a flagged one
names the file, the command, and what would satisfy it.

Its own dependencies count, not merely items listed earlier: an item branches from the
integration branch, which holds only what its dependencies merged, so a file an
unrelated earlier item creates is not in its worktree.
"""

import posixpath
import shlex
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from vibey.domain.interfaces.plan_references_interface import (
    PlanReferenceCheckerInterface,
    ReferencingItemInterface,
)


class ReferenceUse(StrEnum):
    """What a command does with a file it names."""

    EXECUTES = "executes"
    READS = "reads"
    CREATES = "creates"


@dataclass(frozen=True, slots=True)
class FileReference:
    """One checkout-relative path a command names, and what it does with it."""

    path: str
    use: ReferenceUse


@dataclass(frozen=True, slots=True)
class UnresolvedReference:
    """A file an item's verification needs that nothing provides."""

    item_id: str
    path: str
    use: ReferenceUse
    command: str


# Interpreters whose first non-option operand is the program they run, and the option
# that makes them run inline code instead (then no file is named).
_INTERPRETERS: Final[Mapping[str, str]] = {
    "python": "-c",
    "python3": "-c",
    "pypy": "-c",
    "pypy3": "-c",
    "bash": "-c",
    "sh": "-c",
    "zsh": "-c",
    "dash": "-c",
    "ksh": "-c",
    "node": "-e",
    "ruby": "-e",
    "perl": "-e",
}
# Interpreter options that consume the next word as their value.
_VALUED_OPTIONS: Final[frozenset[str]] = frozenset({"-W", "-X", "-o", "-O"})
# pytest options that consume the next word as their value.
_PYTEST_VALUED: Final[frozenset[str]] = frozenset(
    {"-k", "-m", "-p", "-c", "-o", "-W", "-n", "--rootdir", "--confcutdir", "--basetemp"}
)
# Commands every operand of which is a file they read.
_READERS: Final[frozenset[str]] = frozenset({"cat", "source", "."})
# Prefixes that run the command after them unchanged.
_WRAPPERS: Final[frozenset[str]] = frozenset({"env", "time", "exec", "command", "nice", "nohup"})
# Runners whose `run` subcommand runs the command after it: `uv run pytest`.
_RUNNERS: Final[frozenset[str]] = frozenset({"uv", "poetry", "pipenv", "pdm", "hatch"})
_SEPARATOR_CHARACTERS: Final[frozenset[str]] = frozenset("();|&")
_OUTPUT_REDIRECTS: Final[frozenset[str]] = frozenset({">", ">>", ">|", "&>", "&>>"})
_UNRESOLVABLE: Final[frozenset[str]] = frozenset("$*?[{~`")


class PlanReferenceChecker:
    """Finds the files a plan's verification executes or reads that nothing provides.

    Pure and stateless: the plan and an existence predicate over checkout-relative
    paths in, the unresolved references out. The predicate is the only view of the
    checkout, so this never touches a filesystem itself.
    """

    def references(self, command: str) -> tuple[FileReference, ...]:
        found: list[FileReference] = []
        for words, reads, writes in self._segments(command):
            found.extend(FileReference(path, ReferenceUse.READS) for path in reads)
            found.extend(self._operands(words))
            found.extend(FileReference(path, ReferenceUse.CREATES) for path in writes)
        return tuple(found)

    def unresolved(
        self,
        items: Sequence[ReferencingItemInterface],
        *,
        exists: Callable[[str], bool],
    ) -> tuple[UnresolvedReference, ...]:
        by_id = {item.item_id: item for item in items}
        missing: list[UnresolvedReference] = []
        for item in items:
            declared = self._declared(item, by_id)
            written: set[str] = set()
            for command in item.verification.commands:
                for reference in self.references(command):
                    if reference.use is ReferenceUse.CREATES:
                        written.add(reference.path)
                        continue
                    provided = (
                        reference.path in written
                        or self._declares(declared, reference.path)
                        or exists(reference.path)
                    )
                    if not provided:
                        missing.append(
                            UnresolvedReference(
                                item.item_id, reference.path, reference.use, command
                            )
                        )
        return tuple(missing)

    def violations(
        self,
        items: Sequence[ReferencingItemInterface],
        *,
        exists: Callable[[str], bool],
    ) -> tuple[str, ...]:
        grouped: dict[str, list[UnresolvedReference]] = {}
        for reference in self.unresolved(items, exists=exists):
            grouped.setdefault(reference.item_id, []).append(reference)
        return tuple(
            f"item {item_id!r} verification needs files nothing provides: "
            + "; ".join(
                f"{reference.path} (the command {reference.command!r} {reference.use} it)"
                for reference in references
            )
            + ". Each is neither in the checkout nor listed in files_touched_hint by this "
            "item or an item it depends on: verify only with files that exist, or have "
            "this item (or one it depends on) create the file and list it in "
            "files_touched_hint"
            for item_id, references in grouped.items()
        )

    def _declared(
        self, item: ReferencingItemInterface, by_id: Mapping[str, ReferencingItemInterface]
    ) -> frozenset[str]:
        """The paths the item and every item it transitively depends on declare."""
        declared: set[str] = set()
        seen: set[str] = set()
        pending = [item.item_id]
        while pending:
            current = by_id.get(pending.pop())
            if current is None or current.item_id in seen:
                continue
            seen.add(current.item_id)
            declared.update(
                path for hint in current.files_touched_hint if (path := self._path(hint))
            )
            pending.extend(current.depends_on)
        return frozenset(declared)

    @staticmethod
    def _declares(declared: frozenset[str], path: str) -> bool:
        """Whether a declared path is this file or a directory holding it."""
        return any(path == entry or path.startswith(f"{entry}/") for entry in declared)

    def _segments(self, command: str) -> Iterator[tuple[list[str], list[str], list[str]]]:
        """Each simple command: its words, the files it redirects in, the files it
        redirects out. Nothing when the command cannot be split."""
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        try:
            parts = list(lexer)
        except ValueError:
            return
        words: list[str] = []
        reads: list[str] = []
        writes: list[str] = []
        index = 0
        while index < len(parts):
            part = parts[index]
            if part in _OUTPUT_REDIRECTS or part == "<":
                target = parts[index + 1] if index + 1 < len(parts) else ""
                if path := self._path(target):
                    (reads if part == "<" else writes).append(path)
                index += 2
                continue
            if part.startswith(("<", ">")):
                # `>&` duplicates a descriptor and `<<` opens a here-document: the word
                # after either is not a file in the checkout.
                index += 2
                continue
            if set(part) <= _SEPARATOR_CHARACTERS:
                yield words, reads, writes
                words, reads, writes = [], [], []
            else:
                words.append(part)
            index += 1
        yield words, reads, writes

    def _operands(self, words: list[str]) -> Iterator[FileReference]:
        """The files one simple command executes or reads by its own arguments."""
        words = self._unwrapped(words)
        if not words:
            return
        program, arguments = words[0], words[1:]
        name = posixpath.basename(program)
        interpreter = self._interpreter(name)
        if interpreter is not None:
            yield from self._interpreted(interpreter, arguments)
        elif name in {"pytest", "py.test"}:
            yield from self._pytest_targets(arguments)
        elif name in _READERS:
            for argument in arguments:
                if path := self._path(argument):
                    yield FileReference(path, ReferenceUse.READS)
        elif "/" in program and (path := self._path(program)):
            yield FileReference(path, ReferenceUse.EXECUTES)

    def _interpreted(self, inline: str, arguments: list[str]) -> Iterator[FileReference]:
        index = 0
        while index < len(arguments):
            argument = arguments[index]
            if argument == inline:
                return
            if argument == "-m":
                if arguments[index + 1 : index + 2] == ["pytest"]:
                    yield from self._pytest_targets(arguments[index + 2 :])
                return
            if argument.startswith("-"):
                index += 2 if argument in _VALUED_OPTIONS else 1
                continue
            if path := self._path(argument):
                yield FileReference(path, ReferenceUse.EXECUTES)
            return

    def _pytest_targets(self, arguments: list[str]) -> Iterator[FileReference]:
        index = 0
        while index < len(arguments):
            argument = arguments[index]
            index += 1
            if argument in _PYTEST_VALUED:
                index += 1
                continue
            target = argument.partition("::")[0]
            if (target.endswith(".py") or "/" in target) and (path := self._path(target)):
                yield FileReference(path, ReferenceUse.READS)

    @staticmethod
    def _interpreter(name: str) -> str | None:
        """The inline-code option of the interpreter `name` is, or None if it is none.
        A versioned name (`python3.12`) is its interpreter."""
        if name in _INTERPRETERS:
            return _INTERPRETERS[name]
        stem = name.rstrip("0123456789.")
        return _INTERPRETERS.get(stem) if stem != name else None

    @staticmethod
    def _unwrapped(words: list[str]) -> list[str]:
        """The command itself: leading assignments and pass-through wrappers removed."""
        index = 0
        while index < len(words):
            word = words[index]
            if "=" in word and not word.startswith(("-", "/", ".")) or word in _WRAPPERS:
                index += 1
            elif word in _RUNNERS and words[index + 1 : index + 2] == ["run"]:
                index += 2
                while index < len(words) and words[index].startswith("-"):
                    index += 1
            else:
                break
        return words[index:]

    @staticmethod
    def _path(raw: str) -> str | None:
        """A checkout-relative path, or None when the word cannot be resolved to one."""
        if not raw or raw.startswith(("/", "-")) or not _UNRESOLVABLE.isdisjoint(raw):
            return None
        path = posixpath.normpath(raw)
        if path in {".", ".."} or path.startswith("../"):
            return None
        return path


PLAN_REFERENCE_CHECKER: Final[PlanReferenceCheckerInterface] = PlanReferenceChecker()
"""The checker every decomposition is judged by. Stateless."""
