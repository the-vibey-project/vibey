# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The CI jobs consume the plan, and no row, required check or gate goes missing (SP1-B).

A SKIPPED required check counts as passing on GitHub, so a wrong skip is silent. These tests are
the proof that the skips ci.yml now makes are the ones the diff asks for and no others:

* the PR and full tiers together are exactly today's matrices (a pinned snapshot), and the PR
  tier is a subset of the full tier, so a row is moved, never lost;
* every job-level `if:` reads only the plan's outputs, plus `uv-lock` and `lint` results and
  `cancelled()`. It never uses `always()` and never reads another job's result, so a `lint`
  failure still skips the heavy jobs and a failed, timed-out or cancelled `plan` cannot;
* the expressions are EVALUATED, by a small evaluator for the subset GitHub's expression
  language they use, with the plan's outputs absent and with its defaults: every dependant must
  run. The evaluator refuses any function or context outside that subset, so a later edit cannot
  slip a construct past it that these tests never ran;
* `gates` always runs, and the two VS Code names stay byte-identical to the required checks.

The evaluator is a class and the checks are module-level functions: pytest collects functions
(ADR-0016 permits it).
"""

import json
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml
from vibey_gh.ci_areas import CiAreas

from .ci_matrix_rows import CiMatrixRows

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
SNAPSHOT = REPO / "tests" / "meta" / "ci_matrix_snapshot.json"
VIBEY_GH = REPO / ".vibey-gh.toml"

# Every job whose `if:` reads the plan, with the needs it has besides `plan` (what the implicit
# `success()` used to test and the `if:` now tests by name).
AREA_JOBS: dict[str, tuple[str, ...]] = {
    "noloss": ("uv-lock", "lint"),
    "postgres-compatibility": ("uv-lock", "lint"),
    "tools": ("uv-lock", "lint"),
    "tools-lint": ("uv-lock", "lint"),
    "image": ("lint",),
    "cluster-smoke": ("lint",),
    "krypton-app": (),
    "vibey-core": (),
    "app": (),
    "vscode-extension-ubuntu": (),
    "vscode-extension-macos": (),
    "desktop": (),
    "chart": (),
}
MATRIX_JOBS = {
    "tools": "tools",
    "postgres-compatibility": "postgres",
    "desktop": "desktop",
}
VSCODE_NAMES = {
    "vscode-extension-ubuntu": "VS Code extension (ubuntu-latest)",
    "vscode-extension-macos": "VS Code extension (macos-latest)",
}
# `ci-result` is the one job that must run after a failure: its `always()` is the point.
ALWAYS_JOBS = {"ci-result"}
PLAN_OUTPUTS = (
    "areas",
    "full",
    "tier",
    "tools_any",
    "postgres_any",
    "desktop_any",
    "tools_matrix",
    "postgres_matrix",
    "desktop_matrix",
)


class ExpressionError(ValueError):
    """An expression uses something the evaluator does not model."""


class ExpressionEvaluator:
    """Parses and evaluates the subset of GitHub's expression language ci.yml's `if:` uses.

    Supported: single-quoted strings, `!`, `&&`, `||`, `==`, `!=`, parentheses,
    `cancelled()`, `contains(a, b)`, `fromJSON(s)`, `needs.<job>.result` and
    `needs.plan.outputs.<name>`. `&&` and `||` return an operand, as GitHub's do, and an empty
    string and `null` are falsy, `'false'` is truthy. Anything else raises `ExpressionError`:
    a function, a context or an operator outside the subset is never silently treated as true.
    """

    FUNCTIONS = ("cancelled", "contains", "fromJSON")
    _TOKEN = re.compile(
        r"""\s*(?:
            (?P<string>'(?:[^']|'')*')
          | (?P<op>&&|\|\||==|!=|!|\(|\)|,)
          | (?P<name>[A-Za-z_][A-Za-z0-9_\-]*(?:\.[A-Za-z_][A-Za-z0-9_\-]*)*)
        )""",
        re.VERBOSE,
    )

    def __init__(self, expression: str) -> None:
        self.source = expression.strip()
        self._tokens = self._tokenise(self.source)
        self._at = 0
        self.tree = self._or()
        if self._at != len(self._tokens):
            raise ExpressionError(f"unparsed tail in {expression!r}: {self._tokens[self._at :]}")

    # -- parsing ---------------------------------------------------------------------------

    @classmethod
    def _tokenise(cls, text: str) -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = []
        at = 0
        while at < len(text):
            if text[at:].strip() == "":
                break
            match = cls._TOKEN.match(text, at)
            if match is None:
                raise ExpressionError(f"cannot tokenise {text[at:]!r} in {text!r}")
            kind = str(match.lastgroup)
            tokens.append((kind, match.group(kind)))
            at = match.end()
        return tokens

    def _peek(self) -> tuple[str, str]:
        return self._tokens[self._at] if self._at < len(self._tokens) else ("end", "")

    def _take(self, value: str | None = None) -> tuple[str, str]:
        token = self._peek()
        if value is not None and token[1] != value:
            raise ExpressionError(f"expected {value!r}, found {token[1]!r} in {self.source!r}")
        self._at += 1
        return token

    def _or(self) -> tuple[Any, ...]:
        left = self._and()
        while self._peek() == ("op", "||"):
            self._take()
            left = ("or", left, self._and())
        return left

    def _and(self) -> tuple[Any, ...]:
        left = self._eq()
        while self._peek() == ("op", "&&"):
            self._take()
            left = ("and", left, self._eq())
        return left

    def _eq(self) -> tuple[Any, ...]:
        left = self._not()
        while self._peek() in (("op", "=="), ("op", "!=")):
            operator = self._take()[1]
            left = ("eq" if operator == "==" else "ne", left, self._not())
        return left

    def _not(self) -> tuple[Any, ...]:
        if self._peek() == ("op", "!"):
            self._take()
            return ("not", self._not())
        return self._primary()

    def _primary(self) -> tuple[Any, ...]:
        kind, value = self._take()
        if kind == "string":
            return ("str", value[1:-1].replace("''", "'"))
        if (kind, value) == ("op", "("):
            inner = self._or()
            self._take(")")
            return inner
        if kind != "name":
            raise ExpressionError(f"unexpected {value!r} in {self.source!r}")
        if self._peek() == ("op", "("):
            if value not in self.FUNCTIONS:
                raise ExpressionError(f"function {value!r} is outside the evaluated subset")
            self._take("(")
            args: list[tuple[Any, ...]] = []
            if self._peek() != ("op", ")"):
                args.append(self._or())
                while self._peek() == ("op", ","):
                    self._take()
                    args.append(self._or())
            self._take(")")
            return ("call", value, tuple(args))
        parts = value.split(".")
        is_result = len(parts) == 3 and parts[0] == "needs" and parts[2] == "result"
        is_output = len(parts) == 4 and parts[:2] == ["needs", "plan"] and parts[2] == "outputs"
        if not (is_result or is_output):
            raise ExpressionError(f"context {value!r} is outside the evaluated subset")
        return ("ref", value)

    # -- what it reads -----------------------------------------------------------------------

    def references(self) -> set[str]:
        found: set[str] = set()

        def walk(node: tuple[Any, ...]) -> None:
            if node[0] == "ref":
                found.add(node[1])
            elif node[0] == "call":
                found.add(f"{node[1]}()")
                for arg in node[2]:
                    walk(arg)
            elif node[0] in ("and", "or", "eq", "ne"):
                walk(node[1])
                walk(node[2])
            elif node[0] == "not":
                walk(node[1])

        walk(self.tree)
        return found

    def conjuncts(self) -> list[str]:
        """The top-level `&&` operands, as source-like text, in order."""
        terms: list[tuple[Any, ...]] = []

        def flatten(node: tuple[Any, ...]) -> None:
            if node[0] == "and":
                flatten(node[1])
                flatten(node[2])
            else:
                terms.append(node)

        flatten(self.tree)
        return [self._show(term) for term in terms]

    def _show(self, node: tuple[Any, ...]) -> str:
        kind = node[0]
        if kind == "str":
            return "'" + str(node[1]) + "'"
        if kind == "ref":
            return str(node[1])
        if kind == "call":
            return f"{node[1]}({', '.join(self._show(a) for a in node[2])})"
        if kind == "not":
            return "!" + self._show(node[1])
        symbol = {"and": "&&", "or": "||", "eq": "==", "ne": "!="}[kind]
        return f"({self._show(node[1])} {symbol} {self._show(node[2])})"

    # -- evaluation ----------------------------------------------------------------------------

    @staticmethod
    def _truthy(value: Any) -> bool:
        return value not in (None, "", 0, False)

    def evaluate(
        self, results: Mapping[str, str], outputs: Mapping[str, str], cancelled: bool
    ) -> bool:
        return self._truthy(self._value(self.tree, results, outputs, cancelled))

    def _value(
        self,
        node: tuple[Any, ...],
        results: Mapping[str, str],
        outputs: Mapping[str, str],
        cancelled: bool,
    ) -> Any:
        kind = node[0]

        def go(child: tuple[Any, ...]) -> Any:
            return self._value(child, results, outputs, cancelled)

        if kind == "str":
            return node[1]
        if kind == "ref":
            parts = str(node[1]).split(".")
            if parts[2] == "result":
                return results.get(parts[1], "")
            return outputs.get(parts[3], "")
        if kind == "not":
            return not self._truthy(go(node[1]))
        if kind == "and":
            left = go(node[1])
            return left if not self._truthy(left) else go(node[2])
        if kind == "or":
            left = go(node[1])
            return left if self._truthy(left) else go(node[2])
        if kind in ("eq", "ne"):
            same = str(go(node[1])).lower() == str(go(node[2])).lower()
            return same if kind == "eq" else not same
        name, args = node[1], [go(arg) for arg in node[2]]
        if name == "cancelled":
            return cancelled
        if name == "fromJSON":
            if args[0] == "" or args[0] is None:
                raise ExpressionError("fromJSON of an empty string: GitHub fails the expression")
            return json.loads(str(args[0]))
        needle = str(args[1]).lower()
        haystack = args[0]
        if isinstance(haystack, list):
            return any(str(item).lower() == needle for item in haystack)
        return needle in str(haystack).lower()


# ------------------------------------------------------------------------------- the workflow


def _jobs() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    return loaded


def _needs(job: str) -> list[str]:
    needs = _jobs()[job].get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


def _if_text(job: str) -> str:
    """The job's `if:` without its `${{ }}` wrapper (a bare `!` would be a YAML tag)."""
    text = str(_jobs()[job]["if"]).strip()
    match = re.fullmatch(r"\$\{\{ (.*) \}\}", text, re.DOTALL)
    assert match, f"{job}: the `if:` must be written as ${{{{ ... }}}}"
    return match.group(1)


def _expression(job: str) -> ExpressionEvaluator:
    return ExpressionEvaluator(_if_text(job))


def _default_outputs() -> dict[str, str]:
    """The plan's outputs when its `cli` step never ran: what its first step writes."""
    steps = _jobs()["plan"]["steps"]
    script = str(steps[0]["run"])
    written: dict[str, str] = {}
    for line in script.splitlines():
        match = re.match(r"^\s*(?:echo\s+)?\"?([a-z_]+)=(.*?)\"?\s*$", line)
        if match and match.group(1) in PLAN_OUTPUTS:
            written[match.group(1)] = match.group(2)
    return written


def _runs(job: str, outputs: Mapping[str, str], **results: str) -> bool:
    every = {"uv-lock": "success", "lint": "success", "plan": "success", **results}
    return _expression(job).evaluate(every, outputs, cancelled=False)


def _outputs_for(
    paths: list[str], event: str = "pull_request", base_ref: str = "develop"
) -> dict[str, str]:
    areas = CiAreas.load(REPO / ".github" / "ci-areas.toml", REPO / ".github" / "ci-matrices.toml")
    return areas.outputs(areas.classify(paths, event=event, base_ref=base_ref))


def _would_run(outputs: Mapping[str, str]) -> set[str]:
    return {job for job in AREA_JOBS if _runs(job, outputs)}


# ------------------------------------------------------------------------------- the evaluator


def test_the_evaluator_models_github_semantics() -> None:
    def run(text: str, **outputs: str) -> bool:
        return ExpressionEvaluator(text).evaluate({"lint": "success"}, outputs, cancelled=False)

    assert run("needs.plan.outputs.full != 'false'") is True  # absent
    assert run("needs.plan.outputs.full != 'false'", full="false") is False
    assert run("needs.plan.outputs.full != 'false'", full="true") is True
    assert run("needs.lint.result == 'SUCCESS'") is True  # comparison ignores case
    assert run("!cancelled() && needs.lint.result == 'success'") is True
    assert (
        run(
            "contains(fromJSON(needs.plan.outputs.areas || '[]'), 'docs')",
            areas='["docs"]',
        )
        is True
    )
    assert run("contains(fromJSON(needs.plan.outputs.areas || '[]'), 'docs')") is False
    assert ExpressionEvaluator("!cancelled()").evaluate({}, {}, cancelled=True) is False
    with pytest.raises(ExpressionError, match="empty string"):
        run("contains(fromJSON(needs.plan.outputs.areas), 'docs')")


@pytest.mark.parametrize(
    "text",
    [
        "always()",
        "success()",
        "failure()",
        "format('{0}', needs.plan.outputs.full)",
        "startsWith(needs.plan.outputs.full, 't')",
        "github.event_name == 'push'",
        "needs.gates.outputs.full == 'true'",
        "needs.plan.outputs == 'x'",
        "needs.plan.result == 'success' && toJSON(needs)",
        "needs.plan.outputs.full != 'false' <= 3",
    ],
)
def test_the_evaluator_rejects_anything_outside_the_subset(text: str) -> None:
    with pytest.raises(ExpressionError):
        ExpressionEvaluator(text)


# ------------------------------------------------------------------------------- the matrices


def _snapshot() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return loaded


def _canonical(rows: list[dict[str, Any]]) -> list[str]:
    return sorted(json.dumps(row, sort_keys=True) for row in rows)


@pytest.mark.parametrize("job", sorted(MATRIX_JOBS))
def test_the_union_of_the_pr_and_full_rows_is_the_snapshot(job: str) -> None:
    union = CiMatrixRows.full(job) + [
        row for row in CiMatrixRows.pr(job) if row not in CiMatrixRows.full(job)
    ]
    assert _canonical(union) == _canonical(_snapshot()[job]), (
        f"{job}: the PR and full tiers no longer add up to the matrix ci.yml declared before "
        "the plan job (tests/meta/ci_matrix_snapshot.json). A row was dropped or invented."
    )


@pytest.mark.parametrize("job", sorted(MATRIX_JOBS))
def test_every_pr_row_is_a_full_row(job: str) -> None:
    full = CiMatrixRows.full(job)
    assert [row for row in CiMatrixRows.pr(job) if row not in full] == []


@pytest.mark.parametrize("job", sorted(MATRIX_JOBS))
def test_the_job_reads_its_matrix_from_the_plan(job: str) -> None:
    output = MATRIX_JOBS[job]
    strategy = _jobs()[job]["strategy"]
    assert strategy["matrix"] == f"${{{{ fromJSON(needs.plan.outputs.{output}_matrix) }}}}"
    assert strategy["fail-fast"] is False


def test_the_vscode_snapshot_is_the_two_jobs() -> None:
    wanted = [row["os"] for row in _snapshot()["vscode"]]
    runs_on = [_jobs()[job]["runs-on"] for job in VSCODE_NAMES]
    assert sorted(wanted) == sorted(runs_on) == ["macos-latest", "ubuntu-latest"]


def test_the_default_matrices_are_the_full_tier_as_literals() -> None:
    defaults = _default_outputs()
    for job, output in MATRIX_JOBS.items():
        literal = json.loads(defaults[f"{output}_matrix"])
        assert literal == {"include": CiMatrixRows.full(job)}, job
        assert defaults[f"{output}_any"] == "true", job
        # The plan job falls through from the CLI to those literals.
        outputs = _jobs()["plan"]["outputs"]
        want = f"${{{{ steps.cli.outputs.{output}_matrix || steps.defaults.outputs.{output}_matrix }}}}"
        assert outputs[f"{output}_matrix"] == want


def test_the_default_matrix_literals_are_what_the_cli_prints_for_the_full_tier() -> None:
    printed = {
        job: json.dumps({"include": CiMatrixRows.full(job)}, separators=(",", ":"))
        for job in MATRIX_JOBS
    }
    defaults = _default_outputs()
    for job, output in MATRIX_JOBS.items():
        assert defaults[f"{output}_matrix"] == printed[job], (
            f"{job}: the literal in the plan job's first step differs from "
            f"`vibey-gh ci-matrix --job {job} --tier full`; regenerate it from the CLI"
        )


# ------------------------------------------------------------------------------- the `if:`s


def test_exactly_the_area_jobs_have_an_if_and_the_always_jobs_keep_theirs() -> None:
    with_if = {job for job, spec in _jobs().items() if "if" in spec}
    assert with_if == set(AREA_JOBS) | ALWAYS_JOBS, sorted(with_if ^ (set(AREA_JOBS) | ALWAYS_JOBS))
    assert _jobs()["ci-result"]["if"] == "always()"


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_every_area_if_reads_only_the_plan_outputs_and_the_two_gating_results(job: str) -> None:
    allowed = {"cancelled()", "contains()", "fromJSON()"}
    for reference in _expression(job).references():
        if reference in allowed:
            continue
        assert reference.startswith("needs.plan.outputs.") or reference in (
            "needs.uv-lock.result",
            "needs.lint.result",
        ), f"{job}: its `if:` reads {reference}"


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_no_if_uses_always_or_reads_another_jobs_result(job: str) -> None:
    text = _if_text(job)
    assert "always(" not in text
    assert "needs.plan.result" not in text
    assert "needs.gates" not in text
    assert "success()" not in text


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_every_job_with_an_if_has_plan_in_its_needs(job: str) -> None:
    assert "plan" in _needs(job)
    assert set(_needs(job)) - {"plan"} == set(AREA_JOBS[job]), (
        f"{job}: its other needs changed; `!cancelled()` replaces the implicit `success()`, "
        "so every one of them must be named in the `if:`"
    )


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_the_if_replaces_the_implicit_success_without_losing_the_chain(job: str) -> None:
    terms = _expression(job).conjuncts()
    assert terms[0] == "!cancelled()", f"{job}: {terms}"
    tested = {
        term for term in terms if term.endswith(".result == 'success')") or "result ==" in term
    }
    assert tested == {f"(needs.{need}.result == 'success')" for need in AREA_JOBS[job]}, (
        f"{job}: a failed uv-lock or lint must still skip it ({terms})"
    )
    area = terms[len(AREA_JOBS[job]) + 1 :]
    assert area, f"{job}: no area clause"
    if job in MATRIX_JOBS:
        # The `<job>_any` output IS the area test of a matrix job: the CLI folds the areas and
        # `select_on` into it (a docs change selects the tools whose suites read the docs), and
        # it is the guard that keeps an empty matrix away from `strategy`.
        guard = f"(needs.plan.outputs.{MATRIX_JOBS[job]}_any != 'false')"
        assert guard in area, f"{job}: the `_any` guard is missing ({area})"
    else:
        assert any("needs.plan.outputs.full" in term for term in area), (
            f"{job}: `full` must be tested before the areas"
        )


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_the_full_test_comes_before_any_areas_parse_and_fromjson_is_guarded(job: str) -> None:
    text = _if_text(job)
    if "fromJSON" in text:
        assert "fromJSON(needs.plan.outputs.areas || '[]')" in text
        assert text.index("needs.plan.outputs.full") < text.index("fromJSON")
        assert text.count("fromJSON(") == text.count("fromJSON(needs.plan.outputs.areas || '[]')")


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_with_the_plan_outputs_absent_every_dependant_runs(job: str) -> None:
    assert _runs(job, {}), f"{job} must fail open when the plan wrote nothing"


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_with_the_default_outputs_every_dependant_runs(job: str) -> None:
    defaults = _default_outputs()
    assert defaults["full"] == "true"
    assert _runs(job, defaults)
    # ... and whatever the plan's own result was: nothing reads it.
    for result in ("success", "failure", "cancelled", "skipped"):
        assert _runs(job, defaults, plan=result), f"{job} with needs.plan.result={result}"


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_a_partial_plan_still_fails_open(job: str) -> None:
    # The CLI printed some keys and not others (a crash mid-write).
    for keep in ("full", "areas", "tools_any"):
        partial = {keep: _default_outputs()[keep]}
        assert _runs(job, partial), f"{job} with only {keep!r}"


@pytest.mark.parametrize("job", sorted(AREA_JOBS))
def test_a_failed_uv_lock_or_lint_or_a_cancellation_still_skips(job: str) -> None:
    for need in AREA_JOBS[job]:
        assert not _runs(job, {}, **{need: "failure"}), f"{job} must skip when {need} failed"
        assert not _runs(job, {}, **{need: "skipped"}), f"{job} must skip when {need} was skipped"
        assert not _runs(job, {}, **{need: "cancelled"})
    assert not _expression(job).evaluate({}, {}, cancelled=True)


# ------------------------------------------------------------------------------- the areas


def test_gates_always_runs_and_does_not_wait_for_the_plan() -> None:
    gates = _jobs()["gates"]
    assert "if" not in gates
    assert "plan" not in _needs("gates")
    assert _needs("gates") == ["uv-lock", "lint"]


@pytest.mark.parametrize(
    "paths",
    [
        ["src/vibey_tools/gh/vibey_gh/x.py"],
        ["docs/guides/x.md"],
        ["clients/vscode/src/x.ts"],
        ["src/vibey/domain/x.py"],
        [".github/workflows/ci.yml"],
    ],
)
def test_no_diff_skips_gates(paths: list[str]) -> None:
    # `gates` has no `if:`, so the only way it can be skipped is a skipped need (uv-lock, lint),
    # which the diff cannot cause.
    outputs = _outputs_for(paths)
    assert "if" not in _jobs()["gates"]
    assert outputs["full"] in ("true", "false")


def test_a_docs_only_diff_skips_the_heavy_jobs() -> None:
    outputs = _outputs_for(["docs/guides/getting-started.md"])
    assert outputs["full"] == "false"
    ran = _would_run(outputs)
    # `tools` runs three PR rows: the suites of vibey-gh and vibey-skills read the root docs,
    # so the area map selects them on a docs change (.github/ci-matrices.toml `select_on`), and
    # vibey-bootstrap installs vibey-gh from the tree, so it rides along.
    assert ran == {"tools"}
    assert [row["package"] for row in json.loads(outputs["tools_matrix"])["include"]] == [
        "vibey-gh",
        "vibey-skills",
        "vibey-bootstrap",
    ]


def test_a_python_only_diff_runs_the_python_jobs_and_the_image() -> None:
    outputs = _outputs_for(["src/vibey/domain/x.py"])
    assert outputs["full"] == "false"
    assert _would_run(outputs) == {
        "noloss",
        "postgres-compatibility",
        "tools-lint",
        "image",
        "cluster-smoke",
        "chart",
    }
    assert [row["postgres"] for row in json.loads(outputs["postgres_matrix"])["include"]] == [
        14,
        18,
    ]


def test_a_tools_only_diff_runs_the_tools_jobs_and_not_the_rest() -> None:
    outputs = _outputs_for(["src/vibey_tools/gh/vibey_gh/x.py"])
    assert outputs["full"] == "false"
    ran = _would_run(outputs)
    assert {"tools", "tools-lint", "image", "cluster-smoke", "chart"} <= ran
    assert not ran & {"noloss", "postgres-compatibility", "desktop", "app", "krypton-app"}
    # vibey-bootstrap installs vibey-gh from the tree, so a vibey-gh change selects both.
    assert [row["package"] for row in json.loads(outputs["tools_matrix"])["include"]] == [
        "vibey-gh",
        "vibey-bootstrap",
    ]


def test_a_vscode_only_diff_runs_the_vscode_jobs_and_no_desktop_or_python() -> None:
    outputs = _outputs_for(["clients/vscode/src/extension/chat.ts"])
    ran = _would_run(outputs)
    assert {"vscode-extension-ubuntu", "vscode-extension-macos", "vibey-core", "app"} <= ran
    assert not ran & {"desktop", "noloss", "postgres-compatibility", "tools", "image"}


def test_a_ci_workflow_diff_runs_everything() -> None:
    outputs = _outputs_for([".github/workflows/ci.yml"])
    assert outputs["full"] == "true"
    assert _would_run(outputs) == set(AREA_JOBS)


@pytest.mark.parametrize("event", ["merge_group", "workflow_dispatch", "schedule"])
def test_the_full_events_run_everything(event: str) -> None:
    outputs = _outputs_for(["docs/x.md"], event=event, base_ref="")
    assert _would_run(outputs) == set(AREA_JOBS)


def test_a_pull_request_into_main_runs_everything() -> None:
    outputs = _outputs_for(["docs/x.md"], base_ref="main")
    assert _would_run(outputs) == set(AREA_JOBS)


# ------------------------------------------------------------------------------- VS Code


def _required_checks() -> dict[str, list[str]]:
    config = tomllib.loads(VIBEY_GH.read_text(encoding="utf-8"))
    return {
        name: list(spec["required_checks"])
        for name, spec in config["rulesets"].items()
        if isinstance(spec, dict)
    }


def test_the_two_vscode_jobs_carry_the_required_names_byte_for_byte() -> None:
    jobs = _jobs()
    assert "vscode-extension" not in jobs, "the matrix job is replaced by two plain jobs"
    for job, name in VSCODE_NAMES.items():
        assert jobs[job]["name"] == name
        assert "strategy" not in jobs[job], "a skipped matrix job reports its unexpanded name"
        assert "${{" not in jobs[job]["name"]
    required = _required_checks()
    for ruleset, names in required.items():
        for name in VSCODE_NAMES.values():
            assert name in names, f"{ruleset} no longer requires {name!r}"


def test_the_required_names_that_ci_produces_are_plain_job_names() -> None:
    jobs = _jobs()
    ci_names = {spec["name"]: job for job, spec in jobs.items() if "name" in spec}
    for ruleset, names in _required_checks().items():
        for name in names:
            if name == "gates":
                assert "gates" in jobs and "name" not in jobs["gates"]
            elif name in ci_names:
                assert "${{" not in name
                assert "strategy" not in jobs[ci_names[name]], (
                    f"{ruleset}: {name!r} is produced by a matrix job, whose skipped name is "
                    "the unexpanded template"
                )


def test_the_vscode_jobs_are_the_old_matrix_cells_and_differ_only_where_they_must() -> None:
    ubuntu = _jobs()["vscode-extension-ubuntu"]
    macos = _jobs()["vscode-extension-macos"]
    assert ubuntu["runs-on"] == "ubuntu-latest" and macos["runs-on"] == "macos-latest"
    assert ubuntu["timeout-minutes"] == macos["timeout-minutes"] == 15
    assert ubuntu["defaults"] == macos["defaults"]

    def comparable(job: dict[str, Any], os_name: str) -> list[str]:
        text = yaml.safe_dump(job["steps"])
        return text.replace(os_name, "<os>").splitlines()

    ubuntu_steps = [
        s for s in ubuntu["steps"] if not str(s.get("name", "")).startswith("Smoke test")
    ]
    macos_steps = [s for s in macos["steps"] if not str(s.get("name", "")).startswith("Smoke test")]
    assert comparable({"steps": ubuntu_steps}, "ubuntu-latest") == comparable(
        {"steps": macos_steps}, "macos-latest"
    )
    smoke_u = [s["run"] for s in ubuntu["steps"] if str(s.get("name", "")).startswith("Smoke test")]
    smoke_m = [s["run"] for s in macos["steps"] if str(s.get("name", "")).startswith("Smoke test")]
    assert smoke_u == ["xvfb-run -a npm run smoke"]
    assert smoke_m == ["npm run smoke"]


def test_the_vscode_artifact_names_are_unchanged() -> None:
    for job, os_name in (
        ("vscode-extension-ubuntu", "ubuntu-latest"),
        ("vscode-extension-macos", "macos-latest"),
    ):
        uploads = [
            s
            for s in _jobs()[job]["steps"]
            if str(s.get("uses", "")).startswith("actions/upload-artifact")
        ]
        assert [u["with"]["name"] for u in uploads] == [f"krypton-vscode-{os_name}"]
        assert uploads[0]["with"]["path"] == f"clients/vscode/krypton-{os_name}.vsix"


def test_the_vscode_jobs_are_in_the_limits_the_result_and_the_lint_partition() -> None:
    limits = tomllib.loads((REPO / "tests/meta/ci_job_limits.toml").read_text(encoding="utf-8"))[
        "jobs"
    ]
    assert "vscode-extension" not in limits
    for job in VSCODE_NAMES:
        assert limits[job]["timeout_minutes"] == _jobs()[job]["timeout-minutes"]
        assert job in _jobs()["ci-result"]["needs"]
    assert "vscode-extension" not in _jobs()["ci-result"]["needs"]
    assert "plan" in _needs("vscode-extension-ubuntu")
    assert "lint" not in _needs("vscode-extension-ubuntu"), "the JS jobs stay ungated by lint"


def test_the_repository_still_declares_a_plan_that_never_fails_a_dependant() -> None:
    plan = _jobs()["plan"]
    assert plan["continue-on-error"] is True
    assert "needs" not in plan
    assert "if" not in plan
