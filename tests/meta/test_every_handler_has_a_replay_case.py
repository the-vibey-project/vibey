# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every job handler has a replay case, or is recorded as not having one yet.

CLAUDE.md: "Every job is idempotent under replay. Workers die; the lease expires and another
worker picks it up." A handler is held to that by a ``ReplayCase`` under
``tests/application/replay/`` (``assert_replay_is_idempotent``). This census walks
``src/vibey/application/*.py`` for the classes that are job handlers (an ``async def handle``
taking a ``JobRecord``: the registered handlers in ``bootstrap.py``, ``deploy_design_bridge``
and ``deploy_review_routing`` among them, not only the modules named ``*_handler.py``), keys each
by its module name without a ``_handler`` suffix, and requires each handler to be named by the ``kind``
of some ``ReplayCase(...)`` call there, or to be listed in
``tests/meta/handler_replay_exemptions.toml`` (a ratchet: stale entries fail, and ``CEILING``
(a constant in this file) must equal the list's length, so it falls in the same change that covers a handler).

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

CEILING = 4
"""The most handlers that may be exempt. It lives here, not in the TOML, so that a change to
the list cannot also move its own limit: lower it in the same change that covers a handler,
and never raise it without a written reason in review."""


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
    def _is_case_call(node: ast.AST) -> bool:
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        return (isinstance(func, ast.Name) and func.id == "ReplayCase") or (
            isinstance(func, ast.Attribute) and func.attr == "ReplayCase"
        )

    @classmethod
    def case_kinds(cls, source: str) -> set[str]:
        """The string-literal ``kind=`` of each ``ReplayCase(...)`` call inside the module's
        ``CASES = ...`` assignment, and only if a ``pytest.mark.parametrize`` over ``CASES``
        runs them. A case defined anywhere else, or defined in CASES but never parametrized,
        is not one that runs and does not count."""
        tree = ast.parse(source)
        runs_cases = any(
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", "") == "parametrize"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Name)
            and node.args[1].id == "CASES"
            for node in ast.walk(tree)
        )
        if not runs_cases:
            return set()
        kinds: set[str] = set()
        for node in ast.walk(tree):
            targets = (
                [node.target]
                if isinstance(node, ast.AnnAssign)
                else getattr(node, "targets", [])
                if isinstance(node, ast.Assign)
                else []
            )
            if any(isinstance(t, ast.Name) and t.id == "CASES" for t in targets) and node.value:
                for call in ast.walk(node.value):
                    if cls._is_case_call(call):
                        for keyword in call.keywords:  # type: ignore[attr-defined]
                            if keyword.arg == "kind" and isinstance(keyword.value, ast.Constant):
                                kinds.add(str(keyword.value.value))
        return kinds


def defines_a_job_handler(source: str) -> bool:
    """Whether the module has a class with ``async def handle(self, job: JobRecord)``."""
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        for member in node.body:
            if (
                isinstance(member, ast.AsyncFunctionDef)
                and member.name == "handle"
                and len(member.args.args) >= 2
                and isinstance(member.args.args[1].annotation, ast.Name)
                and member.args.args[1].annotation.id == "JobRecord"
            ):
                return True
    return False


def handler_names() -> list[str]:
    return sorted(
        path.stem.removesuffix("_handler")
        for path in HANDLERS.glob("*.py")
        if defines_a_job_handler(path.read_text(encoding="utf-8"))
    )


def covered_names() -> set[str]:
    kinds: set[str] = set()
    for path in REPLAY.glob("test_*_replay.py"):
        kinds |= ReplayCensus.case_kinds(path.read_text(encoding="utf-8"))
    return kinds


def recorded() -> list[str]:
    table = tomllib.loads(EXEMPTIONS.read_text(encoding="utf-8"))
    return list(table["exempt"])


def committed() -> ReplayCensus:
    return ReplayCensus(handler_names(), covered_names(), recorded())


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
        "tests/meta/handler_replay_exemptions.toml and lower `CEILING`"
    )


def test_every_replay_case_names_a_real_handler() -> None:
    assert committed().cases_for_no_handler() == [], (
        "these ReplayCase kinds are not src/vibey/application/<kind>_handler.py modules"
    )


def test_the_exemptions_are_unique_and_the_ceiling_is_exactly_their_number() -> None:
    exempt = recorded()
    assert committed().duplicated_exemptions() == []
    assert len(exempt) == CEILING, (
        f"CEILING is {CEILING} but {len(exempt)} handlers are exempt: the list can only "
        "shrink, and CEILING falls with it (a rise needs a written reason in review)"
    )


EXEMPT_FOR_A_STATED_REASON = {
    "bus_dead_letter": "at-least-once",
    "build_dependency_wait": "Defer",
    "engine_selection": "wraps",
    "job_dispatcher": "routes",
}


def test_only_the_wrappers_and_the_dead_letter_are_exempt_each_for_its_stated_reason() -> None:
    """Every job handler has a replay case. The census accepts a reason-bearing entry for
    these four names only: three wrappers that delegate to a handler that has its own case, and
    the dead-letter handler, which is a leased job but whose documented contract is
    at-least-once (a replay publishes the body again; an answer it cannot use re-parks), so
    equality of what a redelivery leaves is not its invariant. Any other handler needs a case."""
    assert sorted(recorded()) == sorted(EXEMPT_FOR_A_STATED_REASON)
    lines = EXEMPTIONS.read_text(encoding="utf-8").splitlines()
    for name, word in EXEMPT_FOR_A_STATED_REASON.items():
        (entry,) = [line for line in lines if line.strip().startswith(f'"{name}"')]
        assert word in entry.split("#", 1)[1], f"{name}: the reason should say {word!r}"


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
    # Job handlers that are not named *_handler.py are in it too.
    assert {"deploy_design_bridge", "deploy_review_routing", "job_dispatcher"} <= set(names)
    assert len(names) >= 23


def test_a_module_defining_a_job_handler_is_recognised_by_its_signature_not_its_name() -> None:
    handler = "class Anything:\n    async def handle(self, job: JobRecord) -> Outcome: ...\n"
    assert defines_a_job_handler(handler)
    assert not defines_a_job_handler("class A:\n    async def handle(self, event: Event): ...\n")
    assert not defines_a_job_handler("class A:\n    def handle(self, job: JobRecord): ...\n")
    assert not defines_a_job_handler("async def handle(job: JobRecord): ...\n")


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
        "CASES = (\n"
        '    ReplayCase(name="n", kind="build_verify", build=f),\n'
        '    harness.ReplayCase(name="n", kind="design", build=f),\n'
        '    ReplayCase(name="n", kind=KIND, build=f),\n'
        '    Other(kind="not_a_case"),\n'
        ")\n"
        '@pytest.mark.parametrize("case", CASES)\n'
        "def test_it(case): ...\n"
    )
    assert ReplayCensus.case_kinds(source) == {"build_verify", "design"}


def test_a_case_outside_cases_or_never_parametrized_does_not_count() -> None:
    outside = (
        'CASES = ()\nSTRAY = ReplayCase(name="n", kind="design", build=f)\n'
        '@pytest.mark.parametrize("case", CASES)\ndef test_it(case): ...\n'
    )
    never_run = 'CASES = (ReplayCase(name="n", kind="design", build=f),)\n'
    assert ReplayCensus.case_kinds(outside) == set()
    assert ReplayCensus.case_kinds(never_run) == set()
