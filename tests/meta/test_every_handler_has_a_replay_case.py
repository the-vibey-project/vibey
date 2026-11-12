# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every job handler has a replay case, or is recorded as not having one yet.

CLAUDE.md: "Every job is idempotent under replay. Workers die; the lease expires and another
worker picks it up." A handler is held to that by a ``ReplayCase`` under
``tests/application/replay/`` (``assert_replay_is_idempotent``). This census walks
``src/vibey/application/*_handler.py`` and requires each handler to be named by the ``kind``
of some ``ReplayCase(...)`` call there, or to be listed in
``tests/meta/handler_replay_exemptions.toml`` (a ratchet: stale entries fail, and ``ceiling``
must equal the list's length, so it falls in the same change that covers a handler).

Cases are found by AST (a ``ReplayCase(..., kind="...")`` call with a string-literal kind in
a ``test_*_replay.py`` file), so the census imports no test module and stays well under a
second. The census is a class so it can be run on synthetic input.
"""

import ast
import tomllib
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HANDLERS = REPO / "src" / "vibey" / "application"
REPLAY = REPO / "tests" / "application" / "replay"
EXEMPTIONS = Path(__file__).with_name("handler_replay_exemptions.toml")


class ReplayCensus:
    """Which handlers lack a case, which exemptions are stale, which cases name no handler."""

    def __init__(
        self, handlers: Iterable[str], covered: Iterable[str], exempt: Iterable[str]
    ) -> None:
        self.handlers = set(handlers)
        self.covered = set(covered)
        self.exempt = list(exempt)

    def uncovered(self) -> list[str]:
        return sorted(self.handlers - self.covered - set(self.exempt))

    def exempt_but_gone(self) -> list[str]:
        return sorted(set(self.exempt) - self.handlers)

    def exempt_but_covered(self) -> list[str]:
        return sorted(set(self.exempt) & self.covered)

    def cases_for_no_handler(self) -> list[str]:
        return sorted(self.covered - self.handlers)

    def duplicated_exemptions(self) -> list[str]:
        return sorted({name for name in self.exempt if self.exempt.count(name) > 1})

    @staticmethod
    def case_kinds(source: str) -> set[str]:
        """The string-literal ``kind=`` of each ``ReplayCase(...)`` call in ``source``."""
        kinds: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "ReplayCase":
                for keyword in node.keywords:
                    if keyword.arg == "kind" and isinstance(keyword.value, ast.Constant):
                        kinds.add(str(keyword.value.value))
        return kinds


def handler_names() -> list[str]:
    return sorted(path.stem.removesuffix("_handler") for path in HANDLERS.glob("*_handler.py"))


def covered_names() -> set[str]:
    kinds: set[str] = set()
    for path in REPLAY.glob("test_*_replay.py"):
        kinds |= ReplayCensus.case_kinds(path.read_text(encoding="utf-8"))
    return kinds


def recorded() -> tuple[int, list[str]]:
    table = tomllib.loads(EXEMPTIONS.read_text(encoding="utf-8"))
    return int(table["ceiling"]), list(table["exempt"])


def committed() -> ReplayCensus:
    return ReplayCensus(handler_names(), covered_names(), recorded()[1])


# ------------------------------------------------------------------- the repository


def test_every_handler_has_a_replay_case_or_a_recorded_exemption() -> None:
    assert committed().uncovered() == [], (
        "these handlers have no ReplayCase in tests/application/replay/: add one "
        "(assert_replay_is_idempotent), or record the handler in "
        "tests/meta/handler_replay_exemptions.toml with the reason"
    )


def test_every_exemption_names_a_handler_that_still_exists() -> None:
    assert committed().exempt_but_gone() == [], (
        "these handlers are gone: delete their entries from "
        "tests/meta/handler_replay_exemptions.toml"
    )


def test_a_handler_with_a_case_leaves_the_exemptions() -> None:
    assert committed().exempt_but_covered() == [], (
        "these handlers now have a replay case: delete their entries from "
        "tests/meta/handler_replay_exemptions.toml and lower `ceiling`"
    )


def test_every_replay_case_names_a_real_handler() -> None:
    assert committed().cases_for_no_handler() == [], (
        "these ReplayCase kinds are not src/vibey/application/<kind>_handler.py modules"
    )


def test_the_exemptions_are_unique_and_the_ceiling_is_exactly_their_number() -> None:
    ceiling, exempt = recorded()
    assert committed().duplicated_exemptions() == []
    assert ceiling == len(exempt), (
        f"`ceiling` is {ceiling} but {len(exempt)} handlers are exempt: the list can only "
        "shrink, and `ceiling` falls with it (a rise needs a written reason in review)"
    )


def test_every_exemption_carries_a_reason() -> None:
    lines = EXEMPTIONS.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("exempt = ["))
    entries = [line for line in lines[start + 1 :] if line.strip().startswith('"')]
    assert entries
    assert [line for line in entries if "#" not in line] == [], (
        "every exempt entry needs a `# reason` on its line"
    )


def test_the_census_sees_the_handlers_it_is_meant_to() -> None:
    names = handler_names()
    assert {"build_implement", "design", "visual"} <= set(names)
    assert len(names) >= 18


# --------------------------------------------------------------- the census, on synthetic input


def test_an_uncovered_handler_is_reported() -> None:
    census = ReplayCensus(["a", "b"], covered=["a"], exempt=[])
    assert census.uncovered() == ["b"]


def test_an_exempt_handler_is_not_reported_as_uncovered() -> None:
    assert ReplayCensus(["a", "b"], covered=["a"], exempt=["b"]).uncovered() == []


def test_a_stale_exemption_is_reported_both_ways() -> None:
    census = ReplayCensus(["a"], covered=["a"], exempt=["a", "gone"])
    assert census.exempt_but_covered() == ["a"]
    assert census.exempt_but_gone() == ["gone"]


def test_a_case_for_no_handler_is_reported() -> None:
    assert ReplayCensus(["a"], covered=["a", "typo"], exempt=[]).cases_for_no_handler() == ["typo"]


def test_a_duplicated_exemption_is_reported() -> None:
    assert ReplayCensus(["a"], covered=[], exempt=["a", "a"]).duplicated_exemptions() == ["a"]


def test_case_kinds_are_read_from_source_by_ast() -> None:
    source = (
        'x = ReplayCase(name="n", kind="build_verify", build=f)\n'
        'y = ReplayCase(name="n", kind=KIND, build=f)\n'
        'z = Other(kind="not_a_case")\n'
    )
    assert ReplayCensus.case_kinds(source) == {"build_verify"}
