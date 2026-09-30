# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plan's verification may only run or read files something provides (#963)."""

import pytest

from vibey.domain.effort import Effort
from vibey.domain.interfaces.plan_references_interface import (
    PlanReferenceCheckerInterface,
    ReferencingItemInterface,
)
from vibey.domain.plan import VerificationSpec, WorkItem
from vibey.domain.plan_references import (
    PLAN_REFERENCE_CHECKER,
    FileReference,
    PlanReferenceChecker,
    ReferenceUse,
    UnresolvedReference,
)

EXECUTES, READS, CREATES = ReferenceUse.EXECUTES, ReferenceUse.READS, ReferenceUse.CREATES

#: The item DECOMPOSE wrote for issue #963, verbatim from the live job's payload.
LIVE_963_COMMANDS = (
    "python generate_toc.py > toc.txt",
    "sed -i '34i ## Contents\n$(cat toc.txt)' README.md",
    "grep -n '^## Contents$' README.md | cut -d: -f1 | grep -q '^34$'",
    "grep -c '^\\* ' README.md | grep -q '^17$'",
    "python anchor_verify.py README.md",
    "git diff --stat | grep -q '^README.md' && git diff --stat | grep -q '^[+]' "
    "&& git diff --stat | grep -q '^[ ]'",
)

#: What the #963 checkout held that the plan could have named.
CHECKOUT = frozenset({"README.md", "scripts/check_docs.py", "scripts/verify.sh", "tests"})


def _exists(path: str) -> bool:
    return path in CHECKOUT or any(entry.startswith(f"{path}/") for entry in CHECKOUT)


def _item(
    item_id: str,
    *commands: str,
    depends_on: tuple[str, ...] = (),
    hint: tuple[str, ...] = (),
) -> WorkItem:
    return WorkItem(
        item_id=item_id,
        title=f"do {item_id}",
        acceptance_ids=("C1",),
        depends_on=depends_on,
        est_effort=Effort.LOW,
        files_touched_hint=hint,
        verification=VerificationSpec(commands=commands, criteria_checked=("C1",)),
    )


def test_the_checker_satisfies_its_interface() -> None:
    assert isinstance(PLAN_REFERENCE_CHECKER, PlanReferenceCheckerInterface)
    assert isinstance(_item("ws"), ReferencingItemInterface)


def test_the_live_963_plan_is_refused_naming_both_missing_scripts() -> None:
    item = _item("ws", *LIVE_963_COMMANDS, hint=("README.md",))

    unresolved = PLAN_REFERENCE_CHECKER.unresolved([item], exists=_exists)

    assert unresolved == (
        UnresolvedReference("ws", "generate_toc.py", EXECUTES, LIVE_963_COMMANDS[0]),
        UnresolvedReference("ws", "anchor_verify.py", EXECUTES, LIVE_963_COMMANDS[4]),
    )
    (violation,) = PLAN_REFERENCE_CHECKER.violations([item], exists=_exists)
    assert violation.startswith(
        "item 'ws' verification needs files nothing provides: generate_toc.py (the "
        "command 'python generate_toc.py > toc.txt' executes it); anchor_verify.py ("
    )
    assert violation.endswith("create the file and list it in files_touched_hint")


@pytest.mark.parametrize(
    "command",
    [
        "python scripts/check_docs.py README.md",
        "./scripts/verify.sh",
        "bash scripts/verify.sh --strict",
        "uv run pytest tests/ -q",
        "uv run --frozen pytest -k 'toc and not slow' tests",
        "python -m pytest -q tests",
        "grep -c '^## Contents$' README.md",
        "python3 -c 'import re; print(1)'",
        "pytest",
        "make docs",
        "cat README.md | wc -l",
        "python -m mypy src",
    ],
)
def test_commands_over_existing_files_pass(command: str) -> None:
    assert PLAN_REFERENCE_CHECKER.violations([_item("ws", command)], exists=_exists) == ()


def test_a_file_the_item_itself_declares_is_provided() -> None:
    """The walking skeleton writes the suite it is verified by; that is the plan."""
    item = _item("ws", "uv run pytest tests/test_toc.py -q", hint=("tests/test_toc.py",))
    assert PLAN_REFERENCE_CHECKER.violations([item], exists=lambda path: False) == ()


def test_a_file_a_dependency_creates_is_provided_transitively() -> None:
    items = [
        _item("ws", "true", hint=("tools/",)),
        _item("mid", "true", depends_on=("ws",)),
        _item("leaf", "python tools/gen.py", depends_on=("mid",)),
    ]
    assert PLAN_REFERENCE_CHECKER.violations(items, exists=lambda path: False) == ()


def test_a_file_only_an_unrelated_earlier_item_creates_is_not_provided() -> None:
    """Items branch from integration: a sibling's file is not in this item's worktree."""
    items = [
        _item("ws", "true", hint=("gen.py",)),
        _item("other", "python gen.py"),
    ]
    unresolved = PLAN_REFERENCE_CHECKER.unresolved(items, exists=lambda path: False)
    assert [(ref.item_id, ref.path) for ref in unresolved] == [("other", "gen.py")]


def test_a_dependency_on_an_unknown_or_repeated_item_does_not_break_the_walk() -> None:
    items = [
        _item("a", "true", depends_on=("b", "ghost"), hint=("a.py",)),
        _item("b", "python a.py", depends_on=("a",)),
    ]
    assert PLAN_REFERENCE_CHECKER.violations(items, exists=lambda path: False) == ()


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("python generate_toc.py > toc.txt", ((EXECUTES, "generate_toc.py"), (CREATES, "toc.txt"))),
        ("python3.12 -W ignore -X dev ./tools/../gen.py arg", ((EXECUTES, "gen.py"),)),
        ("env FOO=1 time node build.js", ((EXECUTES, "build.js"),)),
        ("sh -c 'python missing.py'", ()),
        ("ruby -e 'puts 1'", ()),
        (
            "python -m pytest tests/test_a.py::test_b -p no:cacheprovider",
            ((READS, "tests/test_a.py"),),
        ),
        ("python -m http.server", ()),
        ("python", ()),
        ("source env.sh && . more.sh", ((READS, "env.sh"), (READS, "more.sh"))),
        ("sort < data.csv >> out.txt", ((READS, "data.csv"), (CREATES, "out.txt"))),
        ("cmd 2>&1 | tee log.txt", ()),
        ("cat <<EOF", ()),
        ("echo $(cat a.txt); FOO=1 ./scripts/v.sh", ((READS, "a.txt"), (EXECUTES, "scripts/v.sh"))),
        ("python $SCRIPT", ()),
        ("python /usr/local/bin/tool.py", ()),
        ("python ../outside.py", ()),
        ("python *.py", ()),
        ("cat -- .", ()),
        ("pytest -q --rootdir . -k name", ()),
        ("echo 'unbalanced", ()),
        ("uv run", ()),
        ("poetry install", ()),
        ("> out.txt", ((CREATES, "out.txt"),)),
        ("cmd >", ()),
    ],
)
def test_references_are_recognised_narrowly(
    command: str, expected: tuple[tuple[ReferenceUse, str], ...]
) -> None:
    assert PlanReferenceChecker().references(command) == tuple(
        FileReference(path, use) for use, path in expected
    )


def test_a_file_created_by_an_earlier_command_of_the_same_item_is_provided() -> None:
    item = _item("ws", "echo x > made.txt", "cat made.txt", "cat never.txt")
    unresolved = PLAN_REFERENCE_CHECKER.unresolved([item], exists=lambda path: False)
    assert [(ref.path, ref.use) for ref in unresolved] == [("never.txt", READS)]
