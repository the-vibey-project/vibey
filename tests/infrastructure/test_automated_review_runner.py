# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from vibey.application.build_verify_handler import GateResult, GateRunner
from vibey.application.dto import ProjectRecord
from vibey.domain.phase import Phase
from vibey.domain.review import Ambiguity, Severity
from vibey.infrastructure.build.automated_review_runner import (
    _DEFAULT_CODE_REVIEW,
    _DEFAULT_SECURITY,
    SubprocessAutomatedReviewRunner,
)

NOW = datetime(2026, 8, 15, tzinfo=UTC)


class FakeGateRunner(GateRunner):
    def __init__(self, outcomes: dict[tuple[str, ...], GateResult] | None = None) -> None:
        self.outcomes = outcomes or {}

    async def run(self, argv: tuple[str, ...], *, cwd: Path) -> GateResult:
        return self.outcomes.get(argv, GateResult(0, "ok", ""))


class FakeProjectRepo:
    def __init__(self, project: ProjectRecord | None = None) -> None:
        self.project = project

    async def get(self, project_id: object) -> ProjectRecord | None:
        return self.project


async def test_subprocess_automated_review_runner_clean(tmp_path: Path) -> None:
    proj = ProjectRecord(
        project_id=uuid4(),
        name="p1",
        repo_path=tmp_path,
        phase=Phase.REVIEW,
        cycle=1,
        max_cycles=5,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    runner = SubprocessAutomatedReviewRunner(
        projects=FakeProjectRepo(proj),
        gates=FakeGateRunner(),
    )
    findings = await runner.run_automated_reviews(proj.project_id, 1)
    assert len(findings) == 0


async def test_subprocess_automated_review_runner_detects_security_and_code_findings(
    tmp_path: Path,
) -> None:
    proj = ProjectRecord(
        project_id=uuid4(),
        name="p1",
        repo_path=tmp_path,
        phase=Phase.REVIEW,
        cycle=1,
        max_cycles=5,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    sec_cmd = ("bandit", "-q", "-r", "src")
    code_cmd = ("ruff", "check", ".")
    gates = FakeGateRunner(
        outcomes={
            sec_cmd: GateResult(1, "", "B101: assert used"),
            code_cmd: GateResult(1, "E501: line too long", ""),
        }
    )
    runner = SubprocessAutomatedReviewRunner(
        projects=FakeProjectRepo(proj),
        gates=gates,
        security_commands=(sec_cmd,),
        code_review_commands=(code_cmd,),
    )
    findings = await runner.run_automated_reviews(proj.project_id, 1)
    assert len(findings) == 2

    sec = next(f for f in findings if f.category == "security")
    assert sec.severity == Severity.HIGH
    assert sec.ambiguity == Ambiguity.CLEAR
    assert "B101" in sec.text

    code = next(f for f in findings if f.category == "code_review")
    assert code.severity == Severity.MEDIUM
    assert code.ambiguity == Ambiguity.CLEAR
    assert "E501" in code.text


async def test_subprocess_automated_review_runner_unknown_project() -> None:
    runner = SubprocessAutomatedReviewRunner(
        projects=FakeProjectRepo(None),
        gates=FakeGateRunner(),
    )
    with pytest.raises(LookupError):
        await runner.run_automated_reviews(uuid4(), 1)

    runner_invalid = SubprocessAutomatedReviewRunner(
        projects=object(),
        gates=FakeGateRunner(),
    )
    with pytest.raises(LookupError):
        await runner_invalid.run_automated_reviews(uuid4(), 1)


def test_default_code_review_command_excludes_vibey_machinery() -> None:
    """`ruff check .` at the repo root must never review .vibey worktrees
    or engine state dirs -- a stale worktree's dead code raised a real
    finding live and looped REVIEW back into BUILD."""
    (command,) = _DEFAULT_CODE_REVIEW
    assert command[:3] == ("ruff", "check", ".")
    for name in (".vibey", ".claudeloop", ".codexloop", ".cursorloop", ".agyloop"):
        index = command.index(name)
        assert command[index - 1] == "--exclude"


def test_default_security_command_is_scoped_to_the_product() -> None:
    """The REVIEW security scan gates the same scope CI gates. `-r src` walked
    the absorbed workspace members, failed every cycle, and looped REVIEW back
    into BUILD forever."""
    assert _DEFAULT_SECURITY == (("bandit", "-q", "-r", "src/vibey"),)


def _runner(config: dict[str, object]) -> SubprocessAutomatedReviewRunner:
    return SubprocessAutomatedReviewRunner.from_config(
        config, projects=FakeProjectRepo(None), gates=FakeGateRunner()
    )


def test_from_config_without_a_review_object_keeps_the_defaults() -> None:
    runner = _runner({})
    assert runner._security_commands == _DEFAULT_SECURITY
    assert runner._code_review_commands == _DEFAULT_CODE_REVIEW


def test_from_config_with_partial_review_object_keeps_the_other_default() -> None:
    runner = _runner({"review": {"security_commands": [["bandit", "-q", "-r", "app"]]}})
    assert runner._security_commands == (("bandit", "-q", "-r", "app"),)
    assert runner._code_review_commands == _DEFAULT_CODE_REVIEW


def test_from_config_overrides_both_command_lists() -> None:
    runner = _runner(
        {
            "review": {
                "security_commands": [["semgrep", "--error"], ["bandit", "-r", "lib"]],
                "code_review_commands": [["eslint", "."]],
            }
        }
    )
    assert runner._security_commands == (
        ("semgrep", "--error"),
        ("bandit", "-r", "lib"),
    )
    assert runner._code_review_commands == (("eslint", "."),)


def test_from_config_honours_an_explicitly_empty_command_list() -> None:
    """`[]` disables a check; it is not the same as saying nothing."""
    runner = _runner({"review": {"security_commands": []}})
    assert runner._security_commands == ()
    assert runner._code_review_commands == _DEFAULT_CODE_REVIEW


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"review": ["security_commands"]}, "review project config must be an object"),
        (
            {"review": {"security_commands": "bandit"}},
            "review.security_commands must be a list of command arrays",
        ),
        (
            {"review": {"security_commands": ["bandit"]}},
            "review.security_commands entries must be non-empty command arrays",
        ),
        (
            {"review": {"security_commands": [[]]}},
            "review.security_commands entries must be non-empty command arrays",
        ),
        (
            {"review": {"code_review_commands": [["ruff", 3]]}},
            "review.code_review_commands arguments must be non-empty strings",
        ),
        (
            {"review": {"code_review_commands": [["ruff", ""]]}},
            "review.code_review_commands arguments must be non-empty strings",
        ),
    ],
)
def test_from_config_rejects_malformed_review_configuration(
    config: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _runner(config)


async def test_configured_security_command_is_the_one_that_runs(tmp_path: Path) -> None:
    proj = ProjectRecord(
        project_id=uuid4(),
        name="p1",
        repo_path=tmp_path,
        phase=Phase.REVIEW,
        cycle=1,
        max_cycles=5,
        config={"review": {"security_commands": [["bandit", "-q", "-r", "src/vibey"]]}},
        created_at=NOW,
        updated_at=NOW,
    )
    gates = FakeGateRunner(
        outcomes={("bandit", "-q", "-r", "src"): GateResult(1, "", "would have blocked")}
    )
    runner = SubprocessAutomatedReviewRunner.from_config(
        proj.config, projects=FakeProjectRepo(proj), gates=gates
    )
    assert await runner.run_automated_reviews(proj.project_id, 1) == ()
