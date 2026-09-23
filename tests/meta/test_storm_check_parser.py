# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for the part of `lane-publish.py` that decides what a lane's check means.

The storm's tools are measurement instruments, and its whole verdict is whatever they
report. A bug here does not announce itself as a bug: the check still runs, still prints,
still gets counted -- it just measures something other than what the spec asked for. Six
faults of exactly that shape were found in one night, and each had survived because the
output looked like a result.

WHY THIS LIVES UNDER tests/ AND NOT BESIDE THE TOOL
It began beside the tool, which read better and ran nowhere: `testpaths = ["tests"]`, so
the repository suite never collected it and no CI step named it. A regression test CI does
not run lets the bug come back green, which is the same failure these tests are about.
Here it is collected by Gate 4 with everything else, and `--cov=vibey` does not measure it,
so the per-layer coverage gates are untouched.

The tool is addressed by path because `lane-publish.py` is not an importable name. If the
storm's tools are ever removed this fails loudly rather than skipping quietly -- delete it
in the same commit that deletes them.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools/lane-publish.py"
# Running a script puts its own directory on `sys.path`; importing one BY PATH does not. So a
# tool that imports a sibling -- `lane-publish.py` imports `storm_paths` for the repository
# location it must no longer hard-code (12.h) -- fails here and nowhere else, which is a
# property of this caller rather than of the tool. Reproducing what the interpreter does for
# the tool's real invocation is the honest fix; making the tool carry a workaround for its
# one unusual caller is not.
if str(TOOL.parent) not in sys.path:
    sys.path.insert(0, str(TOOL.parent))
SPEC = importlib.util.spec_from_file_location("lane_publish", TOOL)
assert SPEC and SPEC.loader, f"the storm's publisher is missing: {TOOL}"
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


def test_a_console_script_is_taken_from_the_lanes_own_venv(tmp_path: Path) -> None:
    """A bare `isort` otherwise resolves to whatever environment launched the publisher.

    `run()` drops VIRTUAL_ENV and never puts the lane's `.venv/bin` on PATH, so before this
    the formatter gate measured a tree other than the lane's -- the very mistake the gate
    was added to catch.
    """
    lane = lane_with(tmp_path, "isort --check-only .")
    binaries = lane / ".venv/bin"
    binaries.mkdir(parents=True)
    (binaries / "isort").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    argv = lane_publish.checks_of(lane)[0].argv
    resolved = lane_publish.resolve(lane, argv)
    assert resolved[0] == str(binaries / "isort")


def test_a_console_script_the_lane_does_not_have_is_left_alone(tmp_path: Path) -> None:
    lane = lane_with(tmp_path, "isort --check-only .")
    argv = lane_publish.checks_of(lane)[0].argv
    assert lane_publish.resolve(lane, argv) == ["isort", "--check-only", "."]


# --- subshells, and the lines nobody could classify --------------------------------------


def parsed(tmp_path: Path, block: str) -> tuple[list, list[tuple[str, str]]]:
    lane = lane_with(tmp_path, block)
    return lane_publish.parse_checks((lane / ".qwenstorm/issue.md").read_text(), lane)


def test_a_subshell_line_is_a_check_scoped_to_its_own_directory(tmp_path: Path) -> None:
    """The regression: 80 `(cd tenant && ...)` lines in 28 specs were skipped in silence.

    harness-T20a and T20c were reported READY having run `ruff` and nothing else; their
    tenant pytest, mypy, lint-imports and bandit were subshell lines and never ran.
    """
    lane = lane_with(tmp_path, "(cd src/vibey_tools/gh && python -m pytest -q)\nruff check .")
    checks = lane_publish.checks_of(lane)
    assert [c.argv for c in checks] == [["python", "-m", "pytest", "-q"], ["ruff", "check", "."]]
    assert checks[0].cwd == (lane / "src/vibey_tools/gh").resolve()
    assert checks[1].cwd == lane.resolve(), "a subshell's `cd` must not outlive its line"


def test_an_export_inside_a_subshell_ends_with_it(tmp_path: Path) -> None:
    checks, _ = parsed(tmp_path, "(export A=1 && ruff check .)\nmypy src")
    assert [c.env for c in checks] == [{"A": "1"}, {}]


def test_a_subshell_keeps_a_parenthesis_that_was_quoted(tmp_path: Path) -> None:
    lane = lane_with(tmp_path, '(cd src/vibey_tools/gh && python -c "print(1)")')
    assert [c.argv for c in lane_publish.checks_of(lane)] == [["python", "-c", "print(1)"]]


def test_a_subshell_with_no_cd_is_still_a_check(tmp_path: Path) -> None:
    checks, dropped = parsed(tmp_path, "(ruff check .)")
    assert [c.argv for c in checks] == [["ruff", "check", "."]] and dropped == []


def test_an_unclosed_subshell_is_reported_not_guessed(tmp_path: Path) -> None:
    checks, dropped = parsed(tmp_path, "(cd src/vibey_tools/gh && ruff check .")
    assert checks == []
    assert len(dropped) == 1 and "shell" in dropped[0][1]


def test_a_parenthesis_mid_line_needs_a_shell(tmp_path: Path) -> None:
    checks, dropped = parsed(tmp_path, "ruff check . (optional)")
    assert checks == [] and len(dropped) == 1


def test_a_list_item_in_a_check_block_is_reported(tmp_path: Path) -> None:
    """A line the parser cannot classify is a check that never runs; it must say so."""
    checks, dropped = parsed(tmp_path, "- run the tenant suite\n* and mypy\nruff check .")
    assert [c.argv for c in checks] == [["ruff", "check", "."]]
    assert [line for line, _ in dropped] == ["- run the tenant suite", "* and mypy"]


def test_a_comment_line_is_classified_and_not_reported(tmp_path: Path) -> None:
    checks, dropped = parsed(tmp_path, "# the whole suite\nruff check .")
    assert len(checks) == 1 and dropped == []


def test_prose_after_an_indented_block_is_not_a_check(tmp_path: Path) -> None:
    """The misparse that held orm-bootstrap-async-engine on a check its spec never wrote.

    An unfenced block is Markdown's indented code block, so an unindented line after it is
    prose. Read as a command, "pytest `addopts`, so a partial run..." became a pytest run.
    """
    lane = tmp_path / "lane"
    (lane / ".qwenstorm").mkdir(parents=True)
    (lane / "src/vibey_tools/gh").mkdir(parents=True)
    spec = (
        "# a lane\n\n## Checks the lane must run (all must pass)\n"
        "    uv run ruff check .\n"
        "    (cd src/vibey_tools/gh && uv run python -m pytest -q)\n"
        "The second command is the whole suite: the floor is enforced by the tenant's own\n"
        "pytest `addopts`, so a partial run needs `--no-cov`.\n\n## Out of scope\n- nothing\n"
    )
    checks, dropped = lane_publish.parse_checks(spec, lane)
    assert [c.argv for c in checks] == [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "python", "-m", "pytest", "-q"],
    ]
    assert dropped == []


def test_a_defaulted_parameter_in_an_assignment_is_expanded(tmp_path: Path, monkeypatch) -> None:
    """`${NAME:-default}` reached the test as a literal string, pointing it at no database."""
    monkeypatch.delenv("STORM_TEST_URL", raising=False)
    monkeypatch.setenv("USER", "someone")
    checks, _ = parsed(tmp_path, "STORM_TEST_URL=${STORM_TEST_URL:-pg://$USER@h/db} ruff check .")
    assert checks[0].env == {"STORM_TEST_URL": "pg://someone@h/db"}


def test_an_assignment_left_unexpanded_is_reported(tmp_path: Path) -> None:
    checks, dropped = parsed(tmp_path, "X=${Y:?unset} ruff check .")
    assert checks == [] and len(dropped) == 1


def test_env_unsets_and_assigns_for_one_command(tmp_path: Path) -> None:
    """fakes-harness-decouple's own suite line was dropped because it began with `env`."""
    checks, dropped = parsed(tmp_path, "A=1 env -u B C=2 uv run pytest -q")
    assert dropped == []
    assert checks[0].argv == ["uv", "run", "pytest", "-q"]
    assert checks[0].env == {"A": "1", "C": "2"}
    assert checks[0].unset == ("B",)


def test_bandit_is_a_runnable_check(tmp_path: Path) -> None:
    """CI runs it as a gate; a spec that names it bare must not have it dropped."""
    checks, dropped = parsed(tmp_path, "bandit -q -r src/vibey")
    assert [c.argv[0] for c in checks] == ["bandit"] and dropped == []


def test_run_removes_what_the_check_unsets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("STORM_GONE", "present")
    code, out = lane_publish.run(
        [sys.executable, "-c", "import os; print(os.environ.get('STORM_GONE', 'absent'))"],
        tmp_path,
        drop=("STORM_GONE",),
    )
    assert (code, out) == (0, "absent")


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


# --- storm-snapshot's ownership guard ---------------------------------------------------


SNAPSHOT = (
    Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools/storm-snapshot.py"
)
_SS = importlib.util.spec_from_file_location("storm_snapshot", SNAPSHOT)
assert _SS and _SS.loader, f"the storm's snapshot tool is missing: {SNAPSHOT}"
storm_snapshot = importlib.util.module_from_spec(_SS)
_SS.loader.exec_module(storm_snapshot)


def test_the_committed_blob_is_read_raw_not_through_run() -> None:
    """`run()` strips its output, and a stripped file can never equal an unstripped one.

    `not_ours()` compares the committed `docs/paper.md` against the working copy with the
    generated block removed. Read through `run()`, the committed side loses its trailing
    newline while the working side keeps one, so the two never match and the guard refuses
    EVERY snapshot -- a fail-closed that never opens is just off, and it disabled the
    snapshot job silently.

    `lane-resolve.py` carries a `read_blob()` for exactly this reason. The same mistake was
    made again here, which is why it is now a test rather than a comment.
    """
    source = SNAPSHOT.read_text(encoding="utf-8")
    body = source.split("def not_ours(", 1)[1].split("\ndef ", 1)[0]
    assert 'run(["git", "show"' not in body, (
        "not_ours() reads the committed blob through run(), which strips it"
    )
    assert "subprocess.run(" in body, "not_ours() should read the blob raw"


def test_the_guard_tells_the_storms_own_output_from_somebody_elses(tmp_path) -> None:
    """Inside the markers is the storm's; outside them is a person's."""
    begin, end = storm_snapshot.GENERATED
    base = f"intro\n{begin}\nNUMBERS\n{end}\nconclusion\n"
    regenerated = f"intro\n{begin}\nDIFFERENT NUMBERS\n{end}\nconclusion\n"
    edited = f"intro EDITED\n{begin}\nNUMBERS\n{end}\nconclusion\n"
    assert storm_snapshot.hand_written(base) == storm_snapshot.hand_written(regenerated)
    assert storm_snapshot.hand_written(base) != storm_snapshot.hand_written(edited)
