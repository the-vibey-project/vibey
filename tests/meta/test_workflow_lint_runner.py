# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/workflow_lint.py`: the zizmor finding count is ratcheted in both directions.

Each test hands `WorkflowLint` a fake process runner, so none of them runs zizmor. The tool list
is data (`ToolSpec`), and one test adds a second, fake spec to prove nothing here is zizmor-shaped.

Module-level test functions (ADR-0016: the rule is about production code; pytest collects them).
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts import workflow_lint as wl

REPO = Path(__file__).resolve().parents[2]


def _findings(count: int, ignored: int = 0) -> str:
    rows = [{"ident": "artipacked", "ignored": False} for _ in range(count)]
    rows += [{"ident": "artipacked", "ignored": True} for _ in range(ignored)]
    return json.dumps(rows)


class FakeRunner:
    """Answers each command from a table keyed by the tool's executable; records every call."""

    def __init__(self, answers: dict[str, tuple[int, str, str]]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str, str]:
        self.calls.append(tuple(argv))
        return self.answers[argv[0]]


def _lint(
    tmp_path: Path, baseline: int, answers: dict[str, tuple[int, str, str]]
) -> tuple[int, str, FakeRunner]:
    path = tmp_path / "baseline.toml"
    path.write_text(
        f'[zizmor]\ncount = {baseline}\nversion = "1.32.0"\nmeasured = "2026-11-16"\n',
        encoding="utf-8",
    )
    runner = FakeRunner(answers)
    lines: list[str] = []
    code = wl.WorkflowLint(path, wl.TOOLS, runner, lines.append).run()
    return code, "\n".join(lines), runner


def test_a_count_at_the_baseline_passes(tmp_path: Path) -> None:
    code, out, _ = _lint(tmp_path, 3, {"zizmor": (0, _findings(3), "")})
    assert code == 0
    assert "zizmor" in out


def test_a_count_above_the_baseline_fails_and_names_the_tool(tmp_path: Path) -> None:
    code, out, _ = _lint(tmp_path, 3, {"zizmor": (0, _findings(4), "")})
    assert code == 1
    assert "zizmor" in out and "4" in out and "3" in out


def test_a_count_below_the_baseline_fails_telling_you_to_lower_it(tmp_path: Path) -> None:
    code, out, _ = _lint(tmp_path, 3, {"zizmor": (0, _findings(2), "")})
    assert code == 1
    assert "zizmor" in out and "lower" in out


def test_a_tool_that_exits_with_an_error_instead_of_findings_fails(tmp_path: Path) -> None:
    # A crash with an empty (or well-formed) output must never read as a clean pass at count 0.
    code, out, _ = _lint(tmp_path, 0, {"zizmor": (1, "[]", "boom")})
    assert code == 1
    assert "zizmor" in out and "boom" in out


def test_output_that_is_not_findings_fails(tmp_path: Path) -> None:
    code, out, _ = _lint(tmp_path, 0, {"zizmor": (0, "not json", "")})
    assert code == 1
    assert "zizmor" in out


def test_an_ignored_finding_is_not_counted(tmp_path: Path) -> None:
    code, _, _ = _lint(tmp_path, 3, {"zizmor": (0, _findings(3, ignored=5), "")})
    assert code == 0


def test_zizmor_reads_json_and_does_not_call_the_network(tmp_path: Path) -> None:
    _, _, runner = _lint(tmp_path, 3, {"zizmor": (0, _findings(3), "")})
    (argv,) = runner.calls
    assert "--format" in argv and "json" in argv
    assert "--offline" in argv
    assert "--no-exit-codes" in argv


def test_a_tool_without_a_baseline_entry_fails(tmp_path: Path) -> None:
    path = tmp_path / "baseline.toml"
    path.write_text("", encoding="utf-8")
    lines: list[str] = []
    runner = FakeRunner({"zizmor": (0, _findings(0), "")})
    code = wl.WorkflowLint(path, wl.TOOLS, runner, lines.append).run()
    assert code == 1
    assert "zizmor" in "\n".join(lines)


def test_a_second_tool_is_data_not_code(tmp_path: Path) -> None:
    second = wl.ToolSpec(
        name="fakelint",
        argv=("fakelint", "--all"),
        count=lambda text: len(text.splitlines()),
    )
    path = tmp_path / "baseline.toml"
    path.write_text(
        '[zizmor]\ncount = 1\nversion = "1"\nmeasured = "d"\n'
        '[fakelint]\ncount = 2\nversion = "1"\nmeasured = "d"\n',
        encoding="utf-8",
    )
    runner = FakeRunner({"zizmor": (0, _findings(1), ""), "fakelint": (0, "a\nb\nc\n", "")})
    lines: list[str] = []
    code = wl.WorkflowLint(path, (*wl.TOOLS, second), runner, lines.append).run()
    out = "\n".join(lines)
    assert code == 1
    assert "fakelint" in out and "zizmor" in out
    assert [c[0] for c in runner.calls] == ["zizmor", "fakelint"]


def test_the_committed_baseline_has_an_entry_per_tool_with_version_and_date() -> None:
    table = tomllib.loads((REPO / "tests/meta/workflow_lint_baseline.toml").read_text("utf-8"))
    for tool in wl.TOOLS:
        entry = table[tool.name]
        assert isinstance(entry["count"], int) and entry["count"] >= 0
        assert entry["version"] and entry["measured"]


@pytest.mark.parametrize("tool", wl.TOOLS, ids=lambda t: t.name)
def test_every_tool_runs_from_the_repository_root_paths(tool: wl.ToolSpec) -> None:
    assert ".github/workflows" in tool.argv
