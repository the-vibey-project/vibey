"""Tests for the part of lane-publish that decides what a check means.

These tools are measurement instruments, and the whole storm's verdict is whatever they
report. A bug here does not announce itself as a bug: the check still runs, still prints,
still gets counted -- it just measures something other than what the spec asked for. Three
separate outages tonight were exactly that, and each survived because the output looked
like a result. So the parser gets tests even though the scripts around it do not.

`testpaths = ["tests"]` in the root pyproject, so this is not collected by the repository
suite. Run it directly:

    python3 -m pytest docs/plans/qwenstorm-3.0.0/tools/test_lane_publish.py -q
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "lane_publish", Path(__file__).with_name("lane-publish.py")
)
assert SPEC and SPEC.loader
lane_publish = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lane_publish)


def lane_with(tmp_path: Path, block: str) -> Path:
    """A lane whose spec carries `block` as its check block, and a tenant to cd into."""
    lane = tmp_path / "lane"
    (lane / ".qwenstorm").mkdir(parents=True)
    (lane / "src/vibey_tools/gh").mkdir(parents=True)
    (lane / ".qwenstorm/issue.md").write_text(
        f"# a lane\n\n## Checks the lane must run (all must pass)\n```bash\n{block}\n```\n",
        encoding="utf-8",
    )
    return lane


def test_cd_sets_the_directory_for_every_later_check(tmp_path: Path) -> None:
    """The reason this exists: a tenant's suite cannot run from the repository root."""
    lane = lane_with(tmp_path, "cd src/vibey_tools/gh\npython -m pytest -q")
    checks = lane_publish.checks_of(lane)
    assert [c.argv for c in checks] == [["python", "-m", "pytest", "-q"]]
    assert checks[0].cwd == (lane / "src/vibey_tools/gh").resolve()


def test_cd_back_out_of_a_tenant_returns_to_the_lane(tmp_path: Path) -> None:
    """`cd ../../..` is how every tenant spec closes, and it must land on the lane root."""
    lane = lane_with(tmp_path, "cd src/vibey_tools/gh\ncd ../../..\nruff check .")
    checks = lane_publish.checks_of(lane)
    assert checks[0].cwd == lane.resolve()


def test_a_cd_that_leaves_the_lane_abandons_the_rest(tmp_path: Path) -> None:
    """Running the remaining checks at the lane root would be measuring the wrong tree."""
    lane = lane_with(tmp_path, "cd ../../../../etc\npython -m pytest -q")
    assert lane_publish.checks_of(lane) == []


def test_a_cd_to_somewhere_absent_abandons_the_rest(tmp_path: Path) -> None:
    lane = lane_with(tmp_path, "cd src/vibey_tools/nope\npython -m pytest -q")
    assert lane_publish.checks_of(lane) == []


def test_bare_cd_means_home_and_is_refused(tmp_path: Path) -> None:
    lane = lane_with(tmp_path, "cd\npython -m pytest -q")
    assert lane_publish.checks_of(lane) == []


def test_checks_before_a_bad_cd_are_still_kept(tmp_path: Path) -> None:
    """Only what follows the unrunnable `cd` is in doubt; what precedes it was fine."""
    lane = lane_with(tmp_path, "ruff check .\ncd /etc\npython -m pytest -q")
    checks = lane_publish.checks_of(lane)
    assert [c.argv for c in checks] == [["ruff", "check", "."]]


@pytest.mark.parametrize("note", ["(run in `src/vibey_tools/gh`)", "(in src/vibey_tools/gh)"])
def test_an_annotation_beats_the_running_directory(tmp_path: Path, note: str) -> None:
    """The line says where it runs; that is more specific than where the block had got to."""
    lane = lane_with(tmp_path, f"python -m pytest -q {note}")
    checks = lane_publish.checks_of(lane)
    assert checks[0].argv == ["python", "-m", "pytest", "-q"]
    assert checks[0].cwd == (lane / "src/vibey_tools/gh").resolve()


def test_a_comment_is_not_an_argument(tmp_path: Path) -> None:
    """`# whole suite` once reached pytest as three paths, and it answered "no tests ran"."""
    lane = lane_with(tmp_path, "python -m pytest -q   # whole suite, 100% line+branch")
    assert [c.argv for c in lane_publish.checks_of(lane)] == [["python", "-m", "pytest", "-q"]]


def test_quoting_survives_because_a_shell_would_have_stripped_it(tmp_path: Path) -> None:
    """378 specs quote `--include=...` so a shell will not glob it; nothing else strips it."""
    lane = lane_with(tmp_path, "python -m coverage report --include='src/vibey/domain/*'")
    argv = lane_publish.checks_of(lane)[0].argv
    assert argv[-1] == "--include=src/vibey/domain/*"


def test_and_and_is_a_sequence_not_a_shell(tmp_path: Path) -> None:
    """555 of 643 specs joined checks with `&&` and every one was dropped whole."""
    lane = lane_with(tmp_path, "ruff check . && mypy src")
    assert [c.argv for c in lane_publish.checks_of(lane)] == [
        ["ruff", "check", "."],
        ["mypy", "src"],
    ]


def test_a_chained_cd_is_scoped_to_its_own_line(tmp_path: Path) -> None:
    """`cd X && cmd` is the subshell idiom; treating it as persistent compounds the paths."""
    lane = lane_with(tmp_path, "cd src/vibey_tools/gh && ruff check .\nmypy src")
    checks = lane_publish.checks_of(lane)
    assert checks[0].cwd == (lane / "src/vibey_tools/gh").resolve()
    assert checks[1].cwd == lane.resolve()


def test_a_chained_cd_that_fails_drops_only_its_line(tmp_path: Path) -> None:
    lane = lane_with(tmp_path, "cd nowhere && ruff check .\nmypy src")
    assert [c.argv for c in lane_publish.checks_of(lane)] == [["mypy", "src"]]


def test_and_and_inside_quotes_is_not_a_separator(tmp_path: Path) -> None:
    """Splitting the tokens rather than the text is what makes this safe."""
    lane = lane_with(tmp_path, "grep -r 'a && b' src")
    assert [c.argv for c in lane_publish.checks_of(lane)] == [["grep", "-r", "a && b", "src"]]


def test_a_fallback_is_still_refused(tmp_path: Path) -> None:
    """`||` means "try, else do something else" -- a decision this cannot make for an author."""
    lane = lane_with(tmp_path, 'python -c "import x" || python -m pip install x')
    assert lane_publish.checks_of(lane) == []


@pytest.mark.parametrize("token", ["|", ">", "<", "$("])
def test_the_rest_of_the_shell_is_still_refused(tmp_path: Path, token: str) -> None:
    lane = lane_with(tmp_path, f"ruff check . {token} thing")
    assert lane_publish.checks_of(lane) == []


def test_an_inline_assignment_becomes_the_command_environment(tmp_path: Path) -> None:
    """96 lines were dropped as "not a command" because their first word was a variable."""
    lane = lane_with(tmp_path, "UV_CACHE_DIR=/tmp/uvcache ruff check .")
    check = lane_publish.checks_of(lane)[0]
    assert check.argv == ["ruff", "check", "."]
    assert check.env == {"UV_CACHE_DIR": "/tmp/uvcache"}


def test_export_sets_the_environment_for_what_follows(tmp_path: Path) -> None:
    """261 `export` lines were dropped; each of them configures the checks beneath it."""
    lane = lane_with(tmp_path, "export VIBEY_FEATURE_QWENLOOP=1\nruff check .\nmypy src")
    checks = lane_publish.checks_of(lane)
    assert [c.argv[0] for c in checks] == ["ruff", "mypy"]
    assert all(c.env == {"VIBEY_FEATURE_QWENLOOP": "1"} for c in checks)


def test_an_inline_assignment_does_not_leak_into_later_checks(tmp_path: Path) -> None:
    """A prefix configures one command; `export` is the one that persists."""
    lane = lane_with(tmp_path, "UV_CACHE_DIR=/tmp/c ruff check .\nmypy src")
    assert [c.env for c in lane_publish.checks_of(lane)] == [{"UV_CACHE_DIR": "/tmp/c"}, {}]


def test_the_tenant_formatters_are_runnable_checks(tmp_path: Path) -> None:
    """CI's `tools-lint` enforces both, so a parser that drops them turns a gate off."""
    lane = lane_with(tmp_path, "black --line-length 100 --check vibey_gh\nisort --check-only .")
    assert [c.argv[0] for c in lane_publish.checks_of(lane)] == ["black", "isort"]


# --- why_failed: the reason a person is shown -----------------------------------------


def test_a_filename_containing_error_is_not_a_failure() -> None:
    """The bug this replaced: `errors.py` at 100% was reported as the reason a lane failed."""
    out = "\n".join(
        [
            "FAILED test/test_forge_adapters.py::test_http_transports[GitLabTransport]",
            "vibey_gh/errors.py            78      0     26      0   100%",
            "Installed 4 packages in 15ms",
        ]
    )
    assert lane_publish.why_failed(out).startswith("FAILED test/test_forge_adapters.py")


def test_a_test_file_named_failed_is_not_a_failure() -> None:
    out = "tests/test_failed_handoff.py .....  [100%]\n42 passed in 3.1s"
    assert lane_publish.why_failed(out) == "42 passed in 3.1s"


def test_the_named_test_outranks_the_assertion_under_it() -> None:
    out = "\n".join(
        [
            "E       AssertionError: assert [] == [{'id': 1}]",
            "FAILED test/test_forge_adapters.py::test_http_transports[ForgejoTransport]",
        ]
    )
    assert lane_publish.why_failed(out).startswith("FAILED ")


def test_a_mypy_error_is_found_by_its_shape() -> None:
    out = "Installed 4 packages\nvibey_gh/forge.py:31: error: Missing return statement  [return]"
    assert lane_publish.why_failed(out).endswith("[return]")


def test_a_missed_coverage_gate_is_reported_when_nothing_else_is() -> None:
    out = "TOTAL  9397  1  3002  1  99%\nFAIL Required test coverage of 100% not reached."
    assert "Required test coverage" in lane_publish.why_failed(out)


def test_with_no_recognisable_failure_the_last_line_stands_in() -> None:
    out = "Installed 4 packages in 15ms\nAll checks passed!"
    assert lane_publish.why_failed(out) == "All checks passed!"


def test_no_output_says_so() -> None:
    assert lane_publish.why_failed("   \n\n") == "no output"
