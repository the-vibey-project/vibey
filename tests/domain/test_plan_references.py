# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plan's verification may only run or read files something provides (#963)."""

from dataclasses import replace

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


@pytest.mark.parametrize(
    "command",
    [
        "pytest -q tests/__tests__/ministry.test.ts",
        "python -m pytest src/x.test.tsx::case",
        "py.test -x src/a.mjs",
        "FOO=1 pytest src/app/page.js",
    ],
)
def test_pytest_pointed_at_a_typescript_or_javascript_file_is_rejected(command: str) -> None:
    (message,) = PLAN_REFERENCE_CHECKER.violations(
        [_item("ws", command, hint=("src/a.mjs",))], exists=lambda path: True
    )

    assert "item 'ws' runs pytest on" in message
    assert "is not a Python file" in message
    assert "npm script" in message


def test_pytest_on_python_files_and_other_runners_on_typescript_are_left_alone() -> None:
    items = [
        _item("a", "pytest -q tests/test_x.py::test_a", "python -m pytest tests/"),
        _item("b", "npm test -- src/x.test.ts", "npx vitest run src/x.test.ts"),
        _item("c", "python -m unittest", "echo pytest src/x.ts", "pytest"),
    ]

    assert PLAN_REFERENCE_CHECKER.violations(items, exists=lambda path: True) == ()


def test_the_wrong_files_are_listed_once_per_item_next_to_any_missing_files() -> None:
    item = _item("ws", "pytest src/a.test.ts", "pytest src/a.test.ts src/b.test.ts", "node gone.js")

    missing, wrong = PLAN_REFERENCE_CHECKER.violations(
        [item], exists=lambda path: path != "gone.js"
    )

    assert "needs files nothing provides" in missing
    assert "runs pytest on src/a.test.ts, src/b.test.ts," in wrong


def test_empty_segments_between_separators_are_skipped_by_the_pytest_check() -> None:
    item = _item("ws", "; pytest tests/test_a.py ;; && echo done")

    assert PLAN_REFERENCE_CHECKER.violations([item], exists=lambda path: True) == ()


def _paths(count: int) -> tuple[str, ...]:
    return tuple(f"src/file_{n}.ts" for n in range(count))


def test_how_many_paths_an_item_lists_is_not_limited() -> None:
    """Plan size follows the spec. A large item is the planner's call, so it is not re-asked."""
    big = _item("ws", "npm run build", hint=_paths(40))

    assert PLAN_REFERENCE_CHECKER.violations([big], exists=lambda path: True) == ()


def _claiming(item_id: str, *ids: str, hint: tuple[str, ...] = ()) -> WorkItem:
    return replace(_item(item_id, "npm run build", hint=hint), acceptance_ids=ids)


def test_how_many_criteria_an_item_claims_is_not_limited() -> None:
    """One item may claim every criterion when its paths make them true; the ministry
    section's plans were re-asked for it, and the re-ask dictated a chain of pieces."""
    wide = _claiming("ws", *(f"C{n}" for n in range(1, 12)), hint=_paths(3))

    assert PLAN_REFERENCE_CHECKER.violations([wide], exists=lambda path: True) == ()


def test_a_chain_that_spreads_the_criteria_is_accepted() -> None:
    items = [
        _claiming("ws", "C1", "C2", "C3", hint=_paths(4)),
        replace(_claiming("pages", "C4", "C5", "C6", hint=_paths(5)), depends_on=("ws",)),
        replace(_claiming("polish", "C7", "C8", "C9", "C10", "C11"), depends_on=("pages",)),
    ]

    assert PLAN_REFERENCE_CHECKER.violations(items, exists=lambda path: True) == ()
